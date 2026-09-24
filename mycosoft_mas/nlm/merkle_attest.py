"""
NLM Merkle attestation — SHA-256 leaves + binary Merkle root + ECDSA (P-256).

Transparent inclusion proofs ship in P1; ZK circuits are P2 additive.
Never invents sensor data — only hashes caller-provided payloads.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

_PRODUCER_ID = os.getenv("NLM_ATTEST_PRODUCER_ID", "mas-nlm-training")
_KEY_PATH = Path(
    os.getenv(
        "NLM_ATTEST_KEY_PATH",
        str(Path.home() / ".mycosoft" / "nlm" / "attest_ecdsa_p256.pem"),
    )
)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def leaf_hash(payload: Dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return sha256_hex(canonical.encode("utf-8"))


def merkle_root(leaves: Sequence[str]) -> str:
    """Binary Merkle root over hex leaf digests (SHA-256). Empty → zeros."""
    if not leaves:
        return "0" * 64
    digests: List[bytes] = [
        bytes.fromhex(h) if len(h) == 64 else hashlib.sha256(h.encode("utf-8")).digest()
        for h in leaves
    ]

    while len(digests) > 1:
        nxt: List[bytes] = []
        for i in range(0, len(digests), 2):
            left = digests[i]
            right = digests[i + 1] if i + 1 < len(digests) else left
            nxt.append(hashlib.sha256(left + right).digest())
        digests = nxt
    return digests[0].hex()


def inclusion_proof(leaves: Sequence[str], index: int) -> Dict[str, Any]:
    """Transparent Merkle inclusion proof (siblings path). Not ZK."""
    if index < 0 or index >= len(leaves):
        raise ValueError("leaf index out of range")
    digests = [bytes.fromhex(h) for h in leaves]
    path: List[Dict[str, str]] = []
    idx = index
    while len(digests) > 1:
        nxt: List[bytes] = []
        for i in range(0, len(digests), 2):
            left = digests[i]
            right = digests[i + 1] if i + 1 < len(digests) else left
            if i == idx or i + 1 == idx:
                sibling = right if i == idx else left
                side = "right" if i == idx else "left"
                path.append({"side": side, "sibling": sibling.hex()})
                idx = len(nxt)
            nxt.append(hashlib.sha256(left + right).digest())
        digests = nxt
    return {
        "leaf_index": index,
        "leaf": leaves[index],
        "path": path,
        "root": digests[0].hex() if digests else "0" * 64,
        "proof_kind": "merkle_inclusion_transparent",
        "zk": False,
    }


def _ensure_signing_key() -> Tuple[Any, bytes]:
    """Load or create ECDSA P-256 key. Returns (private_key, public_der_bytes)."""
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec
    except ImportError as exc:
        raise RuntimeError("cryptography package required for ECDSA attestation") from exc

    _KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if _KEY_PATH.exists():
        private_key = serialization.load_pem_private_key(_KEY_PATH.read_bytes(), password=None)
    else:
        private_key = ec.generate_private_key(ec.SECP256R1())
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        _KEY_PATH.write_bytes(pem)
        logger.info("Created NLM ECDSA P-256 attest key at %s", _KEY_PATH)

    public_der = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_key, public_der


def sign_root(merkle_root_hex: str, timestamp: str, producer_id: str = _PRODUCER_ID) -> Dict[str, Any]:
    """ECDSA P-256 over (merkle_root || timestamp || producer_id)."""
    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
        from cryptography.exceptions import UnsupportedAlgorithm
    except ImportError:
        # Soft path: return unsigned attestation metadata
        message = f"{merkle_root_hex}|{timestamp}|{producer_id}"
        return {
            "algorithm": "sha256-hmac-unavailable",
            "message": message,
            "signature": None,
            "signed": False,
            "note": "Install cryptography for ECDSA P-256 signatures",
        }

    message = f"{merkle_root_hex}|{timestamp}|{producer_id}".encode("utf-8")
    try:
        private_key, public_der = _ensure_signing_key()
        signature = private_key.sign(message, ec.ECDSA(hashes.SHA256()))
        return {
            "algorithm": "ECDSA-P256-SHA256",
            "message_utf8": message.decode("utf-8"),
            "signature_der_hex": signature.hex(),
            "public_key_der_hex": public_der.hex(),
            "producer_id": producer_id,
            "signed": True,
        }
    except Exception as exc:
        logger.warning("ECDSA sign failed: %s", exc)
        return {
            "algorithm": "ECDSA-P256-SHA256",
            "signed": False,
            "error": str(exc),
        }


def attest_payloads(
    payloads: Sequence[Dict[str, Any]],
    producer_id: str = _PRODUCER_ID,
) -> Dict[str, Any]:
    """Hash payloads → Merkle root → ECDSA sign → optional inclusion proofs."""
    ts = datetime.now(timezone.utc).isoformat()
    leaves = [leaf_hash(p) for p in payloads]
    root = merkle_root(leaves)
    signature = sign_root(root, ts, producer_id=producer_id)
    proofs = []
    for i in range(len(leaves)):
        try:
            proofs.append(inclusion_proof(leaves, i))
        except ValueError:
            break
    return {
        "timestamp": ts,
        "producer_id": producer_id,
        "leaf_count": len(leaves),
        "leaves": leaves,
        "merkle_root": root,
        "hash_alg": "SHA-256",
        "signature": signature,
        "inclusion_proofs": proofs,
        "zk_proof": None,
        "zk_note": "ZK (Halo2/groth16) deferred to P2 — transparent Merkle proofs only",
    }
