"""
Full-Duplex Voice Enhancement for MYCA Voice System
Created: February 4, 2026

Enhanced full-duplex voice with background announcements,
intelligent interrupts, and continuous conversation flow.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json

logger = logging.getLogger(__name__)


class VoiceState(Enum):
    """State of the voice system."""
    IDLE = "idle"
    LISTENING = "listening"
    SPEAKING = "speaking"
    PROCESSING = "processing"
    INTERRUPTED = "interrupted"


class AnnouncementPriority(Enum):
    """Priority of announcements."""
    INTERRUPT = 1     # Immediately interrupt current speech
    URGENT = 2        # Queue for next opportunity
    NORMAL = 3        # Standard queue position
    BACKGROUND = 4    # Only when completely idle


@dataclass
class QueuedAnnouncement:
    """An announcement in the queue."""
    announcement_id: str
    message: str
    priority: AnnouncementPriority
    source: str
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    callback: Optional[Callable] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at


@dataclass
class ConversationTurn:
    """A turn in the conversation."""
    role: str  # user, assistant
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    was_interrupted: bool = False
    processing_time_ms: Optional[int] = None


class FullDuplexVoice:
    """
    Full-duplex voice system with background announcements.
    
    Features:
    - Continuous listening during speech
    - Intelligent interrupt detection
    - Background announcement queue
    - Natural conversation flow
    - Barge-in handling
    """
    
    def __init__(
        self,
        personaplex_url: str = "ws://localhost:8999/api/chat",
        speech_callback: Optional[Callable[[str], Awaitable[None]]] = None,
    ):
        self.personaplex_url = personaplex_url
        self.speech_callback = speech_callback
        
        # State
        self.state = VoiceState.IDLE
        self.current_speech: Optional[str] = None
        self.speech_position: int = 0
        
        # Announcement queue
        self.announcement_queue: List[QueuedAnnouncement] = []
        
        # Conversation history
        self.conversation: List[ConversationTurn] = []
        
        # Settings
        self.allow_interrupts = True
        self.interrupt_sensitivity = 0.7  # 0-1, higher = more sensitive
        self.min_speech_before_interrupt = 500  # ms
        
        # Background processing
        self._running = False
        self._queue_task: Optional[asyncio.Task] = None
        
        logger.info("FullDuplexVoice initialized")
    
    async def start(self):
        """Start the full-duplex voice system."""
        self._running = True
        self._queue_task = asyncio.create_task(self._process_queue_loop())
        self.state = VoiceState.IDLE
        logger.info("FullDuplexVoice started")
    
    async def stop(self):
        """Stop the voice system."""
        self._running = False
        if self._queue_task:
            self._queue_task.cancel()
        self.state = VoiceState.IDLE
        logger.info("FullDuplexVoice stopped")
    
    async def speak(self, text: str, can_interrupt: bool = True) -> bool:
        """
        Speak text with interrupt support.
        
        Args:
            text: Text to speak
            can_interrupt: Whether user can interrupt
            
        Returns:
            True if completed, False if interrupted
        """
        self.state = VoiceState.SPEAKING
        self.current_speech = text
        self.speech_position = 0
        
        # Add to conversation
        turn = ConversationTurn(role="assistant", content=text)
        self.conversation.append(turn)
        
        logger.info(f"Speaking: {text[:50]}...")
        
        # Send to speech system
        if self.speech_callback:
            try:
                await self.speech_callback(text)
            except asyncio.CancelledError:
                turn.was_interrupted = True
                self.state = VoiceState.INTERRUPTED
                logger.info("Speech interrupted")
                return False
        
        self.current_speech = None
        self.state = VoiceState.IDLE
        return True
    
    async def handle_user_input(self, transcript: str) -> Dict[str, Any]:
        """
        Handle user voice input.
        
        Args:
            transcript: User's speech transcript
            
        Returns:
            Processing result
        """
        start_time = datetime.now()
        
        # Check if this is an interrupt
        is_interrupt = self.state == VoiceState.SPEAKING
        
        if is_interrupt:
            await self._handle_interrupt(transcript)
        
        # Add to conversation
        turn = ConversationTurn(role="user", content=transcript)
        self.conversation.append(turn)
        
        self.state = VoiceState.PROCESSING
        
        # Process the input (would route to intent classifier in production)
        result = await self._process_input(transcript)
        
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        turn.processing_time_ms = int(processing_time)
        
        return {
            "transcript": transcript,
            "was_interrupt": is_interrupt,
            "processing_time_ms": processing_time,
            "result": result,
        }
    
    async def _handle_interrupt(self, transcript: str):
        """Handle an interrupt from the user."""
        logger.info(f"User interrupted with: {transcript[:30]}...")
        
        # Cancel current speech
        self.state = VoiceState.INTERRUPTED
        
        # Brief acknowledgment
        if self.speech_callback:
            await self.speech_callback("Got it.")
    
    async def _process_input(self, transcript: str) -> Dict[str, Any]:
        """Process user input and generate response."""
        # Placeholder - would integrate with intent classifier and agents
        return {
            "intent": "unknown",
            "response": f"I heard: {transcript}",
        }
    
    async def queue_announcement(
        self,
        message: str,
        priority: AnnouncementPriority = AnnouncementPriority.NORMAL,
        source: str = "system",
        expires_in_seconds: Optional[int] = None,
        callback: Optional[Callable] = None,
    ) -> str:
        """
        Queue an announcement for delivery.
        
        Args:
            message: Message to announce
            priority: Announcement priority
            source: Source of the announcement
            expires_in_seconds: Optional expiration
            callback: Optional callback after delivery
            
        Returns:
            Announcement ID
        """
        import hashlib
        ann_id = hashlib.md5(f"{message}{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        
        expires_at = None
        if expires_in_seconds:
            from datetime import timedelta
            expires_at = datetime.now() + timedelta(seconds=expires_in_seconds)
        
        announcement = QueuedAnnouncement(
            announcement_id=ann_id,
            message=message,
            priority=priority,
            source=source,
            expires_at=expires_at,
            callback=callback,
        )
        
        # Handle immediate interrupts
        if priority == AnnouncementPriority.INTERRUPT:
            await self._deliver_interrupt(announcement)
        else:
            # Add to queue in priority order
            self.announcement_queue.append(announcement)
            self.announcement_queue.sort(key=lambda a: a.priority.value)
        
        logger.info(f"Queued announcement: {ann_id} ({priority.name})")
        return ann_id
    
    async def _deliver_interrupt(self, announcement: QueuedAnnouncement):
        """Deliver an interrupt announcement immediately."""
        if self.state == VoiceState.SPEAKING:
            self.state = VoiceState.INTERRUPTED
        
        await self.speak(announcement.message, can_interrupt=True)
        
        if announcement.callback:
            try:
                announcement.callback()
            except Exception as e:
                logger.error(f"Announcement callback failed: {e}")
    
    async def _process_queue_loop(self):
        """Background loop to process announcement queue."""
        while self._running:
            try:
                await self._process_next_announcement()
                await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Queue processing error: {e}")
                await asyncio.sleep(1)
    
    async def _process_next_announcement(self):
        """Process the next announcement if appropriate."""
        if not self.announcement_queue:
            return
        
        # Check if we can deliver
        if self.state not in (VoiceState.IDLE,):
            return
        
        # Get next announcement
        announcement = self.announcement_queue[0]
        
        # Check expiration
        if announcement.is_expired():
            self.announcement_queue.pop(0)
            return
        
        # Check priority requirements
        if announcement.priority == AnnouncementPriority.BACKGROUND:
            # Only if completely idle for a while
            if len(self.conversation) > 0:
                last_turn = self.conversation[-1]
                idle_time = (datetime.now() - last_turn.timestamp).total_seconds()
                if idle_time < 5:  # Wait 5 seconds of idle
                    return
        
        # Deliver the announcement
        self.announcement_queue.pop(0)
        await self.speak(announcement.message, can_interrupt=True)
        
        if announcement.callback:
            try:
                announcement.callback()
            except Exception as e:
                logger.error(f"Announcement callback failed: {e}")
    
    def get_conversation_context(self, max_turns: int = 10) -> List[Dict[str, str]]:
        """Get recent conversation for context."""
        recent = self.conversation[-max_turns:]
        return [
            {"role": t.role, "content": t.content}
            for t in recent
        ]
    
    def clear_queue(self, priority: Optional[AnnouncementPriority] = None):
        """Clear announcements from the queue."""
        if priority:
            self.announcement_queue = [
                a for a in self.announcement_queue
                if a.priority != priority
            ]
        else:
            self.announcement_queue.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get voice system statistics."""
        return {
            "state": self.state.value,
            "queue_size": len(self.announcement_queue),
            "conversation_turns": len(self.conversation),
            "allow_interrupts": self.allow_interrupts,
            "running": self._running,
        }


class VoiceFlowController:
    """
    Controller for natural conversation flow.
    
    Features:
    - Turn-taking management
    - Response latency optimization
    - Natural pause detection
    - Backchannel responses
    """
    
    BACKCHANNELS = ["mm-hmm", "I see", "okay", "got it", "right"]
    
    def __init__(self, voice: FullDuplexVoice):
        self.voice = voice
        self.last_user_turn: Optional[datetime] = None
        self.pending_response: Optional[str] = None
        
        logger.info("VoiceFlowController initialized")
    
    async def handle_pause(self, pause_duration_ms: int):
        """Handle a pause in user speech."""
        # Short pause - might be thinking
        if pause_duration_ms < 500:
            return
        
        # Medium pause - give backchannel
        if pause_duration_ms < 2000:
            import random
            backchannel = random.choice(self.BACKCHANNELS)
            await self.voice.speak(backchannel, can_interrupt=True)
            return
        
        # Long pause - user probably done
        if self.pending_response:
            await self.voice.speak(self.pending_response)
            self.pending_response = None
    
    async def prepare_response(self, response: str):
        """Prepare a response for delivery."""
        self.pending_response = response
    
    async def deliver_response_when_ready(self, response: str, max_wait_ms: int = 3000):
        """Deliver response with natural timing."""
        self.pending_response = response
        
        # Wait for natural pause or timeout
        waited = 0
        while waited < max_wait_ms:
            if self.voice.state == VoiceState.IDLE:
                break
            await asyncio.sleep(0.1)
            waited += 100
        
        if self.pending_response:
            await self.voice.speak(self.pending_response)
            self.pending_response = None


# Singleton
_voice_instance: Optional[FullDuplexVoice] = None


def get_full_duplex_voice() -> FullDuplexVoice:
    global _voice_instance
    if _voice_instance is None:
        _voice_instance = FullDuplexVoice()
    return _voice_instance


__all__ = [
    "FullDuplexVoice",
    "VoiceFlowController",
    "VoiceState",
    "AnnouncementPriority",
    "QueuedAnnouncement",
    "ConversationTurn",
    "get_full_duplex_voice",
]
