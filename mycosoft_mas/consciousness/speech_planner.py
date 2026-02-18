"""
Speech Planner - Converts token streams into short, interruptible speech acts.

Phase 1 of Full-Duplex Consciousness OS.
Created: February 12, 2026

The SpeechPlanner breaks continuous LLM output into ~1-2 second speech segments
that can be interrupted by user barge-in without losing all generated content.

Speech Act Types:
- backchannel: Short acknowledgments ("Got it", "One sec") - ~300ms
- statement: Main content chunks (~1-2s)
- status: Tool/agent progress ("I'm looking that up...") - ~500ms
- correction: Additive refinement ("One more thing...") - capped at 1 per turn
- final: Last segment of a response
"""

import asyncio
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import AsyncGenerator, Callable, List, Literal, Optional

import logging

logger = logging.getLogger(__name__)


class SpeechActType(str, Enum):
    """Types of speech acts."""
    BACKCHANNEL = "backchannel"  # Short acknowledgment
    STATEMENT = "statement"      # Main content chunk
    STATUS = "status"            # Tool/agent progress
    CORRECTION = "correction"    # Additive refinement (max 1)
    FINAL = "final"              # Last segment


@dataclass
class SpeechAct:
    """A single interruptible speech segment."""
    text: str
    type: SpeechActType
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def estimated_duration_ms(self) -> int:
        """Estimate speech duration at ~150 words per minute."""
        words = len(self.text.split())
        # ~150 WPM = 2.5 words per second = 400ms per word
        return int(words * 400)
    
    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "type": self.type.value,
            "estimated_duration_ms": self.estimated_duration_ms,
        }


class SpeechPlanner:
    """
    Converts continuous token streams into short, interruptible speech acts.
    
    Design goals:
    - Speech acts target 1-2 seconds of speech (~80 chars)
    - Natural break points: sentence endings, commas, long phrases
    - Immediate backchannels before longer processing
    - Tool status updates as separate speech acts
    """
    
    # Target ~80 chars = ~1.5s at normal speaking pace
    TARGET_CHARS = 80
    MIN_CHARS = 40  # Don't emit tiny fragments (increased for stability)
    MAX_CHARS = 150  # Force break for very long sentences
    
    # Sentence-ending punctuation (strong break points)
    SENTENCE_ENDINGS = (".", "!", "?", "...")
    
    # Abbreviations to NOT split on (avoid breaking "Dr. Smith" or "2.5")
    ABBREVIATIONS = (
        "Dr.", "Mr.", "Mrs.", "Ms.", "Prof.", "Jr.", "Sr.",
        "Inc.", "Ltd.", "Corp.", "Co.", "vs.", "etc.", "e.g.", "i.e.",
    )
    
    # Mid-sentence break points (weaker, but OK for long sentences)
    CLAUSE_BREAKS = (",", ";", ":", " - ", " — ")
    
    # Common backchannels
    BACKCHANNELS = [
        "Got it",
        "One sec",
        "Sure",
        "Let me check",
        "Okay",
        "Hmm",
        "I see",
        "Right",
    ]
    
    # Status templates
    STATUS_TEMPLATES = {
        "lookup": "I'm looking that up",
        "search": "I'm searching for that",
        "calculate": "Let me calculate",
        "tool": "I'm working on that",
        "agent": "I'm checking with another agent",
        "memory": "Let me recall",
        "default": "One moment",
    }
    
    def __init__(
        self,
        target_chars: int = TARGET_CHARS,
        min_chars: int = MIN_CHARS,
        max_chars: int = MAX_CHARS,
    ):
        self.target_chars = target_chars
        self.min_chars = min_chars
        self.max_chars = max_chars
    
    async def plan(
        self,
        tokens: AsyncGenerator[str, None],
        on_cancel: Optional[Callable[[], bool]] = None,
    ) -> AsyncGenerator[SpeechAct, None]:
        """
        Convert a token stream into speech acts.
        
        Args:
            tokens: Async generator yielding string tokens
            on_cancel: Optional callback that returns True if cancelled
        
        Yields:
            SpeechAct objects ready for TTS
        """
        buffer = ""
        act_count = 0
        cancelled = False
        
        try:
            async for token in tokens:
                # Check cancellation
                if on_cancel and on_cancel():
                    logger.debug("Speech planning cancelled")
                    cancelled = True
                    break
                
                buffer += token
                
                # Check for natural break points
                break_point = self._find_break_point(buffer)
                
                if break_point is not None:
                    segment = buffer[:break_point].strip()
                    buffer = buffer[break_point:].lstrip()
                    
                    if len(segment) >= self.min_chars:
                        act_count += 1
                        yield SpeechAct(
                            text=segment,
                            type=SpeechActType.STATEMENT,
                        )
        finally:
            # If cancellation ended the loop early, explicitly close upstream generators.
            if cancelled and hasattr(tokens, "aclose"):
                try:
                    await tokens.aclose()
                except Exception:
                    pass
        
        # Yield any remaining content (only if not cancelled)
        if not cancelled and buffer.strip():
            yield SpeechAct(
                text=buffer.strip(),
                type=SpeechActType.FINAL,
            )
    
    def _find_break_point(self, text: str) -> Optional[int]:
        """
        Find a natural break point in the text.
        
        Returns the index after the break point, or None if no good break found.
        """
        # Check for double newline (paragraph break) - always a good break
        double_newline = text.find("\n\n")
        if double_newline > self.min_chars:
            return double_newline + 2
        
        # Don't break too early
        if len(text) < self.target_chars:
            # Unless there's a sentence ending that's not an abbreviation
            for ending in self.SENTENCE_ENDINGS:
                idx = text.rfind(ending)
                if idx > self.min_chars and not self._is_abbreviation(text, idx):
                    return idx + len(ending)
            return None
        
        # Force break on very long text
        if len(text) >= self.max_chars:
            # Find the best break point we can
            for ending in self.SENTENCE_ENDINGS:
                idx = text.rfind(ending, 0, self.max_chars)
                if idx > self.min_chars and not self._is_abbreviation(text, idx):
                    return idx + len(ending)
            
            # Try clause breaks
            for brk in self.CLAUSE_BREAKS:
                idx = text.rfind(brk, 0, self.max_chars)
                if idx > self.min_chars:
                    return idx + len(brk)
            
            # Last resort: break at space
            idx = text.rfind(" ", self.min_chars, self.max_chars)
            if idx > 0:
                return idx + 1
            
            # Absolute fallback
            return self.max_chars
        
        # Normal case: look for sentence endings first (not abbreviations)
        # Find the FIRST valid break point (not the last), that's past min_chars
        best_break = None
        for ending in self.SENTENCE_ENDINGS:
            # Search from min_chars onwards
            idx = text.find(ending, self.min_chars)
            if idx != -1 and idx < len(text) - 1:
                if not self._is_abbreviation(text, idx):
                    # Found a valid break - return the earliest one
                    break_pos = idx + len(ending)
                    if best_break is None or break_pos < best_break:
                        best_break = break_pos
        if best_break is not None:
            return best_break
        
        # Try clause breaks if text is getting long
        if len(text) > self.target_chars * 1.2:
            for brk in self.CLAUSE_BREAKS:
                idx = text.rfind(brk)
                if idx > self.min_chars:
                    return idx + len(brk)
        
        return None
    
    def _is_abbreviation(self, text: str, period_idx: int) -> bool:
        """
        Check if a period at the given index is part of an abbreviation.
        
        Args:
            text: The full text
            period_idx: Index of the period
        
        Returns:
            True if this period is part of an abbreviation, False otherwise
        """
        # Check each known abbreviation
        for abbr in self.ABBREVIATIONS:
            abbr_start = period_idx - len(abbr) + 1
            if abbr_start >= 0:
                if text[abbr_start:period_idx + 1] == abbr:
                    return True
        
        # Check for number pattern (e.g., "2.5", "3.14")
        if period_idx > 0 and period_idx < len(text) - 1:
            char_before = text[period_idx - 1]
            char_after = text[period_idx + 1] if period_idx + 1 < len(text) else " "
            if char_before.isdigit() and char_after.isdigit():
                return True
        
        return False
    
    def backchannel(self, phrase: Optional[str] = None) -> SpeechAct:
        """
        Create a quick backchannel speech act.
        
        Args:
            phrase: Optional custom backchannel phrase
        
        Returns:
            SpeechAct of type BACKCHANNEL
        """
        text = phrase or self.BACKCHANNELS[0]
        return SpeechAct(
            text=text,
            type=SpeechActType.BACKCHANNEL,
        )
    
    def status(self, action: str = "default") -> SpeechAct:
        """
        Create a status update speech act.
        
        Args:
            action: Key from STATUS_TEMPLATES or custom text
        
        Returns:
            SpeechAct of type STATUS
        """
        if action in self.STATUS_TEMPLATES:
            text = self.STATUS_TEMPLATES[action]
        else:
            text = f"I'm {action}"
        
        return SpeechAct(
            text=text,
            type=SpeechActType.STATUS,
        )
    
    def correction(self, addition: str) -> SpeechAct:
        """
        Create an additive correction speech act.
        
        Should be used sparingly (max 1 per turn) to avoid sounding unstable.
        
        Args:
            addition: The additional information to add
        
        Returns:
            SpeechAct of type CORRECTION
        """
        # Prefix with additive phrasing (not "Actually, I was wrong...")
        prefixes = ["One more thing: ", "Also, ", "I should add: "]
        
        # Don't double-prefix if already has one
        text = addition.strip()
        if not any(text.startswith(p) for p in prefixes):
            text = f"One more thing: {text}"
        
        return SpeechAct(
            text=text,
            type=SpeechActType.CORRECTION,
        )
    
    async def plan_with_status(
        self,
        tokens: AsyncGenerator[str, None],
        has_tools: bool = False,
        on_cancel: Optional[Callable[[], bool]] = None,
    ) -> AsyncGenerator[SpeechAct, None]:
        """
        Plan speech acts with an optional leading status if tools are running.
        
        Args:
            tokens: Token stream from LLM
            has_tools: Whether tool calls are in progress
            on_cancel: Cancellation callback
        
        Yields:
            SpeechAct objects, starting with status if needed
        """
        # Lead with status if tools are running
        if has_tools:
            yield self.status("tool")
        
        # Then yield planned speech acts
        async for act in self.plan(tokens, on_cancel):
            yield act
    
    def estimate_duration(self, acts: List[SpeechAct]) -> int:
        """Estimate total duration in milliseconds for a list of speech acts."""
        return sum(act.estimated_duration_ms for act in acts)


# Singleton for easy import
_planner: Optional[SpeechPlanner] = None


def get_speech_planner() -> SpeechPlanner:
    """Get the global SpeechPlanner instance."""
    global _planner
    if _planner is None:
        _planner = SpeechPlanner()
    return _planner
