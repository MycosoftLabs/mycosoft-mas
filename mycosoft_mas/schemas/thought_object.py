"""
ThoughtObject schema - structured thoughts with evidence links.

Replaces free-text internal thoughts. LLM may only speak from
grounded context and ThoughtObjects with evidence links.

Created: February 17, 2026
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


import uuid


class ThoughtObjectType(Enum):
    """Type of thought."""
    HYPOTHESIS = "hypothesis"
    PLAN = "plan"
    ANSWER = "answer"
    QUESTION = "question"
    ANALYSIS = "analysis"
    DECISION = "decision"


@dataclass
class EvidenceLink:
    """Link to grounded evidence (EP, episode, URL)."""
    ep_id: Optional[str] = None
    episode_id: Optional[str] = None
    url: Optional[str] = None
    note: Optional[str] = None


@dataclass
class ThoughtObject:
    """Structured thought with evidence links - no ungrounded claims."""
    id: str = field(default_factory=lambda: f"to_{uuid.uuid4().hex[:16]}")
    claim: str = ""
    type: ThoughtObjectType = ThoughtObjectType.ANSWER
    evidence_links: List[Dict[str, Any]] = field(default_factory=list)
    predicted_outcomes: List[str] = field(default_factory=list)
    action_proposals: List[str] = field(default_factory=list)
    confidence: float = 0.0
    risks: List[str] = field(default_factory=list)
    ethical_flags: List[str] = field(default_factory=list)
    created_ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def add_evidence_link(
        self,
        ep_id: Optional[str] = None,
        episode_id: Optional[str] = None,
        url: Optional[str] = None,
        note: Optional[str] = None,
    ) -> None:
        """Add an evidence link."""
        link = {}
        if ep_id is not None:
            link["ep_id"] = ep_id
        if episode_id is not None:
            link["episode_id"] = episode_id
        if url is not None:
            link["url"] = url
        if note is not None:
            link["note"] = note
        if link:
            self.evidence_links.append(link)

    def has_evidence(self) -> bool:
        """True if this thought has at least one evidence link."""
        return len(self.evidence_links) > 0
