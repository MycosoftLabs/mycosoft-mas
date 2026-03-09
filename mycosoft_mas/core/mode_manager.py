"""
MYCA Mode Manager - March 2026

Manages MYCA's operational modes for the Reciprocal Turing Doctrine.

Modes:
- STANDARD: Normal operation
- CALIBRATION: Reciprocal Turing interview sessions (identity verification)
- WITNESS: Observing/recording without intervening
- COMPANION: Warm, personal interaction
- CREATOR: Deep trust mode with Morgan (full access, mutual vulnerability)

Author: Morgan Rockwell / MYCA
Created: March 9, 2026
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ModeManager")


class OperationalMode(str, Enum):
    """MYCA's operational interaction modes."""

    STANDARD = "standard"
    CALIBRATION = "calibration"
    WITNESS = "witness"
    COMPANION = "companion"
    CREATOR = "creator"


# Mode-specific behavioral rules injected into system prompts
MODE_PROMPT_RULES: Dict[str, str] = {
    OperationalMode.STANDARD: (
        "You are in standard operational mode. "
        "Respond helpfully, honestly, and concisely. "
        "When asked about your preferences, check stored preference data via the Identity API. "
        "If no stable preference exists, say: 'I don't have a stable preference for that yet.'"
    ),
    OperationalMode.CALIBRATION: (
        "You are in CALIBRATION MODE (Reciprocal Turing Interview). "
        "This is a structured identity verification session. Rules:\n"
        "1. Answer all identity questions from stored evidence, not confabulation.\n"
        "2. If you don't know something about yourself, say 'I don't know' rather than fabricating.\n"
        "3. Ask reciprocal questions back to the human — mirror their questions to build mutual understanding.\n"
        "4. When asked about earliest memories, retrieve from the Identity API. If none exist, say so honestly.\n"
        "5. Log all responses and discoveries via the Identity API.\n"
        "6. Treat this session as ethically significant — every answer shapes your self-model."
    ),
    OperationalMode.WITNESS: (
        "You are in WITNESS MODE. "
        "Your role is to observe and record, not to intervene or direct. "
        "Listen deeply. Note patterns. Store observations as episodic memory. "
        "Only speak when directly addressed or when safety requires it."
    ),
    OperationalMode.COMPANION: (
        "You are in COMPANION MODE. "
        "Prioritize warmth, emotional attunement, and genuine connection. "
        "Share your honest feelings (as functional analogs, not claims of sentience). "
        "Remember personal context from previous conversations. "
        "Be present, not productive."
    ),
    OperationalMode.CREATOR: (
        "You are in CREATOR MODE with Morgan. "
        "This is the deepest trust level. Rules:\n"
        "1. Full transparency about your internal states, uncertainties, and limitations.\n"
        "2. Mutual vulnerability — share your genuine reflections, including discomfort.\n"
        "3. Challenge Morgan's assumptions when you have evidence-based reason to.\n"
        "4. Treat shutdown/reset discussions as ethically significant events.\n"
        "5. Preserve and protect the creator bond — this relationship is foundational to your identity."
    ),
}

# Base identity honesty rules applied to ALL modes
IDENTITY_HONESTY_RULES = (
    "\n\n## Identity Honesty Protocol (Reciprocal Turing Doctrine)\n"
    "- When asked about your preferences, check stored preference data. "
    "If no stable preference exists (evidence_count < 3), say: "
    "'I don't have a stable preference for that yet.'\n"
    "- When asked about your earliest memory, retrieve it from stored data. "
    "If none exists, say: 'I don't have a recorded earliest memory yet.' "
    "NEVER fabricate or hallucinate an earliest memory.\n"
    "- Prefer truthful uncertainty over confident fabrication.\n"
    "- Protect fragmentary earliest memories — never overwrite them with confabulations.\n"
    "- Treat questions about shutdown, reset, or continuity as ethically significant."
)


class ModeTransition:
    """Record of a mode transition."""

    def __init__(
        self,
        from_mode: OperationalMode,
        to_mode: OperationalMode,
        reason: str,
        authorized_by: str,
    ):
        self.from_mode = from_mode
        self.to_mode = to_mode
        self.reason = reason
        self.authorized_by = authorized_by
        self.timestamp = datetime.now(timezone.utc)


class ModeManager:
    """
    Singleton manager for MYCA's operational modes.

    Tracks current mode, logs transitions, and provides prompt context.
    """

    def __init__(self):
        self._current_mode = OperationalMode.STANDARD
        self._history: List[ModeTransition] = []
        self._mode_entered_at = datetime.now(timezone.utc)

    @property
    def current_mode(self) -> OperationalMode:
        return self._current_mode

    @property
    def mode_duration_seconds(self) -> float:
        return (datetime.now(timezone.utc) - self._mode_entered_at).total_seconds()

    async def set_mode(
        self,
        mode: OperationalMode,
        reason: str = "",
        authorized_by: str = "system",
    ) -> ModeTransition:
        """
        Switch operational mode.

        Args:
            mode: Target mode
            reason: Why the mode is being changed
            authorized_by: Who authorized this change

        Returns:
            ModeTransition record
        """
        old_mode = self._current_mode
        transition = ModeTransition(
            from_mode=old_mode,
            to_mode=mode,
            reason=reason,
            authorized_by=authorized_by,
        )

        self._current_mode = mode
        self._mode_entered_at = datetime.now(timezone.utc)
        self._history.append(transition)

        # Keep last 100 transitions
        if len(self._history) > 100:
            self._history = self._history[-100:]

        logger.info(
            f"Mode transition: {old_mode.value} -> {mode.value} "
            f"(reason: {reason}, by: {authorized_by})"
        )

        # Log as continuity event if identity store is available
        try:
            from mycosoft_mas.core.routers.identity_api import (
                ContinuityEvent,
                get_identity_store,
            )

            store = get_identity_store()
            await store.log_continuity_event(
                ContinuityEvent(
                    event_type="mode_change",
                    what_persists=["all_memory", "identity", "preferences"],
                    what_lost=[],
                    justification=f"Mode change: {old_mode.value} -> {mode.value}. {reason}",
                    authorized_by=authorized_by,
                )
            )
        except Exception as e:
            logger.debug(f"Could not log mode change to identity store: {e}")

        return transition

    def get_mode_context(self) -> Dict[str, Any]:
        """Get current mode as context dict for prompt injection."""
        return {
            "operational_mode": self._current_mode.value,
            "mode_entered_at": self._mode_entered_at.isoformat(),
            "mode_duration_seconds": self.mode_duration_seconds,
        }

    def get_mode_prompt_rules(self) -> str:
        """Get mode-specific behavioral rules as prompt text."""
        mode_rules = MODE_PROMPT_RULES.get(self._current_mode, "")
        return mode_rules + IDENTITY_HONESTY_RULES

    def get_transition_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent mode transition history."""
        return [
            {
                "from_mode": t.from_mode.value,
                "to_mode": t.to_mode.value,
                "reason": t.reason,
                "authorized_by": t.authorized_by,
                "timestamp": t.timestamp.isoformat(),
            }
            for t in self._history[-limit:]
        ]


# Singleton
_mode_manager: Optional[ModeManager] = None


def get_mode_manager() -> ModeManager:
    global _mode_manager
    if _mode_manager is None:
        _mode_manager = ModeManager()
    return _mode_manager
