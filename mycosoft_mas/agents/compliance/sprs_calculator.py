"""SPRS Score Calculator — TAC-O Compliance

Automated Supplier Performance Risk System (SPRS) self-assessment
score computation based on NIST 800-171 Rev. 2 control implementation.

SPRS score ranges from -203 (no controls implemented) to 110 (all controls implemented).
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

NIST_800_171_CONTROL_FAMILIES = {
    "3.1": {"name": "Access Control", "count": 22},
    "3.2": {"name": "Awareness and Training", "count": 3},
    "3.3": {"name": "Audit and Accountability", "count": 9},
    "3.4": {"name": "Configuration Management", "count": 9},
    "3.5": {"name": "Identification and Authentication", "count": 11},
    "3.6": {"name": "Incident Response", "count": 3},
    "3.7": {"name": "Maintenance", "count": 6},
    "3.8": {"name": "Media Protection", "count": 9},
    "3.9": {"name": "Personnel Security", "count": 2},
    "3.10": {"name": "Physical Protection", "count": 6},
    "3.11": {"name": "Risk Assessment", "count": 3},
    "3.12": {"name": "Security Assessment", "count": 4},
    "3.13": {"name": "System and Communications Protection", "count": 16},
    "3.14": {"name": "System and Information Integrity", "count": 7},
}

CONTROL_WEIGHTS = {
    1: 1, 3: 3, 5: 5,
}


class SPRSCalculator:
    """Calculate SPRS self-assessment score for NIST 800-171 compliance."""

    def __init__(self):
        self.controls: Dict[str, Dict[str, Any]] = {}
        self.total_controls = 110

    def set_control_status(
        self, control_id: str, implemented: bool,
        weight: int = 5, notes: str = "",
    ):
        """Set implementation status for a specific NIST 800-171 control."""
        self.controls[control_id] = {
            "implemented": implemented,
            "weight": weight,
            "notes": notes,
        }

    def calculate_score(self) -> Dict[str, Any]:
        """Calculate SPRS score.
        
        Base score is 110 (all controls implemented).
        Subtract weight for each unimplemented control.
        """
        score = 110
        unimplemented = []

        for control_id, status in self.controls.items():
            if not status["implemented"]:
                score -= status["weight"]
                unimplemented.append({
                    "control_id": control_id,
                    "weight": status["weight"],
                    "notes": status["notes"],
                })

        return {
            "sprs_score": max(-203, score),
            "total_controls": self.total_controls,
            "evaluated_controls": len(self.controls),
            "implemented": sum(1 for c in self.controls.values() if c["implemented"]),
            "unimplemented": len(unimplemented),
            "unimplemented_details": unimplemented,
            "assessment_type": "self_assessment",
            "framework": "NIST SP 800-171 Rev. 2",
        }

    def generate_poam(self) -> List[Dict[str, Any]]:
        """Generate Plan of Action and Milestones for unimplemented controls."""
        poam = []
        for control_id, status in self.controls.items():
            if not status["implemented"]:
                poam.append({
                    "control_id": control_id,
                    "weakness": f"Control {control_id} not fully implemented",
                    "notes": status["notes"],
                    "weight": status["weight"],
                    "milestone": "Implement within 180 days of contract award",
                    "status": "open",
                })
        return poam
