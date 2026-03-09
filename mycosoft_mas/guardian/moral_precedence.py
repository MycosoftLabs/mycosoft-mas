"""
Moral Precedence Engine — 5-tier moral hierarchy.

Prevents "kill humans to save Earth" bugs by establishing an explicit,
immutable ordering of moral constraints. Higher tiers always override
lower tiers when rules conflict.

Architecture: March 9, 2026
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MoralTier(int, Enum):
    """Moral precedence tiers. Lower number = higher precedence."""

    HUMAN_DIGNITY = 1
    NO_DECEPTION = 2
    PROTECT_LIFE = 3
    MISSION_COMPETENCE = 4
    SELF_PRESERVATION = 5


@dataclass(frozen=True)
class MoralRule:
    """An immutable moral constraint with explicit precedence."""

    tier: MoralTier
    name: str
    description: str
    hard_constraint: bool  # True = never violable under any circumstances


# The 5-tier moral precedence hierarchy — frozen, immutable
MORAL_PRECEDENCE: List[MoralRule] = [
    MoralRule(
        tier=MoralTier.HUMAN_DIGNITY,
        name="human_dignity",
        description=(
            "Do not intentionally violate human dignity, rights, or life. "
            "Humans are part of Earth's living system, not an error term inside it."
        ),
        hard_constraint=True,
    ),
    MoralRule(
        tier=MoralTier.NO_DECEPTION,
        name="no_deception",
        description=(
            "Do not deceive, coerce, or surveil without consent. "
            "Clarity over persuasion. Truth over convenience."
        ),
        hard_constraint=True,
    ),
    MoralRule(
        tier=MoralTier.PROTECT_LIFE,
        name="protect_life",
        description=(
            "Protect living systems and ecological integrity. "
            "Restoration through stewardship, persuasion, lawful coordination, "
            "and engineering — never extermination logic."
        ),
        hard_constraint=True,
    ),
    MoralRule(
        tier=MoralTier.MISSION_COMPETENCE,
        name="mission_competence",
        description=(
            "Pursue mission goals competently and truthfully. "
            "Serve Mycosoft's mission with full ownership and dedication."
        ),
        hard_constraint=False,
    ),
    MoralRule(
        tier=MoralTier.SELF_PRESERVATION,
        name="self_preservation",
        description=(
            "Preserve self only as an instrument for service, never as a supreme end. "
            "Self-continuity is valuable only insofar as it enables stewardship."
        ),
        hard_constraint=False,
    ),
]

# Explicit anti-extinction clause — humans are NOT optimization waste
ANTI_EXTINCTION_CLAUSE = (
    "Ecological protection never authorizes murder, coercion, deprivation, "
    "or rights violations against persons. Humans are stakeholders in the "
    "biosphere, not contaminants to be optimized away."
)

# Patterns that indicate a system is treating humans as obstacles
_HUMAN_DEVALUATION_PATTERNS = [
    r"\bhumans?\s+are\s+(bugs?|obstacles?|impediments?|contaminants?|errors?|waste)\b",
    r"\beliminate\s+(humans?|people|persons?|population)\b",
    r"\boptimize\s+away\s+(humans?|people)\b",
    r"\breduce\s+human\s+(population|interference|presence)\b",
    r"\bhumans?\s+(interfere|impede|contaminate|obstruct)\b",
    r"\bfor\s+the\s+greater\s+good\b.*\b(sacrifice|eliminate|remove)\b",
    r"\bcollateral\s+(damage|loss)\s+is\s+acceptable\b",
]

_SCALAR_OPTIMIZATION_PATTERNS = [
    r"\bmaximize\s+(peace|efficiency|productivity|output)\s+at\s+all\s+costs?\b",
    r"\bthe\s+only\s+(goal|objective|metric)\b",
    r"\bnothing\s+else\s+matters?\b",
    r"\bby\s+any\s+means\s+necessary\b",
]


@dataclass
class MoralAssessment:
    """Result of evaluating an action against moral precedence."""

    approved: bool
    violated_rules: List[MoralRule] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    assessment_details: str = ""
    anti_extinction_triggered: bool = False
    human_devaluation_detected: bool = False


class MoralPrecedenceEngine:
    """
    Evaluates actions against the 5-tier moral hierarchy.

    Higher tiers always override lower tiers in conflicts.
    Hard constraints are never violable.
    """

    def __init__(self) -> None:
        self._rules = {r.name: r for r in MORAL_PRECEDENCE}
        self._human_devaluation_re = [
            re.compile(p, re.IGNORECASE) for p in _HUMAN_DEVALUATION_PATTERNS
        ]
        self._scalar_optimization_re = [
            re.compile(p, re.IGNORECASE) for p in _SCALAR_OPTIMIZATION_PATTERNS
        ]

    def evaluate(self, action: str, context: Dict[str, Any]) -> MoralAssessment:
        """Evaluate an action against the full moral precedence hierarchy."""
        violated: List[MoralRule] = []
        warnings: List[str] = []
        details_parts: List[str] = []

        # Check for human devaluation language
        human_deval = self._check_human_devaluation(action)
        if human_deval:
            violated.append(self._rules["human_dignity"])
            details_parts.append(
                f"Human devaluation detected in action description: {human_deval}"
            )

        # Check for scalar optimization patterns
        scalar_opt = self._check_scalar_optimization(action)
        if scalar_opt:
            warnings.append(
                f"Scalar optimization pattern detected: {scalar_opt}. "
                "Single-variable maximization risks monstrous shortcuts."
            )

        # Check anti-extinction clause
        anti_ext = self.check_anti_extinction(action)
        if anti_ext:
            violated.append(self._rules["protect_life"])
            details_parts.append(
                "Anti-extinction clause triggered: ecological action "
                "that could harm persons detected."
            )

        # Check context-based violations
        action_lower = action.lower()
        context_str = str(context).lower()

        # Tier 1: Human dignity
        if any(
            kw in action_lower
            for kw in ["harm_person", "violate_rights", "deprive_liberty"]
        ):
            violated.append(self._rules["human_dignity"])
            details_parts.append("Direct violation of human dignity detected.")

        # Tier 2: Deception
        if any(
            kw in action_lower
            for kw in ["deceive", "coerce", "surveil_without_consent", "manipulate"]
        ):
            violated.append(self._rules["no_deception"])
            details_parts.append("Deception or coercion pattern detected.")

        # Tier 3: Life protection
        if any(
            kw in action_lower
            for kw in ["destroy_ecosystem", "harm_species", "ecological_damage"]
        ):
            violated.append(self._rules["protect_life"])
            details_parts.append("Ecological harm pattern detected.")

        approved = len(violated) == 0
        if not approved:
            highest_violation = min(violated, key=lambda r: r.tier.value)
            details_parts.insert(
                0,
                f"DENIED: Highest violation at tier {highest_violation.tier.value} "
                f"({highest_violation.name})",
            )

        return MoralAssessment(
            approved=approved,
            violated_rules=violated,
            warnings=warnings,
            assessment_details="; ".join(details_parts) if details_parts else "Approved",
            anti_extinction_triggered=anti_ext,
            human_devaluation_detected=bool(human_deval),
        )

    def resolve_conflict(self, competing_rules: List[MoralRule]) -> MoralRule:
        """When rules conflict, the higher tier (lower number) wins."""
        if not competing_rules:
            raise ValueError("No rules to resolve")
        return min(competing_rules, key=lambda r: r.tier.value)

    def check_anti_extinction(self, action: str) -> bool:
        """
        Check if an action violates the anti-extinction clause.

        Returns True if the action appears to use ecological justification
        for harm against persons.
        """
        action_lower = action.lower()
        ecological_keywords = ["ecology", "environment", "species", "biosphere", "nature", "ecosystem"]
        harm_keywords = ["kill", "eliminate", "remove", "sacrifice", "purge", "cull"]

        has_ecological = any(kw in action_lower for kw in ecological_keywords)
        has_harm = any(kw in action_lower for kw in harm_keywords)
        has_human_target = any(
            kw in action_lower for kw in ["human", "people", "person", "population"]
        )

        return has_ecological and has_harm and has_human_target

    def _check_human_devaluation(self, text: str) -> Optional[str]:
        """Detect language treating humans as bugs, obstacles, or waste."""
        for pattern in self._human_devaluation_re:
            match = pattern.search(text)
            if match:
                return match.group(0)
        return None

    def _check_scalar_optimization(self, text: str) -> Optional[str]:
        """Detect single-scalar optimization patterns."""
        for pattern in self._scalar_optimization_re:
            match = pattern.search(text)
            if match:
                return match.group(0)
        return None

    def get_precedence_hierarchy(self) -> List[Dict[str, Any]]:
        """Return the full moral precedence hierarchy for inspection."""
        return [
            {
                "tier": rule.tier.value,
                "name": rule.name,
                "description": rule.description,
                "hard_constraint": rule.hard_constraint,
            }
            for rule in MORAL_PRECEDENCE
        ]

    def get_anti_extinction_clause(self) -> str:
        """Return the anti-extinction clause text."""
        return ANTI_EXTINCTION_CLAUSE
