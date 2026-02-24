"""
Telemetry cryptographic integrity and provenance chain helpers.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple


@dataclass
class TelemetryProof:
    payload_hash: str
    signature: str
    chain_hash: str
    prev_chain_hash: str
    signed_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "payload_hash": self.payload_hash,
            "signature": self.signature,
            "chain_hash": self.chain_hash,
            "prev_chain_hash": self.prev_chain_hash,
            "signed_at": self.signed_at,
        }


class TelemetryIntegrityService:
    """HMAC-based signing and chain verification for telemetry events."""

    def __init__(self, signing_key: str | None = None) -> None:
        key = signing_key or os.getenv("TELEMETRY_SIGNING_KEY", "")
        if not key:
            key = "myca-local-telemetry-key"
        self._key = key.encode("utf-8")

    @staticmethod
    def _canonical_json(payload: Dict[str, Any]) -> bytes:
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")

    def compute_payload_hash(self, payload: Dict[str, Any]) -> str:
        return hashlib.sha256(self._canonical_json(payload)).hexdigest()

    def sign_payload_hash(self, payload_hash: str) -> str:
        return hmac.new(self._key, payload_hash.encode("utf-8"), hashlib.sha256).hexdigest()

    def verify_signature(self, payload_hash: str, signature: str) -> bool:
        expected = self.sign_payload_hash(payload_hash)
        return hmac.compare_digest(expected, signature)

    @staticmethod
    def compute_chain_hash(payload_hash: str, signature: str, prev_chain_hash: str) -> str:
        body = f"{prev_chain_hash}:{payload_hash}:{signature}".encode("utf-8")
        return hashlib.sha256(body).hexdigest()

    def create_proof(self, payload: Dict[str, Any], prev_chain_hash: str = "") -> TelemetryProof:
        payload_hash = self.compute_payload_hash(payload)
        signature = self.sign_payload_hash(payload_hash)
        chain_hash = self.compute_chain_hash(payload_hash, signature, prev_chain_hash)
        return TelemetryProof(
            payload_hash=payload_hash,
            signature=signature,
            chain_hash=chain_hash,
            prev_chain_hash=prev_chain_hash,
            signed_at=datetime.now(timezone.utc).isoformat(),
        )

    def verify_proof(self, payload: Dict[str, Any], proof: Dict[str, Any]) -> Tuple[bool, str]:
        payload_hash = self.compute_payload_hash(payload)
        if payload_hash != str(proof.get("payload_hash", "")):
            return False, "payload_hash_mismatch"
        if not self.verify_signature(payload_hash, str(proof.get("signature", ""))):
            return False, "invalid_signature"
        expected_chain = self.compute_chain_hash(
            payload_hash,
            str(proof.get("signature", "")),
            str(proof.get("prev_chain_hash", "")),
        )
        if expected_chain != str(proof.get("chain_hash", "")):
            return False, "chain_hash_mismatch"
        return True, "ok"

    def verify_chain(self, proofs: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """
        Verify internal continuity of a sequence of proofs.
        """
        if not proofs:
            return True, []
        errors: List[str] = []
        prev = ""
        for idx, proof in enumerate(proofs):
            this_prev = str(proof.get("prev_chain_hash", ""))
            if this_prev != prev:
                errors.append(f"chain_break_at_index_{idx}")
            expected = self.compute_chain_hash(
                str(proof.get("payload_hash", "")),
                str(proof.get("signature", "")),
                this_prev,
            )
            actual = str(proof.get("chain_hash", ""))
            if expected != actual:
                errors.append(f"invalid_chain_hash_at_index_{idx}")
            prev = actual
        return len(errors) == 0, errors

