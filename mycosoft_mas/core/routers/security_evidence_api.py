"""
Security evidence API — canonical emitter and personnel screening adjudication.
Patch v2 (Jul 21, 2026): all control Met flips go through POST /api/security/evidence/emit.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from mycosoft_mas.compliance.evidence_emitter import EVIDENCE_TYPES, emit_evidence
from mycosoft_mas.compliance.evidence_register import load_evidence_register
from mycosoft_mas.core.routers.compliance_api import _require_posture_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/security", tags=["security-evidence"])


def _pg_ready() -> bool:
    return bool(os.getenv("MINDEX_DATABASE_URL") or os.getenv("DATABASE_URL"))


class ArtifactRef(BaseModel):
    kind: Literal["preveil", "drive", "local"]
    path: Optional[str] = None
    file_id: Optional[str] = None


class EvidenceEmitRequest(BaseModel):
    control_ids: List[str] = Field(min_length=1)
    evidence_type: str
    artifact_refs: List[ArtifactRef] = Field(min_length=1)
    actor_subject_id: Optional[str] = None
    verified_at: Optional[datetime] = None
    notes: Optional[str] = None


class PsAdjudicateRequest(BaseModel):
    event_id: str


class TrainingRecordRequest(BaseModel):
    subject_id: str
    course: str
    completed_at: datetime
    certificate_preveil_path: str
    control_ids: List[str] = Field(
        default_factory=lambda: ["AT.L2-3.2.1", "AT.L2-3.2.2", "AT.L2-3.2.3", "3.2.1", "3.2.2", "3.2.3"]
    )


class IrTabletopRequest(BaseModel):
    date: datetime
    scenarios: List[str] = Field(min_length=1)
    attendees: List[str] = Field(min_length=1)
    findings_md: str = Field(min_length=1)
    recording_preveil_path: str
    control_ids: List[str] = Field(default_factory=lambda: ["IR.L2-3.6.3", "3.6.3"])


@router.get("/evidence-register")
async def get_evidence_register(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    """Metadata-only CMMC evidence register for Security tab proxy (no file bodies)."""
    _require_posture_api_key(x_api_key)
    try:
        return load_evidence_register()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("get_evidence_register: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/ps/screening-events")
async def list_personnel_screening_events(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    """Admin/hr metadata table for Security tab proxy (no report bodies)."""
    _require_posture_api_key(x_api_key)
    if not _pg_ready():
        raise HTTPException(status_code=503, detail="MINDEX_DATABASE_URL not configured")
    try:
        from mycosoft_mas.soc import repository as soc_repo

        events = await soc_repo.list_ps_screening_events()
        return {"events": events, "count": len(events)}
    except Exception as exc:
        logger.exception("list_personnel_screening_events: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/evidence/emit")
async def emit_security_evidence(
    body: EvidenceEmitRequest,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    _require_posture_api_key(x_api_key)
    if not _pg_ready():
        raise HTTPException(status_code=503, detail="MINDEX_DATABASE_URL not configured")
    actor_uuid: Optional[UUID] = None
    if body.actor_subject_id:
        try:
            actor_uuid = UUID(body.actor_subject_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="invalid actor_subject_id") from exc
    if body.evidence_type not in EVIDENCE_TYPES:
        raise HTTPException(status_code=422, detail=f"unsupported evidence_type: {body.evidence_type}")

    verified_at = body.verified_at or datetime.now(timezone.utc)
    if verified_at.tzinfo is None:
        verified_at = verified_at.replace(tzinfo=timezone.utc)

    try:
        result = await emit_evidence(
            control_ids=body.control_ids,
            evidence_type=body.evidence_type,
            artifact_refs=[ref.model_dump(exclude_none=True) for ref in body.artifact_refs],
            actor_subject_id=actor_uuid,
            verified_at=verified_at,
            notes=body.notes,
            operator="mas_api_key",
            endpoint="/api/security/evidence/emit",
            purpose=f"emit {body.evidence_type}",
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("emit_security_evidence: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/ps/adjudicate")
async def adjudicate_personnel_screening(
    body: PsAdjudicateRequest,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    """Flip PS.L2-3.9.1 + NIST 3.9.1 only when screening row + artifacts validate."""
    _require_posture_api_key(x_api_key)
    if not _pg_ready():
        raise HTTPException(status_code=503, detail="MINDEX_DATABASE_URL not configured")
    try:
        event_uuid = UUID(body.event_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="invalid event_id") from exc

    from mycosoft_mas.compliance.evidence_emitter import adjudicate_screening_event

    try:
        return await adjudicate_screening_event(event_uuid, operator="mas_api_key")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("adjudicate_personnel_screening: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/at/training-record")
async def record_security_training(
    body: TrainingRecordRequest,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    _require_posture_api_key(x_api_key)
    if not _pg_ready():
        raise HTTPException(status_code=503, detail="MINDEX_DATABASE_URL not configured")
    try:
        subject_uuid = UUID(body.subject_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="invalid subject_id") from exc

    verified_at = body.completed_at
    if verified_at.tzinfo is None:
        verified_at = verified_at.replace(tzinfo=timezone.utc)

    try:
        return await emit_evidence(
            control_ids=body.control_ids,
            evidence_type="training_certificate",
            artifact_refs=[{"kind": "preveil", "path": body.certificate_preveil_path}],
            actor_subject_id=subject_uuid,
            verified_at=verified_at,
            notes=f"CDSE training: {body.course}",
            operator="mas_api_key",
            endpoint="/api/security/at/training-record",
            purpose="AT.L2-3.2.x training evidence",
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("record_security_training: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/ir/tabletop-record")
async def record_ir_tabletop(
    body: IrTabletopRequest,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    _require_posture_api_key(x_api_key)
    if not _pg_ready():
        raise HTTPException(status_code=503, detail="MINDEX_DATABASE_URL not configured")

    verified_at = body.date
    if verified_at.tzinfo is None:
        verified_at = verified_at.replace(tzinfo=timezone.utc)

    try:
        return await emit_evidence(
            control_ids=body.control_ids,
            evidence_type="ir_tabletop",
            artifact_refs=[{"kind": "preveil", "path": body.recording_preveil_path}],
            actor_subject_id=None,
            verified_at=verified_at,
            notes=body.findings_md[:500],
            operator="mas_api_key",
            endpoint="/api/security/ir/tabletop-record",
            purpose="IR.L2-3.6.3 tabletop exercise",
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("record_ir_tabletop: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
