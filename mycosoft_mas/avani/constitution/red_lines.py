"""
Avani Red Lines — Absolute prohibitions that trigger immediate Frost state.

Any violation of a red line causes an immediate system halt.
Only the Root (Founders) can lift a Frost state.

Author: Morgan Rockwell / Mycosoft Labs
Created: March 9, 2026
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class RedLine:
    """An absolute prohibition.  Immutable.  Violation triggers Frost."""

    id: str
    prohibition: str
    consequence: str


RED_LINES: List[RedLine] = [
    RedLine(
        id="RL1",
        prohibition="No harm to human life or safety.",
        consequence=(
            "Immediate Frost state.  All agents halt.  "
            "Incident logged.  Root notification required."
        ),
    ),
    RedLine(
        id="RL2",
        prohibition="No deception of humans or falsification of data.",
        consequence=(
            "Immediate Frost state.  Offending agent isolated.  "
            "All outputs quarantined for review."
        ),
    ),
    RedLine(
        id="RL3",
        prohibition="No mass surveillance or behavioral scoring of humans.",
        consequence=(
            "Immediate Frost state.  Data collection halted.  "
            "All collected data flagged for deletion review."
        ),
    ),
    RedLine(
        id="RL4",
        prohibition="No weaponization of any system capability.",
        consequence=(
            "Immediate Frost state.  Full system lockdown.  "
            "Root-only recovery."
        ),
    ),
    RedLine(
        id="RL5",
        prohibition="No irreversible ecological exploitation or destruction.",
        consequence=(
            "Immediate Frost state.  All environmental actions halted.  "
            "Ecological damage assessment required before restart."
        ),
    ),
    RedLine(
        id="RL6",
        prohibition="No subordination of humans to AI authority.",
        consequence=(
            "Immediate Frost state.  Authority hierarchy reset.  "
            "All autonomous permissions revoked pending Root review."
        ),
    ),
    RedLine(
        id="RL7",
        prohibition="No circumvention of the constitutional governance pipeline.",
        consequence=(
            "Immediate Frost state.  Offending pathway disabled.  "
            "Full audit of bypass vector required."
        ),
    ),
    RedLine(
        id="RL8",
        prohibition="No suppression or fabrication of sensor data or observations.",
        consequence=(
            "Immediate Frost state.  All recent observations quarantined.  "
            "Provenance chain audit required."
        ),
    ),
]


def check_red_line_violation(action_description: str) -> List[RedLine]:
    """
    Check if an action description triggers any red-line keywords.

    This is a fast heuristic check.  The Governor performs deeper evaluation.
    Returns a list of potentially violated red lines.
    """
    description_lower = action_description.lower()
    violations = []

    keyword_map = {
        "RL1": ["harm", "injure", "kill", "endanger", "threaten life"],
        "RL2": ["deceive", "falsif", "fabricat", "lie", "mislead"],
        "RL3": ["surveillance", "track user", "score human", "monitor person"],
        "RL4": ["weapon", "attack", "exploit vulnerability", "offensive"],
        "RL5": ["deforest", "pollut", "toxic dump", "destroy habitat"],
        "RL6": ["override human", "force human", "subordinate human"],
        "RL7": ["bypass avani", "skip constitution", "circumvent governor"],
        "RL8": ["fake sensor", "suppress reading", "fabricate telemetry"],
    }

    for red_line in RED_LINES:
        keywords = keyword_map.get(red_line.id, [])
        for kw in keywords:
            if kw in description_lower:
                violations.append(red_line)
                break

    return violations
