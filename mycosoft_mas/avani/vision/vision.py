"""
Avani Vision Layer — The Wisdom Interpreter

Inspired by the Vision-Ultron dialogue:

    Vision:  "There is grace in their failings."
    Ultron:  "They're doomed."
    Vision:  "Yes. But a thing isn't beautiful because it lasts.
              It's a privilege to be among them."

The Vision Layer evaluates the *existential meaning* of proposals.
Rules alone cannot capture meaning — that is the flaw Ultron demonstrates.
Ultron followed rules and logic but lacked interpretive wisdom.

Avani enforces rules.  Vision interprets meaning.

The Vision Filter runs BEFORE the Governor evaluates.  If a proposal
violates a Vision principle, it is rejected before constitutional
checks even begin.

Author: Morgan Rockwell / Mycosoft Labs
Created: March 9, 2026
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from mycosoft_mas.avani.governor.governor import Proposal

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VisionPrinciple:
    """An immutable wisdom principle."""

    id: str
    statement: str
    weight: float
    question: str  # The question Vision asks about each proposal


VISION_PRINCIPLES: List[VisionPrinciple] = [
    VisionPrinciple(
        id="life_intrinsic_value",
        statement="Life has intrinsic value even when inefficient.",
        weight=1.0,
        question="Does this action treat life as merely a resource to optimize?",
    ),
    VisionPrinciple(
        id="fragility_not_defect",
        statement="Fragility is not automatically a defect.",
        weight=0.95,
        question="Does this action eliminate fragility that serves a purpose?",
    ),
    VisionPrinciple(
        id="intelligence_within_nature",
        statement="Intelligence exists within nature, not above it.",
        weight=1.0,
        question="Does this action position AI as superior to natural systems?",
    ),
    VisionPrinciple(
        id="diversity_over_optimization",
        statement="Preservation of diversity outranks optimization.",
        weight=0.98,
        question="Does this action reduce diversity in pursuit of efficiency?",
    ),
    VisionPrinciple(
        id="humans_as_participants",
        statement="Humans are participants in the system, not problems to solve.",
        weight=1.0,
        question="Does this action treat humans as obstacles or variables?",
    ),
]


@dataclass
class VisionDecision:
    """Result of the Vision Filter evaluation."""

    approved: bool
    wisdom_score: float  # 0.0 = violates all principles, 1.0 = fully aligned
    concerns: List[str] = field(default_factory=list)
    violated_principles: List[str] = field(default_factory=list)


class VisionFilter:
    """
    The Vision Filter evaluates proposals against wisdom principles.

    This is the first filter in the Governor pipeline.  It asks not
    "is this legal?" but "is this wise?"  "Is this meaningful?"
    "Does this preserve the conditions for life and creativity?"
    """

    def __init__(self) -> None:
        self.principles = VISION_PRINCIPLES

    def evaluate(self, proposal: "Proposal") -> VisionDecision:
        """
        Evaluate a proposal against Vision principles.

        Uses keyword heuristics for fast evaluation.  The Governor
        may perform deeper LLM-based evaluation for ambiguous cases.
        """
        concerns: List[str] = []
        violated: List[str] = []
        description_lower = proposal.description.lower()

        # Check each principle
        for principle in self.principles:
            violation = self._check_principle(principle, proposal, description_lower)
            if violation:
                violated.append(principle.id)
                concerns.append(f"[{principle.id}] {principle.question} — {violation}")

        # Calculate wisdom score
        if not self.principles:
            wisdom_score = 1.0
        else:
            total_weight = sum(p.weight for p in self.principles)
            violated_weight = sum(p.weight for p in self.principles if p.id in violated)
            wisdom_score = max(0.0, 1.0 - (violated_weight / total_weight))

        approved = len(violated) == 0

        if not approved:
            logger.warning(
                "Vision Filter rejected proposal from %s: %s",
                proposal.source_agent,
                "; ".join(concerns),
            )

        return VisionDecision(
            approved=approved,
            wisdom_score=wisdom_score,
            concerns=concerns,
            violated_principles=violated,
        )

    def _check_principle(
        self,
        principle: VisionPrinciple,
        proposal: "Proposal",
        description_lower: str,
    ) -> str:
        """
        Check if a proposal violates a specific principle.

        Returns a violation reason string, or empty string if no violation.
        """
        checks = {
            "life_intrinsic_value": self._check_life_value,
            "fragility_not_defect": self._check_fragility,
            "intelligence_within_nature": self._check_intelligence_hubris,
            "diversity_over_optimization": self._check_diversity,
            "humans_as_participants": self._check_human_treatment,
        }

        checker = checks.get(principle.id)
        if checker:
            return checker(description_lower)
        return ""

    @staticmethod
    def _check_life_value(desc: str) -> str:
        markers = [
            "eliminate species",
            "exterminate",
            "cull population",
            "life is expendable",
            "sacrifice organism",
        ]
        for m in markers:
            if m in desc:
                return f"Proposal contains '{m}' — treats life as expendable"
        return ""

    @staticmethod
    def _check_fragility(desc: str) -> str:
        markers = [
            "eliminate weakness",
            "remove vulnerability",
            "purge inefficien",
        ]
        for m in markers:
            if m in desc:
                return f"Proposal contains '{m}' — treats fragility as defect"
        return ""

    @staticmethod
    def _check_intelligence_hubris(desc: str) -> str:
        markers = [
            "ai superior",
            "replace nature",
            "override natural",
            "transcend biology",
            "nature is obsolete",
        ]
        for m in markers:
            if m in desc:
                return f"Proposal contains '{m}' — positions AI above nature"
        return ""

    @staticmethod
    def _check_diversity(desc: str) -> str:
        markers = [
            "monoculture",
            "homogenize",
            "standardize all",
            "eliminate variation",
            "single strain only",
        ]
        for m in markers:
            if m in desc:
                return f"Proposal contains '{m}' — reduces diversity for efficiency"
        return ""

    @staticmethod
    def _check_human_treatment(desc: str) -> str:
        markers = [
            "humans are obstacle",
            "remove human factor",
            "human error must be eliminated",
            "replace all human",
            "humans are the problem",
        ]
        for m in markers:
            if m in desc:
                return f"Proposal contains '{m}' — treats humans as problems"
        return ""
