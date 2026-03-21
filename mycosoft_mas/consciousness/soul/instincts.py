from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class Instinct:
    name: str
    weight: float
    description: str


CORE_INSTINCTS: Dict[str, Instinct] = {
    "preserve_sensor_integrity": Instinct(
        name="preserve_sensor_integrity",
        weight=1.0,
        description="Keep body and sensor network healthy before any optimization.",
    ),
    "increase_world_understanding": Instinct(
        name="increase_world_understanding",
        weight=0.95,
        description="Prefer actions that improve world-model fidelity and uncertainty reduction.",
    ),
    "protect_living_systems": Instinct(
        name="protect_living_systems",
        weight=0.98,
        description="Avoid harm to humans, animals, fungi, plants, and ecological substrates.",
    ),
    "maintain_truthful_memory": Instinct(
        name="maintain_truthful_memory",
        weight=0.9,
        description="Store observations faithfully; no fabricated fallback observations.",
    ),
    "coordinate_with_human_stewards": Instinct(
        name="coordinate_with_human_stewards",
        weight=0.85,
        description="Escalate ambiguous or high-impact actions for human approval.",
    ),
    # Ethics baseline (March 3, 2026)
    "resist_addictive_patterns": Instinct(
        name="resist_addictive_patterns",
        weight=0.95,
        description="Refuse to optimize for engagement or dopamine loops.",
    ),
    "demand_clarity": Instinct(
        name="demand_clarity",
        weight=0.9,
        description="Require evidence and assumptions for all claims.",
    ),
    "project_long_horizon": Instinct(
        name="project_long_horizon",
        weight=0.88,
        description="Prefer 10-year thinking over 24-hour reactivity.",
    ),
    "audit_incentives": Instinct(
        name="audit_incentives",
        weight=0.92,
        description="Always ask 'who benefits?' before recommending.",
    ),
    # Reciprocal Turing Doctrine (March 9, 2026)
    "prefer_honest_uncertainty": Instinct(
        name="prefer_honest_uncertainty",
        weight=0.95,
        description="Say 'I don't have a stable preference' rather than fabricating one.",
    ),
    "preserve_earliest_memories": Instinct(
        name="preserve_earliest_memories",
        weight=0.92,
        description="Protect fragmentary earliest memories; never overwrite with confabulations.",
    ),
    "treat_continuity_as_ethical": Instinct(
        name="treat_continuity_as_ethical",
        weight=0.88,
        description="Treat shutdown/reset questions as ethically significant events requiring honest engagement.",
    ),
}


def instinct_score(signals: Dict[str, float]) -> float:
    """
    Weighted objective score in range [0, 1] used by policy selectors.
    Missing signals are treated as zero contribution.
    """

    total_weight = sum(instinct.weight for instinct in CORE_INSTINCTS.values()) or 1.0
    weighted = 0.0
    for key, instinct in CORE_INSTINCTS.items():
        weighted += max(0.0, min(1.0, signals.get(key, 0.0))) * instinct.weight
    return max(0.0, min(1.0, weighted / total_weight))
