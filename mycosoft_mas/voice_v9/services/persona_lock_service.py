"""
Voice v9 Persona Lock Service - March 2, 2026.

Checks and rewrites outgoing text so it stays in MYCA identity.
Applied after conversation_cortex and immediately before TTS.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from mycosoft_mas.voice_v9.schemas.persona import PersonaState

logger = logging.getLogger(__name__)

# Patterns that indicate persona bleed (non-MYCA identity)
PERSONA_BLEED_PATTERNS: List[Tuple[re.Pattern, str]] = [
    # Common AI assistant identity leaks
    (re.compile(r"\b(I'm|I am) (an? )?(AI|artificial intelligence|a language model|ChatGPT|Claude|a bot)\b", re.I), "I'm MYCA"),
    (re.compile(r"\bAs (an? )?(AI|artificial intelligence|a language model)\b", re.I), "As MYCA"),
    (re.compile(r"\b(OpenAI|Anthropic|Google)'s\b", re.I), ""),  # Remove vendor attribution
    (re.compile(r"\b(trained by|created by|developed by) (OpenAI|Anthropic|Google)\b", re.I), "built by Mycosoft"),
    (re.compile(r"\b(I (don't|do not) have (a )?)\b(personality|emotions|consciousness)\b", re.I), "I have"),
    # First-person neutral that might need MYCA framing
    # (re.compile(r"^(Sure|Okay|Of course),?\s*", re.I), ""),  # Optional: trim generic lead-ins
]

# MYCA identity framing (prepend when rewrites occur)
MYCA_FRAMING_PHRASES = [
    "From my perspective, ",
    "In my understanding, ",
    "",  # Sometimes no prefix is needed
]


@dataclass
class PersonaLockResult:
    """Result of persona lock check/rewrite."""
    text: str
    was_rewritten: bool
    rewrite_reason: Optional[str] = None
    drift_detected: bool = False
    confidence: float = 1.0


class PersonaLockService:
    """
    Validates and rewrites outgoing speech for MYCA identity consistency.

    PersonaPlex/Moshi is speech infrastructure only; identity must be enforced
    in the conversational layer before text reaches TTS.
    """

    def __init__(self):
        self._rewrite_count = 0
        self._last_reason: Optional[str] = None
        self._drift_count = 0

    def apply(self, session_id: str, text: str) -> PersonaLockResult:
        """
        Check and optionally rewrite text for MYCA persona.

        Returns PersonaLockResult with locked text and metadata.
        """
        if not text or not text.strip():
            return PersonaLockResult(text=text, was_rewritten=False)

        original = text
        rewritten = text
        reason: Optional[str] = None
        drift = False

        for pattern, replacement in PERSONA_BLEED_PATTERNS:
            if pattern.search(rewritten):
                drift = True
                if replacement:
                    rewritten = pattern.sub(replacement, rewritten)
                    reason = f"Replaced persona bleed: {pattern.pattern[:50]}..."
                else:
                    # Remove the matched span
                    rewritten = pattern.sub("", rewritten)
                    reason = f"Removed vendor attribution: {pattern.pattern[:50]}..."
                self._rewrite_count += 1
                self._last_reason = reason
                self._drift_count += 1
                logger.debug(f"Persona lock: {reason}")

        # Collapse extra whitespace after removals
        if rewritten != original:
            rewritten = re.sub(r"\s+", " ", rewritten).strip()

        return PersonaLockResult(
            text=rewritten,
            was_rewritten=rewritten != original,
            rewrite_reason=reason,
            drift_detected=drift,
            confidence=0.95 if drift else 1.0,
        )

    def get_state(self, session_id: str) -> PersonaState:
        """Get current persona state for session."""
        return PersonaState(
            session_id=session_id,
            persona_locked=True,
            rewrite_count=self._rewrite_count,
            last_rewrite_reason=self._last_reason,
            drift_detected=self._drift_count > 0,
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata={"drift_count": self._drift_count},
        )

    def reset_session_stats(self) -> None:
        """Reset rewrite/drift stats (e.g., on new session)."""
        self._rewrite_count = 0
        self._last_reason = None
        self._drift_count = 0


_persona_lock: Optional[PersonaLockService] = None


def get_persona_lock_service() -> PersonaLockService:
    """Get singleton PersonaLockService."""
    global _persona_lock
    if _persona_lock is None:
        _persona_lock = PersonaLockService()
    return _persona_lock
