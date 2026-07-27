"""
Compliance API — NIST 800-171 control state and versioned SSP/POA&M docs (soc_ops).
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mycosoft_mas.security.posture_integrity_monitor import (
    posture_integrity_monitor,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/compliance", tags=["soc-compliance"])


def _pg_ready() -> bool:
    return bool(os.getenv("MINDEX_DATABASE_URL") or os.getenv("DATABASE_URL"))


class ControlUpsert(BaseModel):
    control_id: str
    framework: str = "NIST_800_171"
    family: Optional[str] = None
    title: Optional[str] = None
    implementation_state: str = Field(
        default="unknown",
        pattern="^(implemented|partial|planned|not_applicable|unknown)$",
    )
    evidence_uri: Optional[str] = None
    state_snapshot: Dict[str, Any] = Field(default_factory=dict)


class DocRegenerateRequest(BaseModel):
    doc_type: str = Field(pattern="^(SSP|POAM|policy)$")
    title: str = "Regenerated document"


def _has_evidence_uri(evidence_uri: Optional[str]) -> bool:
    return bool(evidence_uri and evidence_uri.strip())


def _validate_implemented_current_state(state_snapshot: Dict[str, Any]) -> None:
    """Reject split-brain Met promotions before they can reach ``soc_ops``."""
    current_state = state_snapshot.get("current_state")
    if not isinstance(current_state, dict):
        raise HTTPException(
            status_code=422,
            detail="implemented controls require state_snapshot.current_state",
        )

    if current_state.get("implementation_state") != "implemented":
        raise HTTPException(
            status_code=422,
            detail=(
                "implemented controls require "
                "state_snapshot.current_state.implementation_state=implemented"
            ),
        )

    notes = (
        state_snapshot.get("note", ""),
        state_snapshot.get("notes", ""),
        current_state.get("note", ""),
        current_state.get("notes", ""),
    )
    if any("not met" in str(note).lower() for note in notes):
        raise HTTPException(
            status_code=422,
            detail="implemented control state_snapshot cannot contain contradictory 'Not Met' notes",
        )


@router.get("/health")
async def compliance_health():
    return {"ok": True, "postgres_configured": _pg_ready()}


@router.get("/controls")
async def list_controls():
    if not _pg_ready():
        raise HTTPException(status_code=503, detail="MINDEX_DATABASE_URL not configured")
    try:
        from mycosoft_mas.soc import repository as soc_repo

        controls = await soc_repo.list_compliance_controls()
        integrity = await posture_integrity_monitor.validate_controls(controls)
        if integrity.snapshot is None:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Compliance posture is unavailable and no verified "
                    "last-known-good snapshot exists"
                ),
            )
        return {
            "controls": integrity.controls,
            "degraded": integrity.degraded,
            "integrity_reason": integrity.reason,
            "posture_counts": {
                "met": integrity.snapshot.met,
                "partial": integrity.snapshot.partial,
                "non_compliant": integrity.snapshot.non_compliant,
                "total": integrity.snapshot.total,
            },
        }
    except Exception as e:
        logger.exception("list_controls: %s", e)
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.post("/controls")
async def upsert_control(body: ControlUpsert):
    if not _pg_ready():
        raise HTTPException(status_code=503, detail="MINDEX_DATABASE_URL not configured")
    if body.implementation_state == "implemented" and not _has_evidence_uri(
        body.evidence_uri
    ):
        raise HTTPException(
            status_code=422,
            detail="implemented controls require a non-empty evidence_uri",
        )
    if body.implementation_state == "implemented":
        _validate_implemented_current_state(body.state_snapshot)
    try:
        from mycosoft_mas.soc import repository as soc_repo

        await soc_repo.upsert_compliance_control(
            control_id=body.control_id,
            framework=body.framework,
            family=body.family,
            title=body.title,
            implementation_state=body.implementation_state,
            evidence_uri=body.evidence_uri,
            state_snapshot=body.state_snapshot,
        )
        return {"status": "ok", "control_id": body.control_id}
    except Exception as e:
        logger.exception("upsert_control: %s", e)
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.get("/score")
async def compliance_score_api():
    if not _pg_ready():
        raise HTTPException(status_code=503, detail="MINDEX_DATABASE_URL not configured")
    try:
        from mycosoft_mas.soc import repository as soc_repo

        controls = await soc_repo.list_compliance_controls()
        integrity = await posture_integrity_monitor.validate_controls(controls)
        if integrity.snapshot is None:
            raise HTTPException(
                status_code=503,
                detail="Compliance score is unavailable without a verified posture snapshot",
            )
        score = await soc_repo.compliance_score()
        return {
            **score,
            "degraded": integrity.degraded,
            "integrity_reason": integrity.reason,
            "verified_practice_counts": {
                "met": integrity.snapshot.met,
                "partial": integrity.snapshot.partial,
                "non_compliant": integrity.snapshot.non_compliant,
                "total": integrity.snapshot.total,
                "met_percent": round(
                    integrity.snapshot.met / integrity.snapshot.total * 100, 1
                ),
            },
        }
    except Exception as e:
        logger.exception("compliance_score: %s", e)
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.get("/docs")
async def list_docs_placeholder():
    """Latest SSP and POAM pointers (full list can be added with pagination)."""
    if not _pg_ready():
        raise HTTPException(status_code=503, detail="MINDEX_DATABASE_URL not configured")
    try:
        from mycosoft_mas.soc import repository as soc_repo

        ssp = await soc_repo.get_latest_compliance_doc("SSP")
        poam = await soc_repo.get_latest_compliance_doc("POAM")
        return {"SSP": ssp, "POAM": poam}
    except Exception as e:
        logger.exception("list_docs: %s", e)
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.get("/docs/{doc_type}")
async def get_doc(doc_type: str):
    if doc_type not in ("SSP", "POAM", "policy"):
        raise HTTPException(status_code=400, detail="invalid doc_type")
    if not _pg_ready():
        raise HTTPException(status_code=503, detail="MINDEX_DATABASE_URL not configured")
    try:
        from mycosoft_mas.soc import repository as soc_repo

        row = await soc_repo.get_latest_compliance_doc(doc_type)
        if not row:
            raise HTTPException(status_code=404, detail="no document yet")
        return row
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_doc: %s", e)
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.post("/regenerate")
async def regenerate_doc(body: DocRegenerateRequest):
    """
    Run the multi-model compliance doc pipeline (Perplexity -> Claude -> OpenAI).
    Requires API keys; writes a new version to soc_ops.compliance_docs.
    """
    if not _pg_ready():
        raise HTTPException(status_code=503, detail="MINDEX_DATABASE_URL not configured")
    try:
        from mycosoft_mas.compliance.doc_engine import run_compliance_doc_pipeline

        result = await run_compliance_doc_pipeline(doc_type=body.doc_type, title=body.title)
        return result
    except ImportError as e:
        raise HTTPException(status_code=501, detail=str(e)) from e
    except Exception as e:
        logger.exception("regenerate_doc: %s", e)
        raise HTTPException(status_code=503, detail=str(e)) from e
