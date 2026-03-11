"""
Voice v9 Voice Gateway - March 2, 2026.

Entry point for v9 voice session lifecycle.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional
from uuid import uuid4

from mycosoft_mas.voice_v9.schemas import VoiceSession, TranscriptChunk
from mycosoft_mas.voice_v9.services.latency_monitor import get_latency_monitor
from mycosoft_mas.voice_v9.services.truth_mirror_bus import get_truth_mirror_bus
from mycosoft_mas.voice_v9.services.interrupt_manager import release_interrupt_manager


class VoiceGateway:
    """Manages v9 voice session lifecycle and routing."""

    def __init__(self) -> None:
        self._sessions: Dict[str, VoiceSession] = {}
        self._latency = get_latency_monitor()
        self._truth_bus = get_truth_mirror_bus()

    def create_session(
        self,
        user_id: str = "morgan",
        conversation_id: Optional[str] = None,
    ) -> VoiceSession:
        """Create a new v9 voice session."""
        session_id = str(uuid4())
        conv_id = conversation_id or str(uuid4())
        session = VoiceSession(
            session_id=session_id,
            conversation_id=conv_id,
            user_id=user_id,
            status="active",
        )
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[VoiceSession]:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    def end_session(self, session_id: str) -> bool:
        """End a session and clean up."""
        if session_id not in self._sessions:
            return False
        self._sessions[session_id].status = "ended"
        self._latency.clear_session(session_id)
        self._truth_bus.clear_session(session_id)
        release_interrupt_manager(session_id)
        return True

    def add_transcript_chunk(self, chunk: TranscriptChunk) -> bool:
        """Add a transcript chunk and mirror to truth bus."""
        if chunk.session_id not in self._sessions:
            return False
        self._sessions[chunk.session_id].transcript_chunks.append(chunk)
        self._truth_bus.push_chunk(chunk)
        return True


_gateway: Optional[VoiceGateway] = None


def get_voice_gateway() -> VoiceGateway:
    global _gateway
    if _gateway is None:
        _gateway = VoiceGateway()
    return _gateway
