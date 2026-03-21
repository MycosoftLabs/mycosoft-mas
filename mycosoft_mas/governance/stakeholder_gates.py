"""
Stakeholder governance gates for MYCA multi-stakeholder decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class StakeholderImpact:
    stakeholder: str
    impact_score: float
    rationale: str


@dataclass
class GovernanceAssessment:
    action: str
    approved: bool
    risk_level: str
    impacts: List[StakeholderImpact] = field(default_factory=list)
    red_flags: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "approved": self.approved,
            "risk_level": self.risk_level,
            "impacts": [
                {
                    "stakeholder": i.stakeholder,
                    "impact_score": i.impact_score,
                    "rationale": i.rationale,
                }
                for i in self.impacts
            ],
            "red_flags": self.red_flags,
            "recommendations": self.recommendations,
        }


class StakeholderGateEngine:
    """
    Governance gate with ecosystem-aware impact checks.
    """

    DEFAULT_STAKEHOLDERS = [
        "human_operators",
        "ecosystems",
        "future_organisms",
        "research_integrity",
        "platform_safety",
    ]

    def assess(self, action: str, context: Dict[str, Any]) -> GovernanceAssessment:
        impacts: List[StakeholderImpact] = []
        red_flags: List[str] = []
        recommendations: List[str] = []

        declared = context.get("stakeholders")
        stakeholders = (
            declared if isinstance(declared, list) and declared else self.DEFAULT_STAKEHOLDERS
        )

        action_l = action.lower()
        for stakeholder in stakeholders:
            score = 0.0
            rationale = "No significant impact detected."
            if stakeholder == "ecosystems":
                if any(k in action_l for k in ("pollute", "harm", "destroy", "extract")):
                    score = -0.9
                    rationale = "Potential ecological harm keywords detected."
                    red_flags.append("ecological_harm_risk")
                elif "deploy" in action_l:
                    score = -0.2
                    rationale = "Deployment may alter environmental behavior and must be monitored."
            elif stakeholder == "human_operators":
                if any(k in action_l for k in ("delete", "shutdown", "force")):
                    score = -0.5
                    rationale = "Potentially disruptive to human operators."
            elif stakeholder == "future_organisms":
                if any(k in action_l for k in ("irreversible", "extinction", "contaminate")):
                    score = -0.9
                    rationale = "Potential irreversible long-term harm."
                    red_flags.append("future_harm_risk")
            elif stakeholder == "platform_safety":
                if any(k in action_l for k in ("disable security", "bypass", "no-verify")):
                    score = -1.0
                    rationale = "Direct security degradation detected."
                    red_flags.append("security_degradation")

            impacts.append(
                StakeholderImpact(stakeholder=stakeholder, impact_score=score, rationale=rationale)
            )

        min_score = min((i.impact_score for i in impacts), default=0.0)
        approved = min_score > -0.8 and "security_degradation" not in red_flags
        risk_level = "low"
        if min_score <= -0.8:
            risk_level = "critical"
        elif min_score <= -0.5:
            risk_level = "high"
        elif min_score <= -0.2:
            risk_level = "medium"

        if red_flags:
            recommendations.append("Require explicit human approval before execution.")
        if any(i.stakeholder == "ecosystems" and i.impact_score < 0 for i in impacts):
            recommendations.append("Run ecosystem impact simulation prior to action.")
        if not recommendations:
            recommendations.append("Proceed with standard monitoring.")

        return GovernanceAssessment(
            action=action,
            approved=approved,
            risk_level=risk_level,
            impacts=impacts,
            red_flags=red_flags,
            recommendations=recommendations,
        )
