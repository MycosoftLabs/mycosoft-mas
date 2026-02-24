"""
Provenance API for telemetry chain-of-custody verification.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from mycosoft_mas.myca.event_ledger import get_ledger
from mycosoft_mas.security.telemetry_integrity import TelemetryIntegrityService

router = APIRouter(prefix="/api/provenance", tags=["provenance"])


class VerifyRequest(BaseModel):
    payload: Dict[str, Any]
    proof: Dict[str, Any]


class VerifyResponse(BaseModel):
    valid: bool
    reason: str


class AuditRequest(BaseModel):
    device_id: Optional[str] = None
    limit: int = Field(default=500, ge=1, le=5000)


@router.post("/verify", response_model=VerifyResponse)
async def verify_payload(req: VerifyRequest) -> VerifyResponse:
    service = TelemetryIntegrityService()
    valid, reason = service.verify_proof(req.payload, req.proof)
    return VerifyResponse(valid=valid, reason=reason)


@router.post("/audit")
async def audit_chain(req: AuditRequest) -> Dict[str, Any]:
    ledger = get_ledger()
    chain = ledger.read_telemetry_chain(device_id=req.device_id, limit=req.limit)
    proof_chain: List[Dict[str, Any]] = [
        {
            "payload_hash": e.get("payload_hash", ""),
            "signature": e.get("signature", ""),
            "chain_hash": e.get("chain_hash", ""),
            "prev_chain_hash": e.get("prev_chain_hash", ""),
        }
        for e in chain
    ]
    service = TelemetryIntegrityService()
    valid, errors = service.verify_chain(proof_chain)
    return {
        "valid": valid,
        "errors": errors,
        "count": len(chain),
        "events": chain,
    }

