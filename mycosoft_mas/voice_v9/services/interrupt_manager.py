"""
Voice v9 Interrupt Manager - March 2, 2026.

Wraps DuplexSession for v9 integration. Supports barge-in, TTS pause/duck,
soft interjects for high-priority events, and resumption of unfinished assistant speech.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from mycosoft_mas.consciousness.conversation_control import ConversationState
from mycosoft_mas.consciousness.duplex_session import (
    DuplexSession,
    create_duplex_session,
)

logger = logging.getLogger(__name__)


@dataclass
class InterruptState:
    """Current interrupt/duplex state for v9 session."""

    is_speaking: bool
    has_interrupted_draft: bool
    interrupted_draft_text: Optional[str] = None
    barge_in_count: int = 0
    last_barge_in_at: Optional[str] = None
    state: str = "idle"


class InterruptManager:
    """
    v9 facade over DuplexSession for interrupt and duplex control.

    Integrates with voice_v9 session lifecycle while delegating to
    DuplexSession for barge-in, TTS pause, and draft preservation.
    """

    def __init__(
        self,
        session_id: str,
        duplex_session: Optional[DuplexSession] = None,
        on_barge_in: Optional[Callable[[], None]] = None,
        on_state_change: Optional[Callable[[str], None]] = None,
    ):
        self.session_id = session_id
        self._duplex = duplex_session or create_duplex_session(
            session_id=session_id,
            on_barge_in=self._wrap_barge_in(on_barge_in),
            on_state_change=self._wrap_state_change(on_state_change),
        )
        self._on_barge_in = on_barge_in
        self._on_state_change = on_state_change

    def _wrap_barge_in(self, ext: Optional[Callable[[], None]]) -> Callable[[], None]:
        def _inner():
            if ext:
                ext()

        return _inner

    def _wrap_state_change(
        self, ext: Optional[Callable[[str], None]]
    ) -> Callable[[ConversationState], None]:
        def _inner(state: ConversationState):
            if ext:
                ext(state.value)

        return _inner

    @property
    def duplex_session(self) -> DuplexSession:
        """Access underlying DuplexSession for bridge integration."""
        return self._duplex

    @property
    def is_speaking(self) -> bool:
        return self._duplex.is_speaking

    @property
    def state(self) -> str:
        return self._duplex.state.value

    def request_barge_in(self, user_input: Optional[str] = None) -> None:
        """
        Manually trigger barge-in (e.g., when browser/STT detects user speech).
        """
        self._duplex.barge_in(user_input)

    def on_audio(self, audio_chunk: bytes) -> bool:
        """
        Process incoming audio for VAD-based barge-in.
        Returns True if barge-in was triggered.
        """
        return self._duplex.on_audio(audio_chunk)

    def get_interrupted_draft(self) -> Optional[str]:
        """Get what MYCA was saying when interrupted."""
        return self._duplex.get_interrupted_draft()

    def get_interrupt_state(self) -> InterruptState:
        """Get current interrupt/duplex state for v9 API/UI."""
        metrics = self._duplex.get_metrics()
        draft = self._duplex.get_interrupted_draft()
        return InterruptState(
            is_speaking=self._duplex.is_speaking,
            has_interrupted_draft=draft is not None and len(draft) > 0,
            interrupted_draft_text=draft if draft else None,
            barge_in_count=metrics.get("total_barge_ins", 0),
            last_barge_in_at=None,
            state=self._duplex.state.value,
        )

    def set_tts_callbacks(
        self,
        send_tts: Callable[[Any], Any],
        stop_tts: Callable[[], Any],
    ) -> None:
        """Wire TTS callbacks for PersonaPlex/Moshi integration."""
        self._duplex.set_tts_callback(send_tts)
        self._duplex.set_stop_tts_callback(stop_tts)

    def reset(self) -> None:
        """Reset session state."""
        self._duplex.reset()

    def get_metrics(self) -> Dict[str, Any]:
        """Get duplex metrics for diagnostics."""
        return self._duplex.get_metrics()


_interrupt_managers: Dict[str, InterruptManager] = {}


def get_interrupt_manager(session_id: str) -> InterruptManager:
    """Get or create session-scoped InterruptManager. Cached per session."""
    if session_id not in _interrupt_managers:
        _interrupt_managers[session_id] = InterruptManager(session_id=session_id)
    return _interrupt_managers[session_id]


def release_interrupt_manager(session_id: str) -> None:
    """Release and reset InterruptManager when session ends."""
    if session_id in _interrupt_managers:
        _interrupt_managers[session_id].reset()
        del _interrupt_managers[session_id]
