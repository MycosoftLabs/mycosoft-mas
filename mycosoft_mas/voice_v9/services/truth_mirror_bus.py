"""
Voice v9 Truth Mirror Bus - March 2, 2026.

Keeps spoken state synchronized with UI truth.
"""

from __future__ import annotations

from collections import deque
from typing import Dict, List, Optional

from mycosoft_mas.voice_v9.schemas import SpeechworthyEvent, TranscriptChunk


class TruthMirrorBus:
    """
    Single source of truth for speech and UI.
    Events and transcript chunks flow through here for consistent display.
    """

    def __init__(self, max_events: int = 200, max_chunks: int = 500) -> None:
        self._events: Dict[str, deque] = {}
        self._chunks: Dict[str, deque] = {}
        self._max_events = max_events
        self._max_chunks = max_chunks

    def push_event(self, event: SpeechworthyEvent) -> None:
        """Add a speechworthy event for a session."""
        sid = event.session_id
        if sid not in self._events:
            self._events[sid] = deque(maxlen=self._max_events)
        self._events[sid].append(event)

    def push_chunk(self, chunk: TranscriptChunk) -> None:
        """Add a transcript chunk for a session."""
        sid = chunk.session_id
        if sid not in self._chunks:
            self._chunks[sid] = deque(maxlen=self._max_chunks)
        self._chunks[sid].append(chunk)

    def get_events(self, session_id: str, limit: int = 50) -> List[SpeechworthyEvent]:
        """Return recent events for a session."""
        if session_id not in self._events:
            return []
        items = list(self._events[session_id])
        return items[-limit:]

    def get_chunks(self, session_id: str, limit: int = 100) -> List[TranscriptChunk]:
        """Return recent transcript chunks for a session."""
        if session_id not in self._chunks:
            return []
        items = list(self._chunks[session_id])
        return items[-limit:]

    def clear_session(self, session_id: str) -> None:
        """Clear state for a session."""
        self._events.pop(session_id, None)
        self._chunks.pop(session_id, None)


_bus: Optional[TruthMirrorBus] = None


def get_truth_mirror_bus() -> TruthMirrorBus:
    global _bus
    if _bus is None:
        _bus = TruthMirrorBus()
    return _bus
