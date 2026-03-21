"""
Red-Team Guardian/AVANI Approval Gate — PentAGI-Style SOC Integration

Enforces Guardian authority-check for medium/high/critical red-team simulations.
Maps simulation types to risk tiers and bounded autonomy policy.

Date: March 10, 2026
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

from mycosoft_mas.guardian.authority_engine import (
    AuthorityDecision,
    AuthorityEngine,
    AuthorityRequest,
    RiskTier,
)

logger = logging.getLogger(__name__)

# Simulation type → risk tier (PentAGI bounded autonomy)
SIMULATION_RISK_MAP: Dict[str, RiskTier] = {
    "credential_test": RiskTier.LOW,
    "phishing_sim": RiskTier.LOW,
    "pivot_test": RiskTier.MEDIUM,
    "exfil_test": RiskTier.MEDIUM,
    "lateral_movement": RiskTier.HIGH,
    "privilege_escalation": RiskTier.CRITICAL,
}

# Simulations that require Guardian approval before execution
REQUIRES_GUARDIAN_APPROVAL: Tuple[RiskTier, ...] = (
    RiskTier.MEDIUM,
    RiskTier.HIGH,
    RiskTier.CRITICAL,
)

# Singleton
_authority_engine: Optional[AuthorityEngine] = None


def _get_authority() -> AuthorityEngine:
    global _authority_engine
    if _authority_engine is None:
        from mycosoft_mas.guardian.constitutional_guardian import ConstitutionalGuardian

        guardian = ConstitutionalGuardian()
        _authority_engine = AuthorityEngine(guardian=guardian)
    return _authority_engine


async def check_redteam_authority(
    simulation_type: str,
    requester: str = "api_user",
    target: Optional[str] = None,
    justification: str = "",
) -> Tuple[bool, str, Optional[str]]:
    """
    Check Guardian/AVANI approval for red-team simulation.

    Returns:
        (approved, reason, approved_by)
        - approved: True if execution may proceed
        - reason: Human-readable explanation
        - approved_by: "guardian" | "avani" | "low_risk" | None
    """
    risk_tier = SIMULATION_RISK_MAP.get(simulation_type, RiskTier.MEDIUM)

    if risk_tier not in REQUIRES_GUARDIAN_APPROVAL:
        return True, "Low-risk simulation; no Guardian approval required", "low_risk"

    engine = _get_authority()
    action = f"redteam:{simulation_type}"
    context: Dict[str, Any] = {
        "simulation_type": simulation_type,
        "target": target,
        "risk_tier": risk_tier.value,
    }

    request = AuthorityRequest(
        action=action,
        requester=requester,
        context=context,
        risk_tier=risk_tier,
        justification=justification or f"Red-team simulation: {simulation_type}",
    )

    result = await engine.authorize(request)

    if result.decision == AuthorityDecision.GRANTED:
        return True, result.reason, "guardian"
    if result.decision == AuthorityDecision.ESCALATED:
        return False, f"Escalated for human approval: {result.reason}", None
    return False, f"Denied: {result.reason}", None


def get_simulation_risk_tier(simulation_type: str) -> str:
    """Return risk tier string for a simulation type."""
    return SIMULATION_RISK_MAP.get(simulation_type, RiskTier.MEDIUM).value


def requires_guardian_approval(simulation_type: str) -> bool:
    """Return True if simulation type requires Guardian approval."""
    risk = SIMULATION_RISK_MAP.get(simulation_type, RiskTier.MEDIUM)
    return risk in REQUIRES_GUARDIAN_APPROVAL
