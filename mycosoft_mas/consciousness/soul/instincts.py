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

