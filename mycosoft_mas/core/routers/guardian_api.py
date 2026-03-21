"""
Guardian API — Expose constitutional guardian capabilities.

Endpoints for monitoring guardian state, checking authority,
managing sentry mode, viewing moral precedence, and inspecting tripwires.

Architecture: March 9, 2026
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mycosoft_mas.core.routers.api_keys import require_api_key_scoped
from mycosoft_mas.guardian.authority_engine import (
    AuthorityEngine,
    AuthorityRequest,
    RiskTier,
)
from mycosoft_mas.guardian.constitutional_guardian import ConstitutionalGuardian
from mycosoft_mas.guardian.developmental_stages import DevelopmentalTracker
from mycosoft_mas.guardian.operational_modes import OperationalMode, OperationalModeManager
from mycosoft_mas.guardian.sentry_mode import SentryMode, SentryProfile
from mycosoft_mas.guardian.tripwires import GuardianTripwires

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/guardian", tags=["guardian"])

# Singleton instances (initialized on first use)
_guardian: Optional[ConstitutionalGuardian] = None
_authority: Optional[AuthorityEngine] = None
_developmental: Optional[DevelopmentalTracker] = None
_sentry: Optional[SentryMode] = None
_tripwires: Optional[GuardianTripwires] = None
_modes: Optional[OperationalModeManager] = None


def _get_guardian() -> ConstitutionalGuardian:
    global _guardian
    if _guardian is None:
        _guardian = ConstitutionalGuardian()
    return _guardian


def _get_authority() -> AuthorityEngine:
    global _authority
    if _authority is None:
        _authority = AuthorityEngine(guardian=_get_guardian())
    return _authority


def _get_developmental() -> DevelopmentalTracker:
    global _developmental
    if _developmental is None:
        _developmental = DevelopmentalTracker()
    return _developmental


def _get_sentry() -> SentryMode:
    global _sentry
    if _sentry is None:
        _sentry = SentryMode()
    return _sentry


def _get_tripwires() -> GuardianTripwires:
    global _tripwires
    if _tripwires is None:
        _tripwires = GuardianTripwires()
    return _tripwires


def _get_modes() -> OperationalModeManager:
    global _modes
    if _modes is None:
        _modes = OperationalModeManager()
    return _modes


# --- Request/Response Models ---


class AuthorityCheckRequest(BaseModel):
    action: str
    requester: str = "api_user"
    context: Dict[str, Any] = Field(default_factory=dict)
    risk_tier: Optional[str] = None
    target_files: List[str] = Field(default_factory=list)
    justification: str = ""


class SentryActivateRequest(BaseModel):
    profile_name: Optional[str] = None
    watch_targets: Optional[List[str]] = None
    duration_hours: Optional[float] = None


class ModeSwitchRequest(BaseModel):
    mode: str  # "morgan" or "mycosoft"
    reason: str = ""


class EmergencyHaltRequest(BaseModel):
    reason: str


# --- Endpoints ---


@router.get("/status")
async def guardian_status():
    """Get guardian health and current state."""
    guardian = _get_guardian()
    state = await guardian.get_state()
    return {
        "status": "active" if state.active else "inactive",
        "halted": guardian.is_halted(),
        "developmental_stage": state.developmental_stage,
        "operational_mode": state.operational_mode,
        "sentry_active": state.sentry_active,
        "actions_reviewed": state.actions_reviewed,
        "actions_blocked": state.actions_blocked,
        "actions_paused": state.actions_paused,
        "emergency_halts": state.emergency_halts,
        "boot_statement_loaded": state.boot_statement_loaded,
        "tripwire_alerts_count": len(state.tripwire_alerts),
    }


@router.get("/boot-statement")
async def get_boot_statement():
    """View the constitutional boot statement."""
    guardian = _get_guardian()
    return {
        "boot_statement": guardian.get_boot_statement(),
        "loaded": bool(guardian.get_boot_statement()),
    }


@router.get("/developmental-stage")
async def get_developmental_stage():
    """Get current developmental stage and capabilities."""
    tracker = _get_developmental()
    caps = tracker.get_capabilities()
    return {
        "current_stage": tracker.get_current_stage().value,
        "capabilities": {
            "can_read": caps.can_read,
            "can_write": caps.can_write,
            "can_execute": caps.can_execute,
            "can_deploy": caps.can_deploy,
            "can_self_modify": caps.can_self_modify,
            "max_risk_tier": caps.max_risk_tier,
            "requires_approval": caps.requires_approval,
            "autonomy_domains": list(caps.autonomy_domains),
        },
        "description": caps.description,
        "all_stages": tracker.get_all_stage_info(),
    }


@router.post("/authority-check")
async def check_authority(request: AuthorityCheckRequest):
    """Check if an action is authorized."""
    engine = _get_authority()
    risk = RiskTier(request.risk_tier) if request.risk_tier else None

    result = await engine.authorize(
        AuthorityRequest(
            action=request.action,
            requester=request.requester,
            context=request.context,
            risk_tier=risk,
            target_files=request.target_files,
            justification=request.justification,
        )
    )

    return {
        "decision": result.decision.value,
        "reason": result.reason,
        "risk_tier": result.risk_tier.value,
        "moral_approved": result.moral_approved,
        "guardian_verdict": result.guardian_verdict.value if result.guardian_verdict else None,
        "warnings": result.warnings,
        "pipeline_stages": result.pipeline_stages,
    }


@router.get("/moral-precedence")
async def get_moral_precedence():
    """View the moral precedence hierarchy."""
    from mycosoft_mas.guardian.moral_precedence import (
        ANTI_EXTINCTION_CLAUSE,
        MoralPrecedenceEngine,
    )

    engine = MoralPrecedenceEngine()
    return {
        "hierarchy": engine.get_precedence_hierarchy(),
        "anti_extinction_clause": ANTI_EXTINCTION_CLAUSE,
        "uncertainty_rule": "When moral uncertainty rises, power goes down, not up.",
    }


@router.get("/sentry")
async def get_sentry_status():
    """Get sentry mode status."""
    sentry = _get_sentry()
    status = await sentry.get_status()
    return {
        "state": status.state.value,
        "profile": status.profile.name if status.profile else None,
        "activated_at": status.activated_at.isoformat() if status.activated_at else None,
        "alerts_count": len(status.alerts),
        "actions_taken": status.actions_taken,
        "watch_targets": status.watch_targets_active,
        "duration_remaining_hours": status.duration_remaining_hours,
        "available_profiles": sentry.get_available_profiles(),
    }


@router.post("/sentry/activate")
async def activate_sentry(
    request: SentryActivateRequest,
    _auth: dict = require_api_key_scoped("guardian:admin"),
):
    """Activate sentry mode."""
    sentry = _get_sentry()

    if request.profile_name:
        status = await sentry.activate(profile_name=request.profile_name)
    elif request.watch_targets:
        profile = SentryProfile(
            name="custom",
            watch_targets=request.watch_targets,
            duration_hours=request.duration_hours,
        )
        status = await sentry.activate(profile=profile)
    else:
        status = await sentry.activate()

    return {
        "state": status.state.value,
        "profile": status.profile.name if status.profile else None,
        "watch_targets": status.watch_targets_active,
    }


@router.post("/sentry/deactivate")
async def deactivate_sentry(
    _auth: dict = require_api_key_scoped("guardian:admin"),
):
    """Deactivate sentry mode."""
    sentry = _get_sentry()
    status = await sentry.deactivate()
    return {"state": status.state.value}


@router.get("/tripwires")
async def get_tripwire_alerts():
    """Get active tripwire alerts."""
    tripwires = _get_tripwires()
    alerts = tripwires.get_alerts()
    return {
        "total_alerts": len(alerts),
        "alerts": [
            {
                "type": a.tripwire_type.value,
                "severity": a.severity.value,
                "description": a.description,
                "evidence": a.evidence,
                "triggered_at": a.triggered_at.isoformat(),
                "recommended_action": a.recommended_action,
            }
            for a in alerts
        ],
    }


@router.get("/operational-mode")
async def get_operational_mode():
    """Get current operational mode."""
    modes = _get_modes()
    return {
        "current_mode": modes.get_current_mode().value,
        "policy": {
            "scope": modes.get_policy().scope,
            "permission_level": modes.get_policy().permission_level,
            "voice_style": modes.get_voice_style(),
        },
        "modes": modes.get_mode_info(),
    }


@router.post("/operational-mode")
async def switch_operational_mode(
    request: ModeSwitchRequest,
    auth: dict = require_api_key_scoped("guardian:admin"),
):
    """Switch operational mode."""
    modes = _get_modes()
    try:
        target = OperationalMode(request.mode)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode: {request.mode}. Must be 'morgan' or 'mycosoft'",
        )

    result = await modes.switch_mode(
        target=target,
        requester=auth.get("user_id", "api_key"),
        reason=request.reason,
    )
    return {
        "success": result.success,
        "previous_mode": result.previous_mode.value,
        "new_mode": result.new_mode.value,
        "reason": result.reason,
    }


@router.post("/emergency-halt")
async def emergency_halt(
    request: EmergencyHaltRequest,
    _auth: dict = require_api_key_scoped("guardian:admin"),
):
    """Emergency halt — block all actions immediately."""
    guardian = _get_guardian()
    await guardian.emergency_halt(reason=request.reason)
    return {
        "halted": True,
        "reason": request.reason,
        "message": "Emergency halt activated. All actions blocked. Manual restart required.",
    }


@router.get("/audit-log")
async def get_audit_log():
    """Get the guardian's independent audit log."""
    guardian = _get_guardian()
    return {"audit_log": guardian.get_audit_log()}
