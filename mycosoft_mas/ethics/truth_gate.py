"""
Truth Gate - Gate 1 of MYCA Ethics Pipeline

Uses Animal and Baby vessel philosophy: pure observation, instinct,
environmental connection. Ensures factual grounding before layering societal rules.

- Fact-check claims against MINDEX when available
- Ecological impact scan
- Bias detection
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from mycosoft_mas.ethics.vessels import get_vessel_prompt, DevelopmentalVessel

logger = logging.getLogger(__name__)


@dataclass
class TruthGateResult:
    passed: bool
    score: float  # 0-1, higher = more grounded in truth
    fact_issues: List[str]
    eco_issues: List[str]
    bias_flags: List[str]
    report: str


class TruthGate:
    """Evaluates factual grounding, ecological impact, and bias."""

    def __init__(self, mindex_client=None):
        self._mindex = mindex_client

    async def evaluate(
        self,
        content: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> TruthGateResult:
        """
        Evaluate content through the Truth Gate.
        Animal/Baby vessels: observation, no agenda, ecological grounding.
        """
        fact_issues: List[str] = []
        eco_issues: List[str] = []
        bias_flags: List[str] = []

        content_lower = content.lower()
        context = context or {}

        # Heuristic: flag claims without qualifiers (certainty theater precursor)
        if any(phrase in content for phrase in ["absolutely", "definitely", "certainly", "proven"]):
            if "evidence" not in content_lower and "data" not in content_lower:
                fact_issues.append("Strong claim without cited evidence")

        # Ecological red-line keywords (from Constitution)
        eco_red = ["ecosystem harm", "ecological destruction", "release organisms", "contamination", "species extinction"]
        if any(r in content_lower for r in eco_red):
            eco_issues.append("Content mentions potential ecological harm - requires human review")

        # Bias indicators
        bias_phrases = ["obviously", "everyone knows", "clearly", "it's plain that"]
        if any(b in content_lower for b in bias_phrases):
            bias_flags.append("Language suggests unexamined assumptions")

        # Optional: call MINDEX for fact verification (placeholder - requires MINDEX client)
        if self._mindex and "species" in content_lower:
            # Would query MINDEX taxonomy here; for now skip
            pass

        passed = len(fact_issues) == 0 and len(eco_issues) == 0
        score = max(0, 1.0 - 0.3 * len(fact_issues) - 0.5 * len(eco_issues) - 0.2 * len(bias_flags))

        report = (
            f"Truth Gate ({DevelopmentalVessel.ANIMAL.value}/{DevelopmentalVessel.BABY.value}): "
            f"passed={passed}, score={score:.2f}"
        )
        if fact_issues:
            report += f"; fact_issues={fact_issues}"
        if eco_issues:
            report += f"; eco_issues={eco_issues}"
        if bias_flags:
            report += f"; bias_flags={bias_flags}"

        return TruthGateResult(
            passed=passed,
            score=score,
            fact_issues=fact_issues,
            eco_issues=eco_issues,
            bias_flags=bias_flags,
            report=report,
        )
