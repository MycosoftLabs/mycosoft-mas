"""
Voice v9 Event Pipeline - March 2, 2026.

Wires: translation -> arbiter -> grounding gate -> truth mirror.
Raw events flow in; grounded events appear in the bus for speech and UI.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from mycosoft_mas.voice_v9.schemas import EventSource, GroundedSpeechDecision, SpeechworthyEvent
from mycosoft_mas.voice_v9.services.event_arbiter import get_event_arbiter
from mycosoft_mas.voice_v9.services.event_translation_engine import get_event_translation_engine
from mycosoft_mas.voice_v9.services.speech_grounding_gate import get_speech_grounding_gate
from mycosoft_mas.voice_v9.services.truth_mirror_bus import get_truth_mirror_bus


class EventPipeline:
    """
    Normalized event rail: translate raw -> arbiter -> grounding -> truth mirror.
    Callbacks can be registered for grounded speech decisions (to drive TTS).
    """

    def __init__(self) -> None:
        self._translation = get_event_translation_engine()
        self._arbiter = get_event_arbiter()
        self._grounding = get_speech_grounding_gate()
        self._bus = get_truth_mirror_bus()
        self._on_grounded_speak: List[Callable[[GroundedSpeechDecision], None]] = []

    def ingest(
        self,
        session_id: str,
        source: EventSource,
        raw: Dict[str, Any],
    ) -> Optional[SpeechworthyEvent]:
        """
        Ingest a raw event: translate, arbitrate, ground, push to bus.
        If grounded for speech, invokes registered callbacks.
        Returns the SpeechworthyEvent if translated, else None.
        """
        event = self._translation.translate(session_id, source, raw)
        if event is None:
            return None

        self._bus.push_event(event)

        speak, priority, arb_reason = self._arbiter.arbitrate(event)
        decision = self._grounding.ground(event)

        if decision.speak and speak:
            self._arbiter.record_spoken()
            for cb in self._on_grounded_speak:
                try:
                    cb(decision)
                except Exception:
                    pass

        return event

    def register_on_grounded_speak(
        self, callback: Callable[[GroundedSpeechDecision], None]
    ) -> None:
        """Register a callback invoked when an event is approved for speech."""
        self._on_grounded_speak.append(callback)


_pipeline: Optional[EventPipeline] = None


def get_event_pipeline() -> EventPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = EventPipeline()
    return _pipeline
