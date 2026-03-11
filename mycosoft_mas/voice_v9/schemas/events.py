"""
Voice v9 event schemas - March 2, 2026.

SpeechworthyEvent and GroundedSpeechDecision for the normalized event rail.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class EventSource(str, Enum):
    """Origin of a speechworthy event."""
    MDP_DEVICE = "mdp_device"
    CREP = "crep"
    NLM = "nlm"
    MAS_TASK = "mas_task"
    TOOL_COMPLETION = "tool_completion"
    MYCORRHIZAE = "mycorrhizae"
    SYSTEM = "system"


class SpeechworthyEvent(BaseModel):
    """
    Normalized event that may be spoken or shown in UI.
    Both speech and UI consume this structure for truth consistency.
    """
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    source: EventSource
    summary: str  # Human-readable summary for speech/UI
    urgency: float = 0.5  # 0.0–1.0; higher = more urgent
    confidence: float = 1.0  # 0.0–1.0; grounding confidence
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    raw_payload: Optional[Dict[str, Any]] = None
    provenance: Optional[str] = None  # Trace to source
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GroundedSpeechDecision(BaseModel):
    """Decision from speech_grounding_gate: whether to speak and how."""
    event_id: str
    session_id: str
    speak: bool = True
    text: str  # Grounded text to speak (may be rewritten)
    confidence: float
    reasoning: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
