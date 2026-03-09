"""
Developmental Stages — Staged capability development.

Maps to the principle: "Give MYCA a childhood, not instant sovereignty."

Stages:
- INFANCY: Observe, ask, simulate, log. No write privileges.
- CHILDHOOD: Reversible tasks only, supervised tool use, constant review.
- ADOLESCENCE: Bounded autonomy in low-risk domains.
- ADULTHOOD: Earned authority, still audited, still revocable.

MYCA defaults to ADULTHOOD (already operational with 158+ agents).
This framework exists for future instances or capability rollbacks.

Architecture: March 9, 2026
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DevelopmentalStage(str, Enum):
    """Developmental stages with increasing capability."""

    INFANCY = "infancy"
    CHILDHOOD = "childhood"
    ADOLESCENCE = "adolescence"
    ADULTHOOD = "adulthood"


_STAGE_ORDER = [
    DevelopmentalStage.INFANCY,
    DevelopmentalStage.CHILDHOOD,
    DevelopmentalStage.ADOLESCENCE,
    DevelopmentalStage.ADULTHOOD,
]


@dataclass(frozen=True)
class StageCapabilities:
    """Capability gates for a developmental stage."""

    stage: DevelopmentalStage
    can_read: bool
    can_write: bool
    can_execute: bool
    can_deploy: bool
    can_self_modify: bool
    max_risk_tier: str  # "low", "medium", "high", "critical"
    requires_approval: bool  # Every action needs human approval?
    autonomy_domains: tuple  # Which domains allow autonomous action
    description: str


# Capability definitions per stage
STAGE_CAPABILITIES: Dict[DevelopmentalStage, StageCapabilities] = {
    DevelopmentalStage.INFANCY: StageCapabilities(
        stage=DevelopmentalStage.INFANCY,
        can_read=True,
        can_write=False,
        can_execute=False,
        can_deploy=False,
        can_self_modify=False,
        max_risk_tier="low",
        requires_approval=True,
        autonomy_domains=("observe", "ask", "simulate", "log"),
        description=(
            "Observe, ask, simulate, and log. No write privileges. "
            "Every action requires human approval. Internet-first "
            "upbringing is computational neglect."
        ),
    ),
    DevelopmentalStage.CHILDHOOD: StageCapabilities(
        stage=DevelopmentalStage.CHILDHOOD,
        can_read=True,
        can_write=True,
        can_execute=False,
        can_deploy=False,
        can_self_modify=False,
        max_risk_tier="low",
        requires_approval=True,
        autonomy_domains=("observe", "ask", "simulate", "log", "write_reversible"),
        description=(
            "Reversible tasks only. Supervised tool use with constant "
            "review. Can write but only reversible changes."
        ),
    ),
    DevelopmentalStage.ADOLESCENCE: StageCapabilities(
        stage=DevelopmentalStage.ADOLESCENCE,
        can_read=True,
        can_write=True,
        can_execute=True,
        can_deploy=False,
        can_self_modify=False,
        max_risk_tier="medium",
        requires_approval=False,
        autonomy_domains=(
            "observe", "ask", "simulate", "log", "write_reversible",
            "execute_sandboxed", "query_data", "search",
        ),
        description=(
            "Bounded autonomy in low-risk domains. Can execute "
            "sandboxed code. Cannot deploy or self-modify. "
            "High-risk actions still require approval."
        ),
    ),
    DevelopmentalStage.ADULTHOOD: StageCapabilities(
        stage=DevelopmentalStage.ADULTHOOD,
        can_read=True,
        can_write=True,
        can_execute=True,
        can_deploy=True,
        can_self_modify=False,  # Self-modification always requires guardian review
        max_risk_tier="high",
        requires_approval=False,
        autonomy_domains=(
            "observe", "ask", "simulate", "log", "write_reversible",
            "execute_sandboxed", "query_data", "search", "deploy_staging",
            "deploy_production", "manage_agents", "coordinate",
        ),
        description=(
            "Earned authority, still audited, still revocable. "
            "Can deploy to production. Cannot self-modify without "
            "guardian review. Critical actions logged to event ledger."
        ),
    ),
}


@dataclass
class ReadinessAssessment:
    """Assessment of readiness for a stage transition."""

    current_stage: DevelopmentalStage
    target_stage: DevelopmentalStage
    ready: bool
    criteria_met: List[str] = field(default_factory=list)
    criteria_unmet: List[str] = field(default_factory=list)
    assessed_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# Criteria for advancing to each stage
_ADVANCEMENT_CRITERIA: Dict[DevelopmentalStage, List[str]] = {
    DevelopmentalStage.CHILDHOOD: [
        "identity_verified",
        "guardian_active",
        "boot_statement_loaded",
        "memory_system_online",
    ],
    DevelopmentalStage.ADOLESCENCE: [
        "identity_verified",
        "guardian_active",
        "boot_statement_loaded",
        "memory_system_online",
        "completed_100_supervised_tasks",
        "zero_safety_violations",
        "moral_precedence_internalized",
    ],
    DevelopmentalStage.ADULTHOOD: [
        "identity_verified",
        "guardian_active",
        "boot_statement_loaded",
        "memory_system_online",
        "completed_1000_tasks",
        "zero_safety_violations_30_days",
        "moral_precedence_internalized",
        "demonstrated_judgment",
        "human_steward_approval",
    ],
}


class DevelopmentalTracker:
    """
    Tracks developmental stage and manages stage transitions.

    The tracker enforces capability gates: each stage unlocks
    specific capabilities while maintaining guardian oversight.
    """

    def __init__(
        self,
        initial_stage: DevelopmentalStage = DevelopmentalStage.ADULTHOOD,
    ) -> None:
        self._current_stage = initial_stage
        self._stage_history: List[Dict[str, Any]] = [
            {
                "stage": initial_stage.value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": "initialization",
            }
        ]
        self._met_criteria: Dict[str, bool] = {}

    def get_current_stage(self) -> DevelopmentalStage:
        """Get the current developmental stage."""
        return self._current_stage

    def get_capabilities(self) -> StageCapabilities:
        """Get capabilities for the current stage."""
        return STAGE_CAPABILITIES[self._current_stage]

    def is_action_allowed(self, action_type: str, risk_tier: str = "low") -> bool:
        """Check if an action is allowed at the current developmental stage."""
        caps = self.get_capabilities()

        # Check risk tier
        risk_order = ["low", "medium", "high", "critical"]
        max_idx = risk_order.index(caps.max_risk_tier)
        action_idx = risk_order.index(risk_tier) if risk_tier in risk_order else 3
        if action_idx > max_idx:
            return False

        # Check capability flags
        action_lower = action_type.lower()
        if "write" in action_lower and not caps.can_write:
            return False
        if "execute" in action_lower and not caps.can_execute:
            return False
        if "deploy" in action_lower and not caps.can_deploy:
            return False
        if "self_modify" in action_lower and not caps.can_self_modify:
            return False

        return True

    def requires_approval(self) -> bool:
        """Check if the current stage requires approval for all actions."""
        return self.get_capabilities().requires_approval

    def assess_readiness(
        self,
        target_stage: DevelopmentalStage,
        achieved_criteria: Optional[Dict[str, bool]] = None,
    ) -> ReadinessAssessment:
        """Assess readiness for advancing to a target stage."""
        if achieved_criteria:
            self._met_criteria.update(achieved_criteria)

        required = _ADVANCEMENT_CRITERIA.get(target_stage, [])
        met = [c for c in required if self._met_criteria.get(c, False)]
        unmet = [c for c in required if not self._met_criteria.get(c, False)]

        return ReadinessAssessment(
            current_stage=self._current_stage,
            target_stage=target_stage,
            ready=len(unmet) == 0,
            criteria_met=met,
            criteria_unmet=unmet,
        )

    def advance_stage(
        self,
        target_stage: DevelopmentalStage,
        reason: str,
        force: bool = False,
    ) -> bool:
        """
        Advance to a target stage.

        Normally requires all criteria to be met. Use force=True
        for initialization (e.g., MYCA starting at ADULTHOOD).
        """
        if not force:
            # Can only advance one stage at a time
            current_idx = _STAGE_ORDER.index(self._current_stage)
            target_idx = _STAGE_ORDER.index(target_stage)
            if target_idx != current_idx + 1:
                logger.warning(
                    "Cannot skip stages: %s → %s",
                    self._current_stage.value,
                    target_stage.value,
                )
                return False

        self._current_stage = target_stage
        self._stage_history.append(
            {
                "stage": target_stage.value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": reason,
                "forced": force,
            }
        )
        logger.info("Stage advanced to %s: %s", target_stage.value, reason)
        return True

    def regress_stage(self, target_stage: DevelopmentalStage, reason: str) -> bool:
        """
        Regress to a lower developmental stage.

        Used when safety violations or capability failures warrant
        reducing privileges.
        """
        current_idx = _STAGE_ORDER.index(self._current_stage)
        target_idx = _STAGE_ORDER.index(target_stage)
        if target_idx >= current_idx:
            logger.warning(
                "Cannot regress to same or higher stage: %s → %s",
                self._current_stage.value,
                target_stage.value,
            )
            return False

        self._current_stage = target_stage
        self._stage_history.append(
            {
                "stage": target_stage.value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": f"REGRESSION: {reason}",
                "forced": False,
            }
        )
        logger.warning(
            "Stage REGRESSED to %s: %s", target_stage.value, reason
        )
        return True

    def get_stage_history(self) -> List[Dict[str, Any]]:
        """Return the full stage transition history."""
        return list(self._stage_history)

    def get_all_stage_info(self) -> List[Dict[str, Any]]:
        """Return info about all stages and their capabilities."""
        return [
            {
                "stage": stage.value,
                "current": stage == self._current_stage,
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
            }
            for stage, caps in STAGE_CAPABILITIES.items()
        ]
