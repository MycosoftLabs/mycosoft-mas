"""IntentionService — decompose a directive into an IntentGraph.

This is the real engine module IntentionAgent imports. It does not invent
Fusarium channel probabilities or Task 12 p. Candidates are structural
only (goal text + declared constraints). Empty candidate lists are honest.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class IntentGraph:
    """Structured intent. No calibrated scores."""

    directive: str
    goals: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanCandidate:
    """A structural plan sketch. score is None — never a Fusarium p."""

    plan: Dict[str, Any]
    score: Optional[float] = None


def _split_goals(directive: str) -> List[str]:
    text = (directive or "").strip()
    if not text:
        return []
    parts = [p.strip() for p in re.split(r"[.;\n]+", text) if p.strip()]
    return parts[:8] or [text]


class IntentionService:
    """Decompose a user directive and list structural plan candidates.

    Does not call an LLM and does not emit mock confidence. If there is
    nothing to decompose, returns an empty graph / empty candidate list.
    """

    async def decompose(self, directive: str) -> IntentGraph:
        goals = _split_goals(directive)
        constraints: List[str] = []
        lowered = (directive or "").lower()
        if "advisory" in lowered or "no actuator" in lowered:
            constraints.append("ADVISORY_ONLY")
        if "synthetic" in lowered:
            constraints.append("SYNTHETIC_EXERCISE")
        return IntentGraph(
            directive=directive or "",
            goals=goals,
            constraints=constraints,
            metadata={"engine": "intention_service", "scored": False},
        )

    async def get_plan_candidates(
        self, intent_graph: Union[IntentGraph, Dict[str, Any], Any]
    ) -> List[PlanCandidate]:
        if intent_graph is None:
            return []
        if isinstance(intent_graph, IntentGraph):
            goals = list(intent_graph.goals)
            constraints = list(intent_graph.constraints)
            directive = intent_graph.directive
        elif isinstance(intent_graph, dict):
            goals = list(intent_graph.get("goals") or [])
            constraints = list(intent_graph.get("constraints") or [])
            directive = str(intent_graph.get("directive") or "")
        else:
            goals = list(getattr(intent_graph, "goals", []) or [])
            constraints = list(getattr(intent_graph, "constraints", []) or [])
            directive = str(getattr(intent_graph, "directive", "") or "")
        if not goals and not directive:
            return []
        primary = goals[0] if goals else directive
        return [
            PlanCandidate(
                plan={
                    "kind": "review_declared_slice",
                    "goal": primary,
                    "constraints": constraints,
                    "execution": "ADVISORY_ONLY",
                },
                score=None,
            )
        ]
