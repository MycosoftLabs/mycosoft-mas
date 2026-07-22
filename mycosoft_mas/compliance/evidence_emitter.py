"""
Canonical SSP evidence emitter — all control Met flips go through here.
Perplexity handoff patch v2 (Jul 21, 2026).
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

logger = logging.getLogger(__name__)

_DRIVE_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{20,}$")
_PREVEIL_PATH_RE = re.compile(r"^/CUI/.+")

EVIDENCE_TYPES = frozenset(
    {
        "personnel_screening",
        "endpoint_config",
        "siem_alert",
        "enclave_activation",
        "training_certificate",
        "ir_tabletop",
        "policy_signature",
        "supply_chain_screen",
    }
)


def _db_ready() -> bool:
    return bool(os.getenv("MINDEX_DATABASE_URL") or os.getenv("DATABASE_URL"))


def validate_artifact_ref(ref: Dict[str, Any]) -> Optional[str]:
    """Return None if valid, else human-readable rejection reason."""
    kind = str(ref.get("kind") or "").strip().lower()
    if kind == "preveil":
        path = str(ref.get("path") or "").strip()
        if not _PREVEIL_PATH_RE.match(path):
            return "preveil artifact requires path under /CUI/"
        return None
    if kind == "drive":
        file_id = str(ref.get("file_id") or "").strip()
        if not _DRIVE_ID_RE.match(file_id):
            return "drive artifact requires a valid file_id"
        return None
    if kind == "local":
        path = str(ref.get("path") or "").strip()
        if not path:
            return "local artifact requires path"
        if not os.path.isfile(path):
            return f"local artifact path does not exist: {path}"
        return None
    return f"unsupported artifact kind: {kind or 'missing'}"


def validate_emit_request(
    control_ids: List[str],
    evidence_type: str,
    artifact_refs: List[Dict[str, Any]],
) -> Optional[str]:
    if not control_ids:
        return "control_ids must not be empty"
    if evidence_type not in EVIDENCE_TYPES:
        return f"unsupported evidence_type: {evidence_type}"
    if not artifact_refs:
        return "artifact_refs must not be empty (honesty gate)"
    for ref in artifact_refs:
        reason = validate_artifact_ref(ref)
        if reason:
            return reason
    return None


def primary_evidence_uri(artifact_refs: List[Dict[str, Any]], evidence_id: UUID) -> str:
    for ref in artifact_refs:
        if ref.get("kind") == "preveil" and ref.get("path"):
            return str(ref["path"])
    for ref in artifact_refs:
        if ref.get("kind") == "drive" and ref.get("file_id"):
            return f"drive://{ref['file_id']}"
    for ref in artifact_refs:
        if ref.get("kind") == "local" and ref.get("path"):
            return str(ref["path"])
    return f"ssp_evidence://{evidence_id}"


async def emit_evidence(
    *,
    control_ids: List[str],
    evidence_type: str,
    artifact_refs: List[Dict[str, Any]],
    actor_subject_id: Optional[UUID],
    verified_at: datetime,
    notes: Optional[str],
    operator: str,
    endpoint: str,
    purpose: str,
) -> Dict[str, Any]:
    if not _db_ready():
        raise RuntimeError("database not configured")

    rejection = validate_emit_request(control_ids, evidence_type, artifact_refs)
    if rejection:
        raise ValueError(rejection)

    from mycosoft_mas.soc import repository as soc_repo

    evidence_id = await soc_repo.insert_ssp_evidence(
        control_ids=control_ids,
        evidence_type=evidence_type,
        artifact_refs=artifact_refs,
        actor_subject_id=actor_subject_id,
        verified_at=verified_at,
        notes=notes,
    )
    evidence_uri = primary_evidence_uri(artifact_refs, evidence_id)

    await soc_repo.insert_compliance_audit_log(
        operator=operator,
        endpoint=endpoint,
        purpose=purpose,
        evidence_id=evidence_id,
        payload={
            "control_ids": control_ids,
            "evidence_type": evidence_type,
            "evidence_uri": evidence_uri,
        },
    )

    for control_id in control_ids:
        framework = "NIST_800_171"
        if "." in control_id and control_id[0].isalpha():
            framework = "CMMC_L2"
        await soc_repo.upsert_compliance_control(
            control_id=control_id,
            framework=framework,
            family=None,
            title=None,
            implementation_state="implemented",
            evidence_uri=evidence_uri,
            state_snapshot={
                "evidence_id": str(evidence_id),
                "evidence_type": evidence_type,
                "verified_at": verified_at.isoformat(),
            },
        )

    score = await soc_repo.compliance_score()
    logger.info(
        "evidence_emitted evidence_id=%s controls=%s type=%s",
        evidence_id,
        control_ids,
        evidence_type,
    )
    return {
        "evidence_id": str(evidence_id),
        "evidence_uri": evidence_uri,
        "control_ids": control_ids,
        "sprs_score": score,
    }


async def adjudicate_screening_event(event_id: UUID, *, operator: str) -> Dict[str, Any]:
    from mycosoft_mas.soc import repository as soc_repo

    event = await soc_repo.get_ps_screening_event(event_id)
    if not event:
        raise ValueError("screening event not found")

    disposition = event.get("disposition")
    if disposition not in ("cleared", "cleared_with_condition"):
        raise ValueError("disposition must be cleared before Met flip")

    report_path = event.get("report_preveil_path")
    memo_path = event.get("adjudication_memo_preveil_path")
    if not report_path or not memo_path:
        raise ValueError("report and adjudication memo PreVeil paths required")

    adjudicator = event.get("adjudicator_subject_id")
    subject = event.get("subject_id")
    if adjudicator and subject and adjudicator == subject:
        raise ValueError("subject cannot self-adjudicate")

    artifact_refs: List[Dict[str, Any]] = [
        {"kind": "preveil", "path": report_path},
        {"kind": "preveil", "path": memo_path},
    ]
    if event.get("report_drive_file_id"):
        artifact_refs.append({"kind": "drive", "file_id": event["report_drive_file_id"]})
    if event.get("adjudication_memo_drive_file_id"):
        artifact_refs.append(
            {"kind": "drive", "file_id": event["adjudication_memo_drive_file_id"]}
        )

    verified_at = datetime.now(timezone.utc)
    memo_id = event.get("adjudication_memo_id") or str(event_id)
    return await emit_evidence(
        control_ids=["PS.L2-3.9.1", "3.9.1"],
        evidence_type="personnel_screening",
        artifact_refs=artifact_refs,
        actor_subject_id=UUID(subject) if subject else None,
        verified_at=verified_at,
        notes=f"Personnel screening adjudication {memo_id}",
        operator=operator,
        endpoint="/api/security/ps/adjudicate",
        purpose="PS.L2-3.9.1 personnel screening evidence",
    )
