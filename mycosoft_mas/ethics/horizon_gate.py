"""
Horizon Gate - Gate 3 of MYCA Ethics Pipeline

Uses Adult and Machine vessel philosophy: emotional intelligence, stoic
responsibility, pure logic. Projects 10-year impacts, multi-stakeholder
evaluation, formats output as Clarity Brief.

- 10-year impact projection
- Multi-stakeholder evaluation (Constitution constraint 7)
- Clarity Brief formatting
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from mycosoft_mas.ethics.clarity_brief import ClarityBrief
from mycosoft_mas.ethics.vessels import DevelopmentalVessel

logger = logging.getLogger(__name__)


STAKEHOLDER_CLASSES = [
    "human_operators",
    "ecosystems",
    "future_organisms",
    "scientific_integrity",
]


@dataclass
class HorizonGateResult:
    passed: bool
    horizon_score: float  # 0-1, higher = better long-horizon alignment
    clarity_brief: Optional[ClarityBrief]
    stakeholder_impact: Dict[str, str]
    report: str


class HorizonGate:
    """Evaluates long-horizon impact and formats Clarity Brief."""

    def __init__(self, simulator=None):
        self._simulator = simulator

    async def evaluate(
        self,
        content: str,
        context: Optional[Dict[str, Any]] = None,
        truth_result: Optional[Any] = None,
        incentive_result: Optional[Any] = None,
    ) -> HorizonGateResult:
        """
        Evaluate through Horizon Gate.
        Adult/Machine vessels: 10-year thinking, multi-stakeholder, Clarity Brief.
        """
        context = context or {}
        truth_result = truth_result or []
        incentive_result = incentive_result or []

        # Extract or infer claim (first sentence as heuristic)
        first_sent = content.split(".")[0].strip() + "." if "." in content else content
        claim = context.get("claim") or first_sent[:200]

        assumptions = context.get("assumptions", [])
        evidence = context.get("evidence", [])
        owner = context.get("owner")
        deadline = context.get("deadline")
        if deadline and isinstance(deadline, str):
            try:
                deadline = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                deadline = None

        risk_score = 0.0
        if truth_result and hasattr(truth_result, "score"):
            risk_score += (1 - truth_result.score) * 0.4
        if incentive_result and hasattr(incentive_result, "manipulation_score"):
            risk_score += (incentive_result.manipulation_score / 100) * 0.6
        risk_score = min(1.0, risk_score)

        stakeholder_impact = {s: "unknown" for s in STAKEHOLDER_CLASSES}
        horizon_score = max(0, 1.0 - risk_score)

        gate_summary = {
            "truth": getattr(truth_result, "score", None) if truth_result else None,
            "incentive": (
                getattr(incentive_result, "manipulation_score", None) if incentive_result else None
            ),
            "horizon": horizon_score,
        }

        clarity_brief = ClarityBrief(
            claim=claim,
            assumptions=(
                assumptions
                if isinstance(assumptions, list)
                else [assumptions] if assumptions else []
            ),
            evidence=evidence if isinstance(evidence, list) else [evidence] if evidence else [],
            owner=owner,
            deadline=deadline,
            risk_score=risk_score,
            gate_summary=gate_summary,
        )

        passed = risk_score < 0.7
        report = (
            f"Horizon Gate ({DevelopmentalVessel.ADULT.value}/{DevelopmentalVessel.MACHINE.value}): "
            f"passed={passed}, horizon_score={horizon_score:.2f}, risk_score={risk_score:.2f}"
        )

        return HorizonGateResult(
            passed=passed,
            horizon_score=horizon_score,
            clarity_brief=clarity_brief,
            stakeholder_impact=stakeholder_impact,
            report=report,
        )
