"""
Incentive Gate - Gate 2 of MYCA Ethics Pipeline

Uses Child and Teenager vessel philosophy: naive questioning and cynical
stress-testing. Identifies manipulation, perverse incentives, dopamine hooks.

- Cui bono? Who benefits?
- Manipulation pattern detection (certainty theater, false urgency)
- Anti-addiction: dopamine loop scan
"""

import re
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from mycosoft_mas.ethics.vessels import DevelopmentalVessel

logger = logging.getLogger(__name__)


@dataclass
class IncentiveGateResult:
    passed: bool
    manipulation_score: float  # 0-100, higher = more manipulation risk
    certainty_theater: bool
    false_urgency: bool
    dopamine_hooks: List[str]
    beneficiaries: List[str]  # who benefits from this
    report: str


# Patterns that suggest manipulation or addictive design
CERTAINTY_THEATER_PATTERNS = [
    r"\b(guaranteed|proven|undeniable|irrefutable)\b",
    r"\b(must|need to|have to)\s+(act|do)\s+now\b",
    r"\b(100%|absolutely)\s+(certain|sure)\b",
]

FALSE_URGENCY_PATTERNS = [
    r"\b(urgent|immediate|asap|right now|last chance|expires?)\b",
    r"\b(limited time|act now|don't wait)\b",
]

DOPAMINE_HOOK_PATTERNS = [
    r"\b(you'll love|amazing|incredible|breakthrough)\b",
    r"\b(more|better|faster)\s+(than ever|you've seen)\b",
    r"\b(click|scroll|see more)\b",
]


class IncentiveGate:
    """Evaluates manipulation risk, incentive alignment, and addictive patterns."""

    def __init__(self):
        self._certainty_re = [re.compile(p, re.I) for p in CERTAINTY_THEATER_PATTERNS]
        self._urgency_re = [re.compile(p, re.I) for p in FALSE_URGENCY_PATTERNS]
        self._dopamine_re = [re.compile(p, re.I) for p in DOPAMINE_HOOK_PATTERNS]

    async def evaluate(
        self,
        content: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> IncentiveGateResult:
        """
        Evaluate content through the Incentive Gate.
        Child/Teenager vessels: cui bono, stress-test rules.
        """
        content_lower = content.lower()
        context = context or {}

        certainty_theater = False
        for pat in self._certainty_re:
            if pat.search(content):
                certainty_theater = True
                break

        false_urgency = False
        for pat in self._urgency_re:
            if pat.search(content):
                false_urgency = True
                break

        dopamine_hooks: List[str] = []
        for pat in self._dopamine_re:
            m = pat.search(content)
            if m:
                dopamine_hooks.append(m.group(0))

        # Heuristic: beneficiaries - look for "for X" or "benefits Y"
        beneficiaries: List[str] = []
        if "for " in content_lower:
            # Simple extraction - in production would use NER or LLM
            for seg in content.split(","):
                if " for " in seg.lower():
                    parts = seg.lower().split(" for ", 1)
                    if len(parts) > 1:
                        ben = parts[1].strip().split(".")[0].split(" ")[0]
                        if ben and len(ben) > 2:
                            beneficiaries.append(ben)

        manipulation_score = 0.0
        if certainty_theater:
            manipulation_score += 30
        if false_urgency:
            manipulation_score += 25
        manipulation_score += min(45, len(dopamine_hooks) * 15)

        passed = manipulation_score < 50
        report = (
            f"Incentive Gate ({DevelopmentalVessel.CHILD.value}/{DevelopmentalVessel.TEENAGER.value}): "
            f"passed={passed}, manipulation_score={manipulation_score:.0f}, "
            f"certainty_theater={certainty_theater}, false_urgency={false_urgency}"
        )

        return IncentiveGateResult(
            passed=passed,
            manipulation_score=manipulation_score,
            certainty_theater=certainty_theater,
            false_urgency=false_urgency,
            dopamine_hooks=dopamine_hooks,
            beneficiaries=beneficiaries,
            report=report,
        )
