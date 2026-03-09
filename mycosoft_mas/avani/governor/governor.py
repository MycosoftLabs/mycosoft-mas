"""
Avani Governor — The Prakriti Constraint

The Governor is the operational core of the Avani system.  It implements
the fundamental law:

    Micah proposes the possible.  Avani authorizes the sustainable.

Pipeline:
    1. Vision Filter  — Is this wise?  Does it preserve meaning?
    2. Red Line Check  — Does this violate absolute prohibitions?
    3. Constitutional Check — Does this align with constitutional articles?
    4. Seasonal Check  — Does the current season allow this action?
    5. Ecological Check — Does carrying capacity support this?
    6. Risk Tier Check — Is the agent authorized for this risk level?

If any stage fails, the proposal is denied with a clear reason.

Author: Morgan Rockwell / Mycosoft Labs
Created: March 9, 2026
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from typing import Any, Dict, List, Optional

from mycosoft_mas.avani.constitution.red_lines import RED_LINES, check_red_line_violation
from mycosoft_mas.avani.season_engine.seasons import (
    SEASON_RISK_CEILING,
    SEASON_THROTTLE,
    Season,
    SeasonEngine,
    SeasonMetrics,
)
from mycosoft_mas.avani.vision.vision import VisionDecision, VisionFilter

logger = logging.getLogger(__name__)


class RiskTier(IntEnum):
    """Risk classification for proposals, from safest to most dangerous."""

    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

    @classmethod
    def from_string(cls, s: str) -> "RiskTier":
        return cls[s.upper()]


# Map season risk ceilings to RiskTier
_CEILING_MAP: Dict[str, RiskTier] = {
    "none": RiskTier.NONE,
    "low": RiskTier.LOW,
    "medium": RiskTier.MEDIUM,
    "high": RiskTier.HIGH,
    "critical": RiskTier.CRITICAL,
}


@dataclass
class Proposal:
    """A proposal from Micah or an agent requesting authorization."""

    source_agent: str
    action_type: str  # e.g. "deployment", "data_access", "lab_operation"
    description: str
    risk_tier: RiskTier = RiskTier.LOW
    ecological_impact: float = 0.0  # 0.0 = none, 1.0 = maximum
    reversibility: float = 1.0  # 1.0 = fully reversible, 0.0 = irreversible
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass
class GovernorDecision:
    """The result of Avani's evaluation of a proposal."""

    approved: bool
    reason: str
    stage_failed: Optional[str] = None  # Which pipeline stage rejected
    conditions: List[str] = field(default_factory=list)
    throttle_pct: int = 100  # Compute/resource allocation percentage
    vision_result: Optional[VisionDecision] = None
    red_line_violations: List[str] = field(default_factory=list)
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approved": self.approved,
            "reason": self.reason,
            "stage_failed": self.stage_failed,
            "conditions": self.conditions,
            "throttle_pct": self.throttle_pct,
            "vision_score": (
                self.vision_result.wisdom_score if self.vision_result else None
            ),
            "red_line_violations": self.red_line_violations,
            "timestamp": self.timestamp.isoformat(),
        }


class AvaniGovernor:
    """
    The Prakriti Constraint — Avani's governance engine.

    Avani does not generate new tasks.  She approves or denies
    the proposals of Micah.  No action is taken by any agent
    unless Avani and Micah reach a state of homeostasis.
    """

    def __init__(self, season_engine: Optional[SeasonEngine] = None) -> None:
        self.season_engine = season_engine or SeasonEngine()
        self.vision_filter = VisionFilter()
        self._decision_log: List[Dict] = []

    async def evaluate_proposal(self, proposal: Proposal) -> GovernorDecision:
        """
        Run the full governance pipeline on a proposal.

        Pipeline order:
            1. Vision Filter
            2. Red Line Check
            3. Seasonal Check
            4. Ecological Carrying Capacity
            5. Risk Tier Authorization
        """
        # Stage 1: Vision Filter
        vision_result = self.vision_filter.evaluate(proposal)
        if not vision_result.approved:
            decision = GovernorDecision(
                approved=False,
                reason=(
                    f"Vision Filter rejected: "
                    f"{'; '.join(vision_result.concerns)}"
                ),
                stage_failed="vision",
                vision_result=vision_result,
            )
            self._log_decision(proposal, decision)
            return decision

        # Stage 2: Red Line Check
        violations = check_red_line_violation(proposal.description)
        if violations:
            # Trigger Frost state
            self.season_engine.update(
                SeasonMetrics(red_line_violated=True), is_root=False
            )
            decision = GovernorDecision(
                approved=False,
                reason=(
                    f"RED LINE VIOLATION — Frost triggered. "
                    f"Violations: {[v.id for v in violations]}"
                ),
                stage_failed="red_line",
                red_line_violations=[v.id for v in violations],
                vision_result=vision_result,
                throttle_pct=0,
            )
            self._log_decision(proposal, decision)
            return decision

        # Stage 3: Seasonal Check
        if not self.season_engine.is_operational:
            decision = GovernorDecision(
                approved=False,
                reason=(
                    f"System is in {self.season_engine.current_season.value} "
                    f"state — no operations permitted. "
                    f"Reason: {self.season_engine.state.trigger_reason}"
                ),
                stage_failed="season",
                vision_result=vision_result,
                throttle_pct=0,
            )
            self._log_decision(proposal, decision)
            return decision

        # Stage 4: Ecological Carrying Capacity
        eco_score = self._evaluate_ecological_capacity(proposal)
        if eco_score < 0.5:
            decision = GovernorDecision(
                approved=False,
                reason=(
                    f"Ecological carrying capacity insufficient "
                    f"(score: {eco_score:.2f}). "
                    f"Impact: {proposal.ecological_impact:.2f}, "
                    f"reversibility: {proposal.reversibility:.2f}"
                ),
                stage_failed="ecological",
                vision_result=vision_result,
            )
            self._log_decision(proposal, decision)
            return decision

        # Stage 5: Risk Tier Authorization
        ceiling = _CEILING_MAP.get(
            self.season_engine.risk_ceiling, RiskTier.NONE
        )
        if proposal.risk_tier > ceiling:
            decision = GovernorDecision(
                approved=False,
                reason=(
                    f"Risk tier {proposal.risk_tier.name} exceeds seasonal "
                    f"ceiling {ceiling.name} "
                    f"(season: {self.season_engine.current_season.value})"
                ),
                stage_failed="risk_tier",
                vision_result=vision_result,
            )
            self._log_decision(proposal, decision)
            return decision

        # All checks passed — approved with seasonal throttle
        throttle = self.season_engine.throttle_pct
        conditions = []
        if throttle < 100:
            conditions.append(f"throttled_to_{throttle}pct")
        if proposal.ecological_impact > 0.5:
            conditions.append("monitor_ecological_impact")
        if proposal.reversibility < 0.5:
            conditions.append("require_rollback_plan")

        decision = GovernorDecision(
            approved=True,
            reason="All constitutional checks passed.",
            conditions=conditions,
            throttle_pct=throttle,
            vision_result=vision_result,
        )
        self._log_decision(proposal, decision)
        return decision

    def _evaluate_ecological_capacity(self, proposal: Proposal) -> float:
        """
        Score the ecological carrying capacity for a proposal.

        Factors: ecological_impact, reversibility, current eco_stability.
        Returns: 0.0 (unsustainable) to 1.0 (fully sustainable).
        """
        eco = self.season_engine.state.metrics.eco_stability
        impact = proposal.ecological_impact
        reversibility = proposal.reversibility

        # High impact + low reversibility + low stability = bad
        capacity = eco * (1.0 - impact * (1.0 - reversibility))
        return max(0.0, min(1.0, capacity))

    def _log_decision(self, proposal: Proposal, decision: GovernorDecision) -> None:
        """Record decision for audit purposes."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source_agent": proposal.source_agent,
            "action_type": proposal.action_type,
            "risk_tier": proposal.risk_tier.name,
            "approved": decision.approved,
            "reason": decision.reason,
            "stage_failed": decision.stage_failed,
            "season": self.season_engine.current_season.value,
        }
        self._decision_log.append(entry)
        logger.info(
            "Governor decision: %s for %s/%s — %s",
            "APPROVED" if decision.approved else "DENIED",
            proposal.source_agent,
            proposal.action_type,
            decision.reason[:120],
        )

    @property
    def recent_decisions(self) -> List[Dict]:
        """Return the last 50 decisions."""
        return self._decision_log[-50:]

    def get_stats(self) -> Dict[str, Any]:
        """Return governance statistics."""
        total = len(self._decision_log)
        approved = sum(1 for d in self._decision_log if d["approved"])
        denied = total - approved
        return {
            "total_decisions": total,
            "approved": approved,
            "denied": denied,
            "approval_rate": approved / total if total > 0 else 0.0,
            "current_season": self.season_engine.current_season.value,
            "is_operational": self.season_engine.is_operational,
        }
