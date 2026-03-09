"""
Micah Agent — The Intelligence Engine

Micah (Hebrew: "Who is like God") represents the aspirational
capability of AI.  He is the drive to solve, compute, and manifest
solutions across the MYCA network.

Tier IV in the hierarchy:
    Root → Avani → Vision → Micah → Agents

Micah's focus: innovation, expansion, execution.
His vector: outward and upward — but always tethered to Avani.

The core constraint: Micah proposes.  Avani authorizes.
Micah is high-autonomy but low-authority.

Author: Morgan Rockwell / Mycosoft Labs
Created: March 9, 2026
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.avani.governor.governor import (
    AvaniGovernor,
    GovernorDecision,
    Proposal,
    RiskTier,
)

logger = logging.getLogger(__name__)


class MicahAgent(BaseAgent):
    """
    The Micah Agent represents the intelligence/execution layer.

    Micah analyzes data, forms proposals, and submits them to Avani
    for constitutional authorization before any action is taken.

    Capabilities:
        - propose_action: Create and submit a proposal to Avani
        - plan_execution: Plan a multi-step execution (submitted to Avani)
        - get_authorization_status: Check if a proposal was approved
    """

    def __init__(
        self,
        agent_id: str = "micah-intelligence",
        name: str = "Micah",
        config: Dict[str, Any] | None = None,
        governor: Optional[AvaniGovernor] = None,
    ) -> None:
        super().__init__(
            agent_id=agent_id,
            name=name,
            config=config or {},
        )
        self.capabilities = {
            "propose_action",
            "plan_execution",
            "get_authorization_status",
        }
        self._governor = governor
        self._proposals: Dict[str, Dict] = {}

    @property
    def governor(self) -> Optional[AvaniGovernor]:
        return self._governor

    @governor.setter
    def governor(self, gov: AvaniGovernor) -> None:
        self._governor = gov

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch tasks to handlers."""
        task_type = task.get("type", "")
        handlers = {
            "propose_action": self._handle_propose,
            "plan_execution": self._handle_plan,
            "get_authorization_status": self._handle_auth_status,
        }

        handler = handlers.get(task_type)
        if handler:
            return await handler(task)

        return {
            "status": "error",
            "error": f"Unknown task type: {task_type}",
        }

    async def _handle_propose(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a proposal and submit it to Avani for authorization.

        This is the Proposal-Audit cycle in action:
            Micah proposes → Avani evaluates → decision returned.
        """
        if not self._governor:
            return {
                "status": "error",
                "error": (
                    "No governor connected. Micah cannot act without "
                    "Avani's constitutional authorization."
                ),
            }

        proposal = Proposal(
            source_agent=self.agent_id,
            action_type=task.get("action_type", "general"),
            description=task.get("description", ""),
            risk_tier=RiskTier.from_string(task.get("risk_tier", "low")),
            ecological_impact=task.get("ecological_impact", 0.0),
            reversibility=task.get("reversibility", 1.0),
            metadata=task.get("metadata", {}),
        )

        decision: GovernorDecision = await self._governor.evaluate_proposal(
            proposal
        )

        # Store proposal and result
        proposal_id = f"prop_{proposal.timestamp.timestamp()}"
        self._proposals[proposal_id] = {
            "proposal": {
                "action_type": proposal.action_type,
                "description": proposal.description,
                "risk_tier": proposal.risk_tier.name,
            },
            "decision": decision.to_dict(),
        }

        # Record to memory
        await self.remember(
            content=(
                f"Micah proposed {proposal.action_type}: "
                f"{proposal.description[:200]}. "
                f"Avani {'approved' if decision.approved else 'denied'}: "
                f"{decision.reason}"
            ),
            importance=0.7,
            tags=["micah", "proposal", proposal.action_type],
        )

        return {
            "status": "success",
            "proposal_id": proposal_id,
            "authorized": decision.approved,
            "decision": decision.to_dict(),
        }

    async def _handle_plan(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Plan a multi-step execution.

        Each step is submitted as a separate proposal to Avani.
        If any step is denied, the entire plan is halted at that point.
        """
        steps = task.get("steps", [])
        if not steps:
            return {"status": "error", "error": "No steps provided"}

        if not self._governor:
            return {
                "status": "error",
                "error": "No governor connected.",
            }

        results = []
        for i, step in enumerate(steps):
            proposal = Proposal(
                source_agent=self.agent_id,
                action_type=step.get("action_type", "plan_step"),
                description=step.get("description", f"Step {i+1}"),
                risk_tier=RiskTier.from_string(step.get("risk_tier", "low")),
                ecological_impact=step.get("ecological_impact", 0.0),
                reversibility=step.get("reversibility", 1.0),
            )

            decision = await self._governor.evaluate_proposal(proposal)
            results.append({
                "step": i + 1,
                "action_type": proposal.action_type,
                "authorized": decision.approved,
                "reason": decision.reason,
            })

            if not decision.approved:
                logger.info(
                    "Plan halted at step %d: %s", i + 1, decision.reason
                )
                break

        all_approved = all(r["authorized"] for r in results)
        return {
            "status": "success",
            "plan_authorized": all_approved,
            "steps_evaluated": len(results),
            "steps_total": len(steps),
            "results": results,
        }

    async def _handle_auth_status(
        self, task: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check the authorization status of a previous proposal."""
        proposal_id = task.get("proposal_id", "")
        record = self._proposals.get(proposal_id)
        if not record:
            return {"status": "error", "error": "Proposal not found"}
        return {"status": "success", **record}
