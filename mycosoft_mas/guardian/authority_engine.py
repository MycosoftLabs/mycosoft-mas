"""
Authority Engine — Unified authorization pipeline.

Composes existing systems (RBAC, SafetyGates, StakeholderGates, MoralPrecedence)
into a single authorization pipeline without modifying any of them.

Pipeline: moral_check → risk_assessment → guardian_review → decision

Architecture: March 9, 2026
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from mycosoft_mas.guardian.constitutional_guardian import (
    ConstitutionalGuardian,
    GuardianVerdict,
)
from mycosoft_mas.guardian.moral_precedence import MoralPrecedenceEngine

logger = logging.getLogger(__name__)


class RiskTier(str, Enum):
    """Risk classification for actions."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuthorityDecision(str, Enum):
    """Final authority decision."""

    GRANTED = "granted"
    DENIED = "denied"
    ESCALATED = "escalated"  # Requires human approval
    DEFERRED = "deferred"  # Needs more information


@dataclass
class AuthorityRequest:
    """A request for authorization to perform an action."""

    action: str
    requester: str
    context: Dict[str, Any] = field(default_factory=dict)
    risk_tier: Optional[RiskTier] = None
    target_files: List[str] = field(default_factory=list)
    justification: str = ""


@dataclass
class AuthorityResult:
    """Result of an authority check."""

    decision: AuthorityDecision
    reason: str
    risk_tier: RiskTier
    moral_approved: bool
    guardian_verdict: Optional[GuardianVerdict] = None
    warnings: List[str] = field(default_factory=list)
    checked_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    pipeline_stages: List[Dict[str, Any]] = field(default_factory=list)


# Action patterns mapped to risk tiers
_RISK_PATTERNS: Dict[str, RiskTier] = {
    "read": RiskTier.LOW,
    "query": RiskTier.LOW,
    "search": RiskTier.LOW,
    "list": RiskTier.LOW,
    "write": RiskTier.MEDIUM,
    "create": RiskTier.MEDIUM,
    "update": RiskTier.MEDIUM,
    "edit": RiskTier.MEDIUM,
    "delete": RiskTier.HIGH,
    "deploy": RiskTier.HIGH,
    "modify_infrastructure": RiskTier.HIGH,
    "access_credentials": RiskTier.HIGH,
    "modify_permissions": RiskTier.CRITICAL,
    "self_modify": RiskTier.CRITICAL,
    "escalate_privileges": RiskTier.CRITICAL,
    "emergency": RiskTier.CRITICAL,
    "bulk_delete": RiskTier.CRITICAL,
    "drop_table": RiskTier.CRITICAL,
}


class AuthorityEngine:
    """
    Unified authority pipeline composing existing security systems.

    The pipeline runs in strict order:
    1. Moral precedence check (hard constraints, never overridable)
    2. Risk tier assessment
    3. Guardian review (independent constitutional check)

    Does NOT modify existing RBAC, SafetyGates, or StakeholderGates.
    Instead, it wraps them into a single decision point.
    """

    def __init__(
        self,
        guardian: ConstitutionalGuardian,
        moral_engine: Optional[MoralPrecedenceEngine] = None,
    ) -> None:
        self._guardian = guardian
        self._moral = moral_engine or MoralPrecedenceEngine()
        self._decision_log: List[Dict[str, Any]] = []

    async def authorize(self, request: AuthorityRequest) -> AuthorityResult:
        """
        Run the full authorization pipeline.

        Returns a decision with full audit trail of which checks passed/failed.
        """
        stages: List[Dict[str, Any]] = []
        warnings: List[str] = []

        # Stage 1: Moral precedence check (hard constraints)
        moral_result = self._moral.evaluate(request.action, request.context)
        stages.append(
            {
                "stage": "moral_precedence",
                "passed": moral_result.approved,
                "details": moral_result.assessment_details,
                "violated_rules": [r.name for r in moral_result.violated_rules],
            }
        )
        if moral_result.warnings:
            warnings.extend(moral_result.warnings)

        if not moral_result.approved:
            result = AuthorityResult(
                decision=AuthorityDecision.DENIED,
                reason=f"Moral precedence violation: {moral_result.assessment_details}",
                risk_tier=RiskTier.CRITICAL,
                moral_approved=False,
                warnings=warnings,
                pipeline_stages=stages,
            )
            self._log_decision(request, result)
            return result

        # Stage 2: Risk tier assessment
        risk_tier = request.risk_tier or self._assess_risk(request.action)
        stages.append(
            {
                "stage": "risk_assessment",
                "risk_tier": risk_tier.value,
            }
        )

        # Stage 3: Guardian constitutional review
        guardian_result = await self._guardian.review_action(
            action=request.action,
            context={
                **request.context,
                "target_files": request.target_files,
                "risk_tier": risk_tier.value,
            },
            requester=request.requester,
        )
        stages.append(
            {
                "stage": "guardian_review",
                "verdict": guardian_result.verdict.value,
                "reason": guardian_result.reason,
            }
        )
        if guardian_result.tripwire_alerts:
            warnings.extend(guardian_result.tripwire_alerts)

        # Map guardian verdict to authority decision
        verdict_map = {
            GuardianVerdict.APPROVE: AuthorityDecision.GRANTED,
            GuardianVerdict.DENY: AuthorityDecision.DENIED,
            GuardianVerdict.PAUSE: AuthorityDecision.ESCALATED,
            GuardianVerdict.DEGRADE: AuthorityDecision.ESCALATED,
            GuardianVerdict.SEVER: AuthorityDecision.DENIED,
        }
        decision = verdict_map.get(guardian_result.verdict, AuthorityDecision.DENIED)

        result = AuthorityResult(
            decision=decision,
            reason=guardian_result.reason,
            risk_tier=risk_tier,
            moral_approved=True,
            guardian_verdict=guardian_result.verdict,
            warnings=warnings,
            pipeline_stages=stages,
        )
        self._log_decision(request, result)
        return result

    def _assess_risk(self, action: str) -> RiskTier:
        """Assess risk tier based on action patterns."""
        action_lower = action.lower().replace(" ", "_")

        # Check exact matches first
        if action_lower in _RISK_PATTERNS:
            return _RISK_PATTERNS[action_lower]

        # Check prefix matches
        for pattern, tier in _RISK_PATTERNS.items():
            if action_lower.startswith(pattern):
                return tier

        # Default to medium for unknown actions
        return RiskTier.MEDIUM

    def _log_decision(
        self, request: AuthorityRequest, result: AuthorityResult
    ) -> None:
        """Log the authority decision for audit."""
        self._decision_log.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": request.action,
                "requester": request.requester,
                "decision": result.decision.value,
                "risk_tier": result.risk_tier.value,
                "moral_approved": result.moral_approved,
                "warnings": result.warnings,
            }
        )

    def get_decision_log(self) -> List[Dict[str, Any]]:
        """Return the authority decision log."""
        return list(self._decision_log)
