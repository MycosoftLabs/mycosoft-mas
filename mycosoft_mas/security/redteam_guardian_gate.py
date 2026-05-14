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

    try:
        from mycosoft_mas.avani.enforcement import AvaniActionPreflight, require_action_preflight
        from mycosoft_mas.core.routers import avani_router

        await avani_router.ensure_runtime_restored()
        avani_decision = await require_action_preflight(
            avani_router.get_governor(),
            AvaniActionPreflight(
                source_agent="redteam_guardian_gate",
                action_type="red_team",
                description=justification or f"Red-team simulation: {simulation_type}",
                route=f"/api/redteam/{simulation_type}",
                risk_tier=risk_tier.value,
                ecological_impact=0.0,
                reversibility=0.4 if risk_tier.value in {"high", "critical"} else 0.7,
                metadata={"simulation_type": simulation_type, "target": target},
            ),
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("AVANI denied red-team preflight: %s", exc)
        return False, f"AVANI denied red-team preflight: {exc}", None

    if risk_tier not in REQUIRES_GUARDIAN_APPROVAL:
        return True, f"Low-risk simulation approved by AVANI: {avani_decision.get('reason')}", "low_risk"

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
        return True, f"{result.reason} AVANI: {avani_decision.get('reason')}", "guardian"
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
