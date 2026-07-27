"""
Compliance API — NIST 800-171 control state and versioned SSP/POA&M docs (soc_ops).
"""

from __future__ import annotations

import hmac
import logging
import os
from collections import defaultdict, deque
from time import monotonic
from typing import Any, Deque, Dict, List, Literal, Optional

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from mycosoft_mas.integrations.backgroundchecks_client import (
    BackgroundChecksClient,
    BackgroundChecksError,
)

from mycosoft_mas.security.posture_integrity_monitor import (
    posture_integrity_monitor,
)

from mycosoft_mas.security.posture_integrity_monitor import (
    posture_integrity_monitor,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/compliance", tags=["soc-compliance"])
posture_router = APIRouter(prefix="/api/myca", tags=["myca-posture"])
_posture_rate_windows: dict[str, Deque[float]] = defaultdict(deque)
_posture_rate_limit = 60
_posture_rate_window_seconds = 60.0


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


class BackgroundCheckOrderRequest(BaseModel):
    applicant_email: str = Field(min_length=3, max_length=254)
    report_sku: Literal["HIRE1", "HIRE2", "HIRE3"]
    terms_agree: Literal[True]
    drug_test: bool = False
    mvr: bool = False
    employment: bool = False
    education: bool = False
    blj: bool = False
    federal_criminal: bool = False

    @field_validator("applicant_email")
    @classmethod
    def validate_applicant_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized.count("@") != 1 or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("a valid applicant email is required")
        return normalized


def _split_env_values(name: str) -> set[str]:
    return {
        value.strip().lower()
        for value in os.getenv(name, "").split(",")
        if value.strip()
    }


def _allowed_background_check_emails() -> set[str]:
    return _split_env_values("BACKGROUNDCHECKS_ALLOWED_EMPLOYEE_EMAILS")


def _bgc_automation_enabled() -> bool:
    return os.getenv("BGC_AUTOMATION_ENABLED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _production_orders_allowed() -> bool:
    if not _bgc_automation_enabled():
        return False
    return os.getenv("BACKGROUNDCHECKS_PROD_ORDERS_ALLOWED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _require_posture_api_key(x_api_key: str | None) -> None:
    configured_key = os.getenv("MYCA_POSTURE_API_KEY", "")
    if not configured_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MYCA posture API key is not configured",
        )
    if not x_api_key or not hmac.compare_digest(x_api_key, configured_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid MYCA posture API key",
        )

    now = monotonic()
    window = _posture_rate_windows[x_api_key]
    cutoff = now - _posture_rate_window_seconds
    while window and window[0] <= cutoff:
        window.popleft()
    if len(window) >= _posture_rate_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="MYCA posture API rate limit exceeded",
            headers={"Retry-After": str(int(_posture_rate_window_seconds))},
        )
    window.append(now)


def _minimum_report_status(report: dict[str, Any]) -> dict[str, Any]:
    """Return metadata only; never expose report content or applicant PII beyond email."""
    return {
        "applicant_email": report.get("applicant_email"),
        "report_key": report.get("report_key"),
        "report_sku": report.get("report_sku"),
        "report_status": report.get("report_status") or report.get("status"),
        "timestamp": report.get("timestamp"),
        "expired": report.get("expired"),
    }


async def _list_allowlisted_background_checks() -> list[dict[str, Any]]:
    allowed_emails = _allowed_background_check_emails()
    if not allowed_emails:
        return []
    client = BackgroundChecksClient()
    reports = await client.list_reports()
    return [
        _minimum_report_status(report)
        for report in reports
        if str(report.get("applicant_email", "")).strip().lower() in allowed_emails
    ]


@router.get("/health")
async def compliance_health():
    return {"ok": True, "postgres_configured": _pg_ready()}


@router.get("/background-checks")
async def list_background_checks(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    """Return limited BackgroundChecks status metadata for configured staff only."""
    _require_posture_api_key(x_api_key)
    allowed_emails = _allowed_background_check_emails()
    if not allowed_emails:
        return {
            "status": "not_configured",
            "subjects": [],
            "allowlist_configured": False,
        }
    try:
        return {
            "status": "ok",
            "subjects": await _list_allowlisted_background_checks(),
            "allowlist_configured": True,
        }
    except BackgroundChecksError as exc:
        logger.warning("background_checks_status_failed status_code=%s", exc.status_code)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="BackgroundChecks status is unavailable",
        ) from exc


@router.post("/background-checks/order", status_code=status.HTTP_202_ACCEPTED)
async def create_background_check_order(
    body: BackgroundCheckOrderRequest,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    """Create an allowlisted staff invitation only when production ordering is enabled."""
    _require_posture_api_key(x_api_key)
    allowed_emails = _allowed_background_check_emails()
    if not allowed_emails:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="BackgroundChecks employee allowlist is not configured",
        )
    if body.applicant_email not in allowed_emails:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="applicant is not eligible for automated background-check ordering",
        )
    if not _production_orders_allowed():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="production background-check ordering is disabled",
        )
    try:
        await BackgroundChecksClient().create_order(
            applicant_email=body.applicant_email,
            report_sku=body.report_sku,
            terms_agree=body.terms_agree,
            add_ons={
                "drug_test": body.drug_test,
                "mvr": body.mvr,
                "employment": body.employment,
                "education": body.education,
                "blj": body.blj,
                "federal_criminal": body.federal_criminal,
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except BackgroundChecksError as exc:
        logger.warning("background_checks_order_failed status_code=%s", exc.status_code)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="BackgroundChecks rejected the order",
        ) from exc

    return {
        "status": "accepted",
        "applicant_email": body.applicant_email,
        "report_sku": body.report_sku,
    }


def _preveil_posture_block(*, drive_path_configured: bool) -> dict[str, Any]:
    """Honest PreVeil onboarding posture; never claims PE.3.10.6 Met or enclave live."""
    enclave_live = os.getenv("PREVEIL_ENCLAVE_LIVE", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    return {
        "status": "configured" if drive_path_configured and enclave_live else "pending_onboarding",
        "design": "drive_fs",
        "storage_assumption": "preveil_drive_mount_not_s3_api",
        "read_only": True,
        "drive_path_configured": drive_path_configured,
        "enclave_live": enclave_live,
        "pending_onboarding": not (drive_path_configured and enclave_live),
        "order_processed_date": "2026-07-16",
        "csm": {
            "name": "Adam Fernandez",
            "email": "afernandez@preveil.com",
            "assigned_date": "2026-07-17",
        },
        "pending_mycosoft_action": "schedule_technical_onboarding_call_or_self_serve_install",
        "email_relay": {
            "status": "phase_2_addon",
            "available_after": "2_user_enclave_live",
            "eta_weeks": "2-3",
            "eca_tls_cert": "customer_procurement_open",
        },
        "pe_l2_3_10_6": {
            "implementation_state": "partial_in_progress",
            "met": False,
            "note": "Do not flip Met until enclave is live with evidence in PreVeil.",
        },
    }


async def _cmmc_summary_block() -> dict[str, Any] | None:
    if not _pg_ready():
        return None
    try:
        from mycosoft_mas.soc import repository as soc_repo

        score = await soc_repo.compliance_score()
        return {
            "source": "soc_ops.compliance_controls",
            "read_only": True,
            "not_evidence": True,
            **score,
        }
    except Exception:
        logger.exception("myca_posture_cmmc_summary_failed")
        return None


@posture_router.get("/posture")
async def myca_posture(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    """Read-only operational posture for MYCA; it is not CMMC evidence."""
    _require_posture_api_key(x_api_key)
    drive_path_configured = bool(os.getenv("PREVEIL_DRIVE_PATH", "").strip())
    background_checks: dict[str, Any] = {
        "vendor": "backgroundchecks.com",
        "fulfillment_provider": "HireRight",
        "vendor_relationship": "hireright_sister_no_long_term_commitment",
        "automation_enabled": _bgc_automation_enabled(),
        "status_polling_configured": BackgroundChecksClient().is_configured,
        "allowlist_configured": bool(_allowed_background_check_emails()),
        "production_orders_allowed": _production_orders_allowed(),
        "prod_orders_gate_note": (
            "BGC_AUTOMATION_ENABLED=false (patch v2). Manual HireRight path complete Jul 21; "
            "do not provision BC.com production orders until automation re-enabled."
        ),
        "nick_faso_confirmation": {
            "status": "bypassed",
            "note": "Patch v2: Morgan ordered HireRight six-check directly; Nick/BC.com path no longer critical-path.",
        },
        "personnel_screening_jul21": {
            "provider": "HireRight",
            "package": "6-check standard",
            "subjects_complete": ["Rockcoons, Morgan", "Ricasata, Raljoseph"],
            "adjudication_memo_ids": [
                "MYC-ADJ-ROCKCOONS-2026-07-21",
                "MYC-ADJ-RICASATA-2026-07-21",
            ],
            "hr_drive_folder_id": "1JzHq6t3ceMp4s3OKA93BS7DtQMJCJau2",
            "evidence_api": "/api/security/ps/screening-events",
            "adjudicate_api": "/api/security/ps/adjudicate",
            "ps_l2_3_9_1_met_via_emitter_only": True,
        },
        "sandbox_in_vendor_docs": True,
        "day_one_path": "deferred_until_BGC_AUTOMATION_ENABLED",
    }
    if background_checks["status_polling_configured"] and background_checks["allowlist_configured"]:
        try:
            background_checks["subjects"] = await _list_allowlisted_background_checks()
            background_checks["status_polling_available"] = True
        except BackgroundChecksError:
            background_checks["status_polling_available"] = False
    payload: dict[str, Any] = {
        "read_only": True,
        "evidence_status": "operational_posture_only",
        "myca_runtime": {
            "agents_registered": "hundreds",
            "daily_runtime_live": False,
            "agent_consumption": "deferred_until_runtime_live",
        },
        "compliance_ui": {
            "surface": "mycosoft.com_security_tab",
            "not_vercel_app": True,
            "not_doppler": True,
            "ui_owner": "claude",
            "posture_api_owner": "cursor_mas",
        },
        "background_checks": background_checks,
        "preveil": _preveil_posture_block(drive_path_configured=drive_path_configured),
    }
    cmmc_summary = await _cmmc_summary_block()
    if cmmc_summary is not None:
        payload["cmmc"] = cmmc_summary
    return payload


@router.get("/controls")
async def list_controls():
    if not _pg_ready():
        raise HTTPException(status_code=503, detail="MINDEX_DATABASE_URL not configured")
    try:
        from mycosoft_mas.soc import repository as soc_repo

        controls = await soc_repo.list_compliance_controls()
        if not controls:
            logger.critical(
                "compliance_controls_empty_refusing_response; investigate soc_ops state"
            )
            raise HTTPException(
                status_code=503,
                detail="compliance control state is unexpectedly empty",
            )
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
    except HTTPException:
        raise
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
        if not controls:
            logger.critical(
                "compliance_score_empty_refusing_response; investigate soc_ops state"
            )
            raise HTTPException(
                status_code=503,
                detail="compliance control state is unexpectedly empty",
            )
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
                "met_percent": (
                    round(integrity.snapshot.met / integrity.snapshot.total * 100, 1)
                    if integrity.snapshot.total
                    else 0.0
                ),
            },
        }
    except HTTPException:
        raise
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
