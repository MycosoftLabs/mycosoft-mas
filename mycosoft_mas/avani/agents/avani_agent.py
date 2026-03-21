"""
Avani Agent — The Constitutional Governor

Avani (Sanskrit: "Earth") is the safeguard layer of the Mycosoft MAS.
She does not generate new tasks — she approves or denies proposals
from Micah and the MYCA agents.

Tier II in the hierarchy:
    Root → Avani → Vision → Micah → Agents

Avani's focus: preservation, grounding, ethics.
Her vector: inward and downward (rooted).

Author: Morgan Rockwell / Mycosoft Labs
Created: March 9, 2026
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.avani.governor.governor import (
    AvaniGovernor,
    GovernorDecision,
    Proposal,
    RiskTier,
)
from mycosoft_mas.avani.season_engine.seasons import (
    Season,
    SeasonEngine,
    SeasonMetrics,
)

logger = logging.getLogger(__name__)


class AvaniAgent(BaseAgent):
    """
    The Avani Agent wraps the Governor, Season Engine, and Vision Filter
    into a standard BaseAgent that participates in the MAS messaging system.

    Capabilities:
        - evaluate_proposal: Run the governance pipeline on a proposal
        - check_season: Return current seasonal state
        - update_season: Update season metrics and evaluate transitions
        - get_constitution: Return constitutional articles
        - get_vision: Return vision principles
        - get_stats: Return governance statistics
    """

    def __init__(
        self,
        agent_id: str = "avani-governor",
        name: str = "Avani",
        config: Dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            agent_id=agent_id,
            name=name,
            config=config or {},
        )
        self.capabilities = {
            "evaluate_proposal",
            "check_season",
            "update_season",
            "get_constitution",
            "get_vision",
            "get_stats",
        }
        self.season_engine = SeasonEngine(initial_season=Season.SPRING)
        self.governor = AvaniGovernor(season_engine=self.season_engine)

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch tasks to the appropriate handler."""
        task_type = task.get("type", "")
        handlers = {
            "evaluate_proposal": self._handle_evaluate,
            "check_season": self._handle_check_season,
            "update_season": self._handle_update_season,
            "get_constitution": self._handle_get_constitution,
            "get_vision": self._handle_get_vision,
            "get_stats": self._handle_get_stats,
        }

        handler = handlers.get(task_type)
        if handler:
            return await handler(task)

        return {
            "status": "error",
            "error": f"Unknown task type: {task_type}",
            "available_types": list(handlers.keys()),
        }

    async def _handle_evaluate(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate a proposal through the governance pipeline."""
        try:
            proposal = Proposal(
                source_agent=task.get("source_agent", "unknown"),
                action_type=task.get("action_type", "unknown"),
                description=task.get("description", ""),
                risk_tier=RiskTier.from_string(task.get("risk_tier", "low")),
                ecological_impact=task.get("ecological_impact", 0.0),
                reversibility=task.get("reversibility", 1.0),
                metadata=task.get("metadata", {}),
            )

            decision: GovernorDecision = await self.governor.evaluate_proposal(proposal)

            # Record to memory
            await self.remember(
                content=(
                    f"Avani {'approved' if decision.approved else 'denied'} "
                    f"proposal from {proposal.source_agent}: "
                    f"{proposal.action_type} — {decision.reason}"
                ),
                importance=0.8 if not decision.approved else 0.5,
                tags=["avani", "governance", "decision"],
            )

            return {
                "status": "success",
                "decision": decision.to_dict(),
            }

        except Exception as e:
            logger.error("Avani evaluation error: %s", e)
            return {"status": "error", "error": str(e)}

    async def _handle_check_season(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Return the current seasonal state."""
        return {
            "status": "success",
            "season": self.season_engine.to_dict(),
        }

    async def _handle_update_season(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Update season metrics and evaluate transitions."""
        metrics = SeasonMetrics(
            eco_stability=task.get("eco_stability", 1.0),
            founder_latency_hours=task.get("founder_latency_hours", 0.0),
            toxicity_detected=task.get("toxicity_detected", False),
            critical_error=task.get("critical_error", False),
            red_line_violated=task.get("red_line_violated", False),
            all_systems_green=task.get("all_systems_green", True),
        )
        is_root = task.get("is_root", False)

        result = self.season_engine.update(metrics, is_root=is_root)
        transitioned = result is not None

        if transitioned:
            await self.remember(
                content=(
                    f"Season transitioned to "
                    f"{self.season_engine.current_season.value}: "
                    f"{self.season_engine.state.trigger_reason}"
                ),
                importance=0.9,
                tags=["avani", "season", "transition"],
            )

        return {
            "status": "success",
            "transitioned": transitioned,
            "season": self.season_engine.to_dict(),
        }

    async def _handle_get_constitution(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Return constitutional articles."""
        from mycosoft_mas.avani.constitution.articles import CONSTITUTION

        articles = {
            k: {"title": v.title, "text": v.text, "tier": v.tier.value}
            for k, v in CONSTITUTION.items()
        }
        return {"status": "success", "articles": articles}

    async def _handle_get_vision(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Return vision principles."""
        from mycosoft_mas.avani.vision.vision import VISION_PRINCIPLES

        principles = [
            {
                "id": p.id,
                "statement": p.statement,
                "weight": p.weight,
                "question": p.question,
            }
            for p in VISION_PRINCIPLES
        ]
        return {"status": "success", "principles": principles}

    async def _handle_get_stats(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Return governance statistics."""
        return {
            "status": "success",
            "stats": self.governor.get_stats(),
        }
