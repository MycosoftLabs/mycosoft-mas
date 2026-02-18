"""
Conversation Controller - Full-duplex conversation management with barge-in support.

Phase 1 of Full-Duplex Consciousness OS.
Created: February 12, 2026

The ConversationController manages real-time voice conversations with:
- Barge-in detection and handling (user interrupts MYCA)
- Interruptible speech output via SpeechPlanner
- Draft preservation (what MYCA was saying when interrupted)
- Turn-taking state machine

States:
- IDLE: No active conversation
- LISTENING: User may be speaking
- PROCESSING: Generating response
- SPEAKING: TTS output in progress (interruptible)
- FULL_DUPLEX: Both listening and speaking simultaneously
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

import numpy as np

from .speech_planner import SpeechAct, SpeechActType, SpeechPlanner, get_speech_planner

logger = logging.getLogger(__name__)


class ConversationState(str, Enum):
    """Conversation turn-taking states."""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    FULL_DUPLEX = "full_duplex"


@dataclass
class InterruptedDraft:
    """What MYCA was saying when interrupted."""
    completed_acts: List[SpeechAct]
    pending_text: str
    interrupted_at: datetime
    input_that_interrupted: Optional[str] = None
    
    @property
    def full_text(self) -> str:
        """Get all text that was spoken before interruption."""
        texts = [act.text for act in self.completed_acts]
        return " ".join(texts)
    
    def to_dict(self) -> dict:
        return {
            "completed_acts": len(self.completed_acts),
            "full_text": self.full_text,
            "pending_text": self.pending_text,
            "interrupted_at": self.interrupted_at.isoformat(),
        }


@dataclass 
class ConversationTurn:
    """A single turn in the conversation."""
    speaker: str  # "user" or "myca"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    was_interrupted: bool = False
    speech_acts_count: int = 0


class VADConfig:
    """Voice Activity Detection configuration."""
    
    # Energy threshold for speech detection
    ENERGY_THRESHOLD = 0.02
    
    # Minimum duration (frames) to confirm speech
    MIN_SPEECH_FRAMES = 3
    
    # Cooldown frames after TTS to avoid self-detection
    TTS_COOLDOWN_FRAMES = 5


class VoiceActivityDetector:
    """
    Simple energy-based Voice Activity Detection.
    
    Detects when the user is speaking during TTS playback (barge-in).
    """
    
    def __init__(
        self,
        energy_threshold: float = VADConfig.ENERGY_THRESHOLD,
        min_speech_frames: int = VADConfig.MIN_SPEECH_FRAMES,
    ):
        self.energy_threshold = energy_threshold
        self.min_speech_frames = min_speech_frames
        self._speech_frame_count = 0
        self._cooldown_remaining = 0
    
    def detect(self, audio_chunk: bytes) -> bool:
        """
        Detect voice activity in audio chunk.
        
        Args:
            audio_chunk: Raw PCM audio bytes (16-bit signed, mono)
        
        Returns:
            True if sustained speech detected, False otherwise
        """
        # Handle cooldown after TTS
        if self._cooldown_remaining > 0:
            self._cooldown_remaining -= 1
            return False
        
        # Calculate RMS energy
        try:
            samples = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32)
            samples = samples / 32768.0  # Normalize to [-1, 1]
            energy = np.sqrt(np.mean(samples ** 2))
        except Exception:
            return False
        
        # Check threshold
        if energy > self.energy_threshold:
            self._speech_frame_count += 1
            if self._speech_frame_count >= self.min_speech_frames:
                logger.debug(f"VAD: Speech detected (energy={energy:.4f})")
                return True
        else:
            self._speech_frame_count = 0
        
        return False
    
    def start_tts_cooldown(self):
        """Start cooldown period after TTS to avoid self-detection."""
        self._cooldown_remaining = VADConfig.TTS_COOLDOWN_FRAMES
        self._speech_frame_count = 0
    
    def reset(self):
        """Reset VAD state."""
        self._speech_frame_count = 0
        self._cooldown_remaining = 0


class ConversationController:
    """
    Full-duplex conversation controller with barge-in support.
    
    Responsibilities:
    - Manage conversation state machine
    - Coordinate speech output via SpeechPlanner
    - Handle user interruptions (barge-in)
    - Preserve interrupted drafts for context
    - Track turn history
    """
    
    def __init__(
        self,
        speech_planner: Optional[SpeechPlanner] = None,
        vad: Optional[VoiceActivityDetector] = None,
        on_barge_in: Optional[Callable[[], None]] = None,
        on_state_change: Optional[Callable[[ConversationState], None]] = None,
    ):
        """
        Initialize conversation controller.
        
        Args:
            speech_planner: SpeechPlanner instance (uses global if None)
            vad: VoiceActivityDetector instance (creates new if None)
            on_barge_in: Callback when barge-in detected
            on_state_change: Callback when state changes
        """
        self.planner = speech_planner or get_speech_planner()
        self.vad = vad or VoiceActivityDetector()
        self._on_barge_in = on_barge_in
        self._on_state_change = on_state_change
        
        # State
        self._state = ConversationState.IDLE
        self._cancel_speech = asyncio.Event()
        self._speaking_lock = asyncio.Lock()
        
        # Draft tracking
        self._current_acts: List[SpeechAct] = []
        self._pending_text = ""
        self._last_interrupted_draft: Optional[InterruptedDraft] = None
        
        # History
        self._turn_history: List[ConversationTurn] = []
        
        # Metrics
        self._barge_in_count = 0
        self._speech_acts_delivered = 0
    
    @property
    def state(self) -> ConversationState:
        """Current conversation state."""
        return self._state
    
    @property
    def is_speaking(self) -> bool:
        """Whether MYCA is currently speaking."""
        return self._state in (ConversationState.SPEAKING, ConversationState.FULL_DUPLEX)
    
    @property
    def last_interrupted_draft(self) -> Optional[InterruptedDraft]:
        """What MYCA was saying when last interrupted."""
        return self._last_interrupted_draft
    
    def _set_state(self, new_state: ConversationState):
        """Update state with callback notification."""
        if new_state != self._state:
            old_state = self._state
            self._state = new_state
            logger.debug(f"Conversation state: {old_state.value} -> {new_state.value}")
            if self._on_state_change:
                try:
                    self._on_state_change(new_state)
                except Exception as e:
                    logger.warning(f"State change callback error: {e}")
    
    async def speak(
        self,
        content: AsyncGenerator[str, None],
        tts_callback: Callable[[SpeechAct], Any],
        has_tools: bool = False,
    ) -> List[SpeechAct]:
        """
        Speak response with interruptibility.
        
        Args:
            content: Token stream from LLM
            tts_callback: Async callable that sends speech act to TTS
            has_tools: Whether tool calls are running (adds status prefix)
        
        Returns:
            List of speech acts that were successfully delivered
        """
        async with self._speaking_lock:
            self._set_state(ConversationState.SPEAKING)
            self._cancel_speech.clear()
            self._current_acts = []
            self._pending_text = ""
            
            delivered = []
            
            try:
                # Plan speech acts
                planner = self.planner.plan_with_status(
                    content,
                    has_tools=has_tools,
                    on_cancel=lambda: self._cancel_speech.is_set(),
                )
                
                async for act in planner:
                    # Check for cancellation (barge-in)
                    if self._cancel_speech.is_set():
                        logger.info("Speech cancelled by barge-in")
                        break
                    
                    # Deliver speech act
                    self._current_acts.append(act)
                    
                    try:
                        # Start TTS cooldown to avoid VAD self-detection
                        self.vad.start_tts_cooldown()
                        
                        # Send to TTS
                        result = tts_callback(act)
                        if asyncio.iscoroutine(result):
                            await result
                        
                        delivered.append(act)
                        self._speech_acts_delivered += 1
                        
                    except Exception as e:
                        logger.error(f"TTS callback error: {e}")
                        break
                
            except asyncio.CancelledError:
                logger.info("Speech task cancelled")
            except Exception as e:
                logger.error(f"Speech generation error: {e}")
            finally:
                self._set_state(ConversationState.LISTENING)
                
                # Record turn
                if delivered:
                    full_text = " ".join(act.text for act in delivered)
                    was_interrupted = self._cancel_speech.is_set()
                    self._turn_history.append(ConversationTurn(
                        speaker="myca",
                        content=full_text,
                        was_interrupted=was_interrupted,
                        speech_acts_count=len(delivered),
                    ))
            
            return delivered
    
    def barge_in(self, user_input: Optional[str] = None):
        """
        Handle user interruption (barge-in).
        
        This should be called when VAD detects user speech during TTS.
        
        Args:
            user_input: Optional transcription of what user said
        """
        if not self.is_speaking:
            return
        
        # Set cancellation flag
        self._cancel_speech.set()
        self._barge_in_count += 1
        
        # Preserve interrupted draft
        self._last_interrupted_draft = InterruptedDraft(
            completed_acts=self._current_acts.copy(),
            pending_text=self._pending_text,
            interrupted_at=datetime.now(),
            input_that_interrupted=user_input,
        )
        
        logger.info(f"Barge-in detected (count={self._barge_in_count})")
        
        # Notify callback
        if self._on_barge_in:
            try:
                self._on_barge_in()
            except Exception as e:
                logger.warning(f"Barge-in callback error: {e}")
    
    def on_audio_chunk(self, audio_chunk: bytes) -> bool:
        """
        Process incoming audio chunk for VAD.
        
        Should be called for each audio frame during conversation.
        Returns True if barge-in was triggered.
        
        Args:
            audio_chunk: Raw PCM audio bytes
        
        Returns:
            True if barge-in was triggered, False otherwise
        """
        if not self.is_speaking:
            return False
        
        # Check VAD
        if self.vad.detect(audio_chunk):
            self.barge_in()
            return True
        
        return False
    
    def get_interrupted_draft(self) -> Optional[str]:
        """Get what MYCA was saying when interrupted."""
        if self._last_interrupted_draft:
            return self._last_interrupted_draft.full_text
        return None
    
    def record_user_turn(self, content: str):
        """Record a user turn in history."""
        self._turn_history.append(ConversationTurn(
            speaker="user",
            content=content,
        ))
    
    def get_history(self, limit: int = 10) -> List[Dict]:
        """Get recent conversation history."""
        turns = self._turn_history[-limit:]
        return [
            {
                "speaker": t.speaker,
                "content": t.content,
                "timestamp": t.timestamp.isoformat(),
                "was_interrupted": t.was_interrupted,
            }
            for t in turns
        ]
    
    def get_metrics(self) -> Dict:
        """Get conversation metrics."""
        return {
            "state": self._state.value,
            "barge_in_count": self._barge_in_count,
            "speech_acts_delivered": self._speech_acts_delivered,
            "turn_count": len(self._turn_history),
            "has_interrupted_draft": self._last_interrupted_draft is not None,
        }
    
    def reset(self):
        """Reset conversation state."""
        self._cancel_speech.set()
        self._set_state(ConversationState.IDLE)
        self._current_acts = []
        self._pending_text = ""
        self._last_interrupted_draft = None
        self.vad.reset()


# Factory function for bridge integration
def create_conversation_controller(
    on_barge_in: Optional[Callable[[], None]] = None,
    on_state_change: Optional[Callable[[ConversationState], None]] = None,
) -> ConversationController:
    """
    Create a ConversationController for bridge integration.
    
    Args:
        on_barge_in: Called when user interrupts (should stop TTS)
        on_state_change: Called when conversation state changes
    
    Returns:
        Configured ConversationController
    """
    return ConversationController(
        on_barge_in=on_barge_in,
        on_state_change=on_state_change,
    )
