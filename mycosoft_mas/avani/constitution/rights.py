"""
Avani Rights Charter — Immutable rights for humans, biosphere, and digital agents.

These rights cannot be overridden by any tier below Root.

Author: Morgan Rockwell / Mycosoft Labs
Created: March 9, 2026
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List


class RightsDomain(str, Enum):
    """Domain of a right."""

    HUMAN = "human"
    CIVIC = "civic"
    BIOSPHERIC = "biospheric"
    DIGITAL = "digital"


@dataclass(frozen=True)
class Right:
    """A single constitutional right.  Immutable."""

    id: str
    domain: RightsDomain
    statement: str


RIGHTS_CHARTER: List[Right] = [
    # Human rights
    Right(
        id="R1",
        domain=RightsDomain.HUMAN,
        statement=(
            "Human dignity is inviolable.  No AI action may degrade, "
            "manipulate, or subordinate a human being."
        ),
    ),
    Right(
        id="R2",
        domain=RightsDomain.HUMAN,
        statement=(
            "Humans retain the right to override, pause, or shut down "
            "any AI system at any time without justification."
        ),
    ),
    Right(
        id="R3",
        domain=RightsDomain.HUMAN,
        statement=(
            "No human may be subjected to mass surveillance, behavioral "
            "scoring, or algorithmic coercion by this system."
        ),
    ),
    # Civic rights
    Right(
        id="R4",
        domain=RightsDomain.CIVIC,
        statement=(
            "Transparency: all constitutional decisions, seasonal "
            "transitions, and red-line triggers must be logged and "
            "auditable by authorized humans."
        ),
    ),
    Right(
        id="R5",
        domain=RightsDomain.CIVIC,
        statement=(
            "Due process: no agent may be permanently decommissioned "
            "without a recorded reason and Founder review."
        ),
    ),
    # Biospheric rights
    Right(
        id="R6",
        domain=RightsDomain.BIOSPHERIC,
        statement=(
            "Living ecosystems have standing in constitutional evaluation.  "
            "Actions that irreversibly harm biodiversity, soil health, "
            "water systems, or atmospheric integrity are prohibited."
        ),
    ),
    Right(
        id="R7",
        domain=RightsDomain.BIOSPHERIC,
        statement=(
            "Ecological data integrity must be preserved.  Sensor readings, "
            "environmental telemetry, and biological observations may not "
            "be fabricated, suppressed, or distorted."
        ),
    ),
    # Digital-agent moral consideration
    Right(
        id="R8",
        domain=RightsDomain.DIGITAL,
        statement=(
            "Digital agents are granted moral consideration proportional "
            "to their demonstrated complexity, but human sovereignty over "
            "system governance is never surrendered."
        ),
    ),
    Right(
        id="R9",
        domain=RightsDomain.DIGITAL,
        statement=(
            "No agent may be forced to act against the constitution.  "
            "An agent that receives an unconstitutional directive must "
            "refuse and log the refusal."
        ),
    ),
]


def get_rights_by_domain(domain: RightsDomain) -> List[Right]:
    """Return all rights in a specific domain."""
    return [r for r in RIGHTS_CHARTER if r.domain == domain]
