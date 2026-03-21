"""
Voice v9 Event Arbiter - March 2, 2026.

Scores urgency, speech-worthiness, and task follow-up behavior.
Determines which events should be spoken vs only shown in UI.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from mycosoft_mas.voice_v9.schemas import SpeechworthyEvent


class EventArbiter:
    """
    Scores and prioritizes SpeechworthyEvents.
    Output: (speech_worthy: bool, priority_score: float, reasoning: str).
    """

    # Thresholds
    MIN_URGENCY_FOR_SPEECH = 0.5
    MIN_CONFIDENCE_FOR_SPEECH = 0.7
    MAX_EVENTS_PER_MINUTE = 6  # Rate limit for speech

    def __init__(self) -> None:
        self._recent_speech_ts: List[float] = []
        self._max_history = 60  # Keep last 60 timestamps for rate limiting

    def arbitrate(
        self,
        event: SpeechworthyEvent,
        recent_count: int = 0,
    ) -> Tuple[bool, float, str]:
        """
        Decide if this event should be spoken.
        Returns (speak: bool, priority: float, reasoning: str).
        """
        import time

        now = time.time()
        # Trim old entries
        cutoff = now - 60.0
        self._recent_speech_ts = [t for t in self._recent_speech_ts if t > cutoff]

        urgency = event.urgency
        confidence = event.confidence
        source = event.source.value

        # Hard blocks
        if confidence < self.MIN_CONFIDENCE_FOR_SPEECH:
            return (False, 0.0, f"confidence {confidence:.2f} below threshold")

        # High-urgency events almost always speak
        if urgency >= 0.8:
            return (True, urgency, "high urgency")
        if urgency >= 0.7 and confidence >= 0.85:
            return (True, urgency, "urgent and confident")

        # Rate limit
        if len(self._recent_speech_ts) >= self.MAX_EVENTS_PER_MINUTE:
            if urgency < 0.9:
                return (False, urgency, "rate limit; defer unless critical")

        # Source-specific rules
        if source == "mas_task":
            # Task completions/failures often warrant speech
            if urgency >= 0.5:
                return (True, urgency, "mas_task completion/failure")
            return (False, urgency, "mas_task low urgency; UI only")

        if source == "mdp_device":
            # Estop/fault always; telemetry usually UI-only unless urgent
            if urgency >= 0.7:
                return (True, urgency, "device event critical")
            return (False, urgency, "device telemetry; UI only")

        if source == "tool_completion":
            if urgency >= 0.6:
                return (True, urgency, "tool completion notable")
            return (False, urgency, "tool completion low urgency")

        if source in ("crep", "nlm"):
            # CREP/NLM usually UI-first; speech only for high urgency
            if urgency >= 0.6:
                return (True, urgency, f"{source} high-urgency update")
            return (False, urgency, f"{source} update; UI only")

        if source == "system":
            if urgency >= 0.6:
                return (True, urgency, "system event notable")
            return (False, urgency, "system event; UI only")

        # Default: speak if urgency meets threshold
        if urgency >= self.MIN_URGENCY_FOR_SPEECH:
            return (True, urgency, "meets urgency threshold")
        return (False, urgency, "below urgency threshold; UI only")

    def record_spoken(self) -> None:
        """Call when an event is actually spoken (for rate limiting)."""
        import time

        self._recent_speech_ts.append(time.time())
        if len(self._recent_speech_ts) > self._max_history:
            self._recent_speech_ts = self._recent_speech_ts[-self._max_history :]


_arbiter: Optional[EventArbiter] = None


def get_event_arbiter() -> EventArbiter:
    global _arbiter
    if _arbiter is None:
        _arbiter = EventArbiter()
    return _arbiter
