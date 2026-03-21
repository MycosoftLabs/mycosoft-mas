"""
Voice v9 Speech Grounding Gate - March 2, 2026.

Validates factual speech against confidence, freshness, and provenance
before allowing output. Ensures MYCA earns the right to speak every event.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from mycosoft_mas.voice_v9.schemas import GroundedSpeechDecision, SpeechworthyEvent


class SpeechGroundingGate:
    """
    Validates events before they become spoken output.
    Checks: confidence, freshness, provenance.
    """

    MIN_CONFIDENCE = 0.7
    MAX_AGE_SECONDS = 300  # 5 minutes - events older are stale
    REQUIRED_PROVENANCE_FOR_HIGH_STAKE = True  # Require provenance for device/safety events

    def ground(
        self,
        event: SpeechworthyEvent,
        proposed_text: Optional[str] = None,
    ) -> GroundedSpeechDecision:
        """
        Validate event and produce a grounded speech decision.
        proposed_text: optional override; defaults to event.summary.
        """
        text = proposed_text or event.summary
        now = datetime.now(timezone.utc)
        issues: list[str] = []

        # Confidence check
        if event.confidence < self.MIN_CONFIDENCE:
            return GroundedSpeechDecision(
                event_id=event.event_id,
                session_id=event.session_id,
                speak=False,
                text=text,
                confidence=event.confidence,
                reasoning=f"confidence {event.confidence:.2f} below {self.MIN_CONFIDENCE}",
            )

        # Freshness check
        try:
            ts = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
            age = (now - ts).total_seconds()
            if age > self.MAX_AGE_SECONDS:
                issues.append(f"event age {age:.0f}s exceeds {self.MAX_AGE_SECONDS}s")
        except Exception:
            pass  # If we can't parse, don't block

        # Provenance for high-stake sources
        if self.REQUIRED_PROVENANCE_FOR_HIGH_STAKE and event.source.value in (
            "mdp_device",
            "mas_task",
        ):
            if not event.provenance or not event.provenance.strip():
                issues.append("missing provenance for device/task event")

        if issues:
            return GroundedSpeechDecision(
                event_id=event.event_id,
                session_id=event.session_id,
                speak=False,
                text=text,
                confidence=event.confidence,
                reasoning="; ".join(issues),
            )

        return GroundedSpeechDecision(
            event_id=event.event_id,
            session_id=event.session_id,
            speak=True,
            text=text,
            confidence=event.confidence,
            reasoning="grounded: confidence, freshness, provenance OK",
        )


_gate: Optional[SpeechGroundingGate] = None


def get_speech_grounding_gate() -> SpeechGroundingGate:
    global _gate
    if _gate is None:
        _gate = SpeechGroundingGate()
    return _gate
