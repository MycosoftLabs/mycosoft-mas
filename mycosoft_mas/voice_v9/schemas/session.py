"""
Voice v9 session schemas - March 2, 2026.

VoiceSession, TranscriptChunk, LatencyTrace for the unified v9 session stream.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class TranscriptRole(str, Enum):
    """Role of the speaker in a transcript chunk."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class TranscriptChunk(BaseModel):
    """Incremental transcript chunk (STT partial or full)."""
    chunk_id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    role: TranscriptRole = TranscriptRole.USER
    text: str
    is_final: bool = False
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "browser_stt"  # browser_stt, moshi_stt, manual
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LatencyTrace(BaseModel):
    """Latency measurement for a voice turn or operation."""
    trace_id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    operation: str  # e.g. stt, brain_chat, tts, mas_clone
    start_ts: str
    end_ts: str
    duration_ms: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VoiceSession(BaseModel):
    """Voice v9 session state."""
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    conversation_id: Optional[str] = None
    user_id: str = "morgan"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "active"  # active, paused, ended
    transcript_chunks: List[TranscriptChunk] = Field(default_factory=list)
    latency_traces: List[LatencyTrace] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
