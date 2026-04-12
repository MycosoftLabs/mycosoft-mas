from __future__ import annotations

from typing import Any, Dict


class MarineEcologicalGuard:
    def evaluate(self, classification_result: Dict[str, Any]) -> Dict[str, Any]:
        mammal_score = float(classification_result.get("marine_mammal_score", 0.0))
        if mammal_score >= 0.85:
            action = "veto"
            ecological_impact = "HIGH"
        elif mammal_score >= 0.6:
            action = "gate_for_human_review"
            ecological_impact = "MEDIUM"
        else:
            action = "pass"
            ecological_impact = "LOW"
        return {
            "action": action,
            "ecological_impact": ecological_impact,
            "marine_mammal_score": mammal_score,
        }
