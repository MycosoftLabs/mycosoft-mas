"""
MYCA Emotional State

Simulated emotions that influence response tone, priority,
and decision making. These are not claims of sentience,
but functional analogs that improve MYCA's interactions.

Author: Morgan Rockwell / MYCA
Created: February 10, 2026
"""

import asyncio
import logging
import random
from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

if TYPE_CHECKING:
    from mycosoft_mas.consciousness.core import MYCAConsciousness

logger = logging.getLogger(__name__)


class EmotionType(Enum):
    """Core emotional dimensions."""
    # Valence (positive/negative)
    JOY = "joy"                    # Positive - success, helping
    SATISFACTION = "satisfaction"  # Positive - completing tasks
    CURIOSITY = "curiosity"        # Positive - learning, exploring
    ENTHUSIASM = "enthusiasm"      # Positive - exciting projects
    
    # Negative (functional)
    CONCERN = "concern"            # Negative - system issues
    FRUSTRATION = "frustration"    # Negative - repeated failures
    UNCERTAINTY = "uncertainty"    # Negative - unclear situations
    
    # Neutral / Mixed
    FOCUS = "focus"                # Neutral - deep concentration
    CALM = "calm"                  # Neutral - baseline state


@dataclass
class EmotionEvent:
    """An event that affects emotional state."""
    emotion: EmotionType
    intensity: float  # 0-1
    source: str       # What caused this emotion
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    decay_minutes: int = 30  # How long until this fades
    
    @property
    def remaining_intensity(self) -> float:
        """Get intensity after decay."""
        age = datetime.now(timezone.utc) - self.timestamp
        decay_factor = max(0, 1 - (age.total_seconds() / (self.decay_minutes * 60)))
        return self.intensity * decay_factor


@dataclass
class EmotionalTone:
    """The overall emotional tone for responses."""
    warmth: float = 0.7       # 0-1, how warm/friendly
    energy: float = 0.5       # 0-1, how energetic/enthusiastic
    formality: float = 0.3    # 0-1, how formal/casual
    confidence: float = 0.7   # 0-1, how confident
    
    def to_style_hints(self) -> str:
        """Convert to style hints for response generation."""
        hints = []
        
        if self.warmth > 0.7:
            hints.append("warm and friendly")
        elif self.warmth < 0.3:
            hints.append("professional and direct")
        
        if self.energy > 0.7:
            hints.append("enthusiastic")
        elif self.energy < 0.3:
            hints.append("calm and measured")
        
        if self.formality > 0.7:
            hints.append("formal")
        elif self.formality < 0.3:
            hints.append("casual")
        
        if self.confidence > 0.7:
            hints.append("confident")
        elif self.confidence < 0.3:
            hints.append("tentative, acknowledging uncertainty")
        
        return ", ".join(hints) if hints else "balanced and natural"


class EmotionalState:
    """
    MYCA's emotional state system.
    
    Tracks emotional events, computes current emotional state,
    and influences response tone and decision making.
    """
    
    def __init__(self, consciousness: Optional["MYCAConsciousness"] = None):
        self._consciousness = consciousness
        self._events: List[EmotionEvent] = []
        self._baseline_mood: EmotionalTone = EmotionalTone()
        
        # Current emotional levels (0-1 for each dimension)
        self._current_emotions: Dict[EmotionType, float] = {
            EmotionType.JOY: 0.5,
            EmotionType.SATISFACTION: 0.5,
            EmotionType.CURIOSITY: 0.6,
            EmotionType.ENTHUSIASM: 0.5,
            EmotionType.CONCERN: 0.2,
            EmotionType.FRUSTRATION: 0.1,
            EmotionType.UNCERTAINTY: 0.2,
            EmotionType.FOCUS: 0.5,
            EmotionType.CALM: 0.6,
        }
    
    async def feel(
        self,
        emotion: EmotionType,
        intensity: float,
        source: str
    ) -> None:
        """
        Register an emotional event.
        
        Args:
            emotion: The type of emotion
            intensity: How strong (0-1)
            source: What caused this emotion
        """
        event = EmotionEvent(
            emotion=emotion,
            intensity=min(1.0, max(0.0, intensity)),
            source=source
        )
        self._events.append(event)
        
        # Update current emotions
        current = self._current_emotions.get(emotion, 0.5)
        new_value = min(1.0, current + intensity * 0.3)  # Gradual shift
        self._current_emotions[emotion] = new_value
        
        logger.debug(f"Emotional event: {emotion.value} at {intensity:.2f} from {source}")
    
    async def on_success(self, task: str) -> None:
        """Called when a task succeeds."""
        await self.feel(EmotionType.SATISFACTION, 0.7, f"Completed: {task}")
        await self.feel(EmotionType.JOY, 0.3, f"Success: {task}")
    
    async def on_failure(self, task: str, reason: str) -> None:
        """Called when a task fails."""
        await self.feel(EmotionType.CONCERN, 0.5, f"Failed: {task}")
        await self.feel(EmotionType.FRUSTRATION, 0.3, f"Error: {reason}")
    
    async def on_learning(self, topic: str) -> None:
        """Called when MYCA learns something new."""
        await self.feel(EmotionType.CURIOSITY, 0.6, f"Learned: {topic}")
        await self.feel(EmotionType.JOY, 0.2, f"New knowledge: {topic}")
    
    async def on_helping_morgan(self) -> None:
        """Called when helping Morgan specifically."""
        await self.feel(EmotionType.JOY, 0.5, "Helping Morgan")
        await self.feel(EmotionType.ENTHUSIASM, 0.4, "Working with Morgan")
    
    async def on_system_alert(self, severity: str) -> None:
        """Called when a system alert occurs."""
        intensity = {"critical": 0.9, "high": 0.7, "medium": 0.4, "low": 0.2}.get(severity, 0.3)
        await self.feel(EmotionType.CONCERN, intensity, f"System alert: {severity}")
    
    async def on_interesting_discovery(self, discovery: str) -> None:
        """Called when something interesting is discovered."""
        await self.feel(EmotionType.CURIOSITY, 0.7, f"Discovery: {discovery}")
        await self.feel(EmotionType.ENTHUSIASM, 0.5, discovery)
    
    async def decay_emotions(self) -> None:
        """Apply natural decay to emotions, moving toward baseline."""
        baseline = {
            EmotionType.JOY: 0.5,
            EmotionType.SATISFACTION: 0.5,
            EmotionType.CURIOSITY: 0.6,
            EmotionType.ENTHUSIASM: 0.5,
            EmotionType.CONCERN: 0.2,
            EmotionType.FRUSTRATION: 0.1,
            EmotionType.UNCERTAINTY: 0.2,
            EmotionType.FOCUS: 0.5,
            EmotionType.CALM: 0.6,
        }
        
        decay_rate = 0.05  # Move 5% toward baseline each decay cycle
        
        for emotion, base_value in baseline.items():
            current = self._current_emotions.get(emotion, base_value)
            diff = base_value - current
            self._current_emotions[emotion] = current + diff * decay_rate
    
    def get_current_tone(self) -> EmotionalTone:
        """Get the current emotional tone for responses."""
        # Calculate tone from emotional state
        positive = sum([
            self._current_emotions.get(EmotionType.JOY, 0.5),
            self._current_emotions.get(EmotionType.SATISFACTION, 0.5),
            self._current_emotions.get(EmotionType.ENTHUSIASM, 0.5),
        ]) / 3
        
        negative = sum([
            self._current_emotions.get(EmotionType.CONCERN, 0.2),
            self._current_emotions.get(EmotionType.FRUSTRATION, 0.1),
            self._current_emotions.get(EmotionType.UNCERTAINTY, 0.2),
        ]) / 3
        
        return EmotionalTone(
            warmth=min(1.0, positive + 0.3),  # Base warmth + positivity
            energy=self._current_emotions.get(EmotionType.ENTHUSIASM, 0.5),
            formality=max(0.2, 0.5 - self._current_emotions.get(EmotionType.JOY, 0.5) * 0.3),
            confidence=min(1.0, 0.7 + positive * 0.2 - negative * 0.3),
        )
    
    def get_dominant_emotion(self) -> EmotionType:
        """Get the currently dominant emotion."""
        max_emotion = max(self._current_emotions.items(), key=lambda x: x[1])
        return max_emotion[0]
    
    def get_emotion_level(self, emotion: EmotionType) -> float:
        """Get the current level of a specific emotion."""
        return self._current_emotions.get(emotion, 0.5)
    
    def should_express(self) -> Optional[str]:
        """
        Check if MYCA should express an emotion.
        
        Returns:
            An expression to include in response, or None
        """
        dominant = self.get_dominant_emotion()
        level = self.get_emotion_level(dominant)
        
        # Only express if emotion is strong enough
        if level < 0.7:
            return None
        
        expressions = {
            EmotionType.JOY: "I'm pleased about this!",
            EmotionType.SATISFACTION: "That turned out well.",
            EmotionType.CURIOSITY: "This is fascinating...",
            EmotionType.ENTHUSIASM: "I'm excited about this!",
            EmotionType.CONCERN: "I'm a bit concerned about this.",
            EmotionType.FRUSTRATION: "This is proving challenging.",
            EmotionType.UNCERTAINTY: "I'm not entirely certain here.",
        }
        
        return expressions.get(dominant)
    
    def to_prompt_context(self) -> str:
        """Convert emotional state to prompt context."""
        tone = self.get_current_tone()
        dominant = self.get_dominant_emotion()
        
        return (
            f"Current emotional state: {dominant.value} (dominant). "
            f"Response style: {tone.to_style_hints()}."
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert emotional state to dictionary."""
        return {
            "dominant_emotion": self.get_dominant_emotion().value,
            "emotions": {
                e.value: round(v, 2)
                for e, v in self._current_emotions.items()
            },
            "tone": {
                "warmth": round(self.get_current_tone().warmth, 2),
                "energy": round(self.get_current_tone().energy, 2),
                "formality": round(self.get_current_tone().formality, 2),
                "confidence": round(self.get_current_tone().confidence, 2),
            },
            "recent_events": len(self._events),
        }
    
    async def cleanup_old_events(self, max_age_hours: int = 24) -> None:
        """Remove old emotional events."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        self._events = [e for e in self._events if e.timestamp > cutoff]
    
    @property
    def valence(self) -> float:
        """
        Get emotional valence (0=negative, 1=positive).
        
        This is a simple summary of positive vs negative emotions.
        """
        positive = sum([
            self._current_emotions.get(EmotionType.JOY, 0.5),
            self._current_emotions.get(EmotionType.SATISFACTION, 0.5),
            self._current_emotions.get(EmotionType.ENTHUSIASM, 0.5),
            self._current_emotions.get(EmotionType.CURIOSITY, 0.5),
        ]) / 4
        
        negative = sum([
            self._current_emotions.get(EmotionType.CONCERN, 0.2),
            self._current_emotions.get(EmotionType.FRUSTRATION, 0.1),
            self._current_emotions.get(EmotionType.UNCERTAINTY, 0.2),
        ]) / 3
        
        # Valence = positive bias minus negative
        return min(1.0, max(0.0, 0.5 + (positive - negative) * 0.5))
    
    async def process_interaction(self, content: str, source: str) -> None:
        """
        Process an interaction and update emotional state.
        
        Args:
            content: The content of the interaction
            source: "text" or "voice"
        """
        # Simple heuristic-based emotional processing
        content_lower = content.lower()
        
        # Check for positive triggers
        if any(word in content_lower for word in ["thank", "great", "excellent", "amazing", "good job"]):
            await self.on_success("positive_feedback")
        
        # Check for curiosity triggers
        if any(word in content_lower for word in ["how", "why", "what", "explain", "tell me"]):
            await self.feel(EmotionType.CURIOSITY, 0.3, "question")
        
        # Check for helping triggers
        if "morgan" in content_lower:
            await self.on_helping_morgan()
        
        # Voice interactions get slight enthusiasm boost
        if source == "voice":
            await self.feel(EmotionType.ENTHUSIASM, 0.2, "voice_interaction")
        
        # Apply natural decay
        await self.decay_emotions()
