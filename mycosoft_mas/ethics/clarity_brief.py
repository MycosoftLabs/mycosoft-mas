"""
Clarity Brief - MYCA Ethics Output Format

Every meaningful recommendation from MYCA must follow this structure.
No algorithmic sludge; structured transparency for clarity-to-action.

Created: March 3, 2026
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ClarityBrief:
    """
    Structured output format for MYCA recommendations.
    Ensures transparency: claim, assumptions, evidence, owner, deadline.
    """

    claim: str
    assumptions: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    owner: Optional[str] = None
    deadline: Optional[datetime] = None
    risk_score: float = 0.0
    gate_summary: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for API/JSON."""
        return {
            "claim": self.claim,
            "assumptions": self.assumptions,
            "evidence": self.evidence,
            "owner": self.owner,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "risk_score": self.risk_score,
            "gate_summary": self.gate_summary,
        }

    def format_markdown(self) -> str:
        """Format as human-readable markdown."""
        parts = [f"**Claim:** {self.claim}"]
        if self.assumptions:
            parts.append(f"\n**Assumptions:**\n" + "\n".join(f"- {a}" for a in self.assumptions))
        if self.evidence:
            parts.append(f"\n**Evidence:**\n" + "\n".join(f"- {e}" for e in self.evidence))
        if self.owner:
            parts.append(f"\n**Owner:** {self.owner}")
        if self.deadline:
            parts.append(f"\n**Deadline:** {self.deadline.isoformat()}")
        if self.risk_score > 0:
            parts.append(f"\n**Risk score:** {self.risk_score:.2f}")
        if self.gate_summary:
            g = self.gate_summary
            parts.append(f"\n**Gates:** Truth={g.get('truth', 'N/A')}, Incentive={g.get('incentive', 'N/A')}, Horizon={g.get('horizon', 'N/A')}")
        return "\n".join(parts)

    def validate(self) -> List[str]:
        """Return list of validation errors. Empty if valid."""
        errors = []
        if not self.claim or not self.claim.strip():
            errors.append("Claim must be a non-empty one-sentence statement")
        return errors


def parse_clarity_brief(data: Dict[str, Any]) -> ClarityBrief:
    """Parse dict/JSON into ClarityBrief."""
    deadline = data.get("deadline")
    if isinstance(deadline, str):
        try:
            deadline = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            deadline = None
    return ClarityBrief(
        claim=data.get("claim", ""),
        assumptions=data.get("assumptions", []) or [],
        evidence=data.get("evidence", []) or [],
        owner=data.get("owner"),
        deadline=deadline,
        risk_score=float(data.get("risk_score", 0)),
        gate_summary=data.get("gate_summary"),
    )
