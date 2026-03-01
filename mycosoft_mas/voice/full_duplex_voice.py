"""
Full-Duplex Voice Enhancement for MYCA Voice System
Created: February 4, 2026

Enhanced full-duplex voice with background announcements,
intelligent interrupts, and continuous conversation flow.
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Awaitable
from urllib.parse import urlencode
from uuid import uuid4

import aiohttp

try:
    from mycosoft_mas.consciousness.conversation_control import VoiceActivityDetector
except Exception:  # pragma: no cover - fallback when dependency is unavailable
    VoiceActivityDetector = None

logger = logging.getLogger(__name__)


class VoiceState(Enum):
    """State of the voice system."""
    IDLE = "idle"
    LISTENING = "listening"
    SPEAKING = "speaking"
    PROCESSING = "processing"
    INTERRUPTED = "interrupted"


class VoiceSessionState(Enum):
    """Session lifecycle state."""
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"


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
        audio_callback: Optional[Callable[[bytes], Awaitable[None]]] = None,
        text_callback: Optional[Callable[[str], Awaitable[None]]] = None,
    ):
        self.personaplex_url = personaplex_url
        self.speech_callback = speech_callback
        self.audio_callback = audio_callback
        self.text_callback = text_callback
        
        # State
        self.state = VoiceState.IDLE
        self.current_speech: Optional[str] = None
        self.speech_position: int = 0
        
        # Announcement queue
        self.announcement_queue: List[QueuedAnnouncement] = []
        
        # Conversation history
        self.conversation: List[ConversationTurn] = []
        self.conversation_id: Optional[str] = None
        self.session_id: Optional[str] = None
        self.user_id: Optional[str] = None
        self.session_state = VoiceSessionState.ENDED
        
        # Settings
        self.allow_interrupts = True
        self._current_can_interrupt = True
        self.interrupt_sensitivity = 0.7  # 0-1, higher = more sensitive
        self.min_speech_before_interrupt = 500  # ms
        self.forward_audio_to_bridge = os.getenv("VOICE_FORWARD_AUDIO", "true").lower() == "true"
        self.bridge_ws_base = os.getenv(
            "PERSONAPLEX_BRIDGE_WS_URL",
            self.personaplex_url.replace("/api/chat", ""),
        ).rstrip("/")
        
        # Background processing
        self._running = False
        self._queue_task: Optional[asyncio.Task] = None
        self._bridge_task: Optional[asyncio.Task] = None
        self._bridge_http: Optional[aiohttp.ClientSession] = None
        self._bridge_ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._tts_reset_task: Optional[asyncio.Task] = None

        self._vad = VoiceActivityDetector() if VoiceActivityDetector else None
        self._speech_started_at: Optional[float] = None

        if self._vad:
            # Adjust VAD sensitivity based on configured interrupt sensitivity.
            base_frames = 3
            extra_frames = int(round((1.0 - self.interrupt_sensitivity) * 2.0))
            self._vad.min_speech_frames = max(1, base_frames + extra_frames)
            base_threshold = 0.02
            scaled_threshold = base_threshold * (1.4 - (0.4 * self.interrupt_sensitivity))
            self._vad.energy_threshold = max(0.008, min(0.08, scaled_threshold))
        
        logger.info("FullDuplexVoice initialized")
    
    async def start(self):
        """Start the full-duplex voice system."""
        self._running = True
        self._queue_task = asyncio.create_task(self._process_queue_loop())
        self.state = VoiceState.IDLE
        if self.session_state == VoiceSessionState.ENDED:
            await self.start_session()
        logger.info("FullDuplexVoice started")
    
    async def stop(self):
        """Stop the voice system."""
        self._running = False
        if self._queue_task:
            self._queue_task.cancel()
        await self.end_session()
        self.state = VoiceState.IDLE
        logger.info("FullDuplexVoice stopped")

    async def start_session(
        self,
        *,
        session_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        connect_bridge: bool = True,
    ):
        """Start a voice session and optionally connect to PersonaPlex Bridge."""
        if self.session_state == VoiceSessionState.ACTIVE:
            return
        if session_id:
            self.session_id = session_id
        if conversation_id:
            self.conversation_id = conversation_id
        if user_id:
            self.user_id = user_id
        if self.conversation_id is None:
            self.conversation_id = str(uuid4())
        if self.session_id is None:
            self.session_id = str(uuid4())
        self.session_state = VoiceSessionState.ACTIVE
        if connect_bridge:
            await self.connect_bridge()

    async def pause_session(self):
        """Pause the current voice session."""
        if self.session_state != VoiceSessionState.ACTIVE:
            return
        self.session_state = VoiceSessionState.PAUSED
        if self._vad:
            self._vad.start_tts_cooldown()
        logger.info("Voice session paused")

    async def resume_session(self):
        """Resume a paused voice session."""
        if self.session_state != VoiceSessionState.PAUSED:
            return
        self.session_state = VoiceSessionState.ACTIVE
        logger.info("Voice session resumed")

    async def end_session(self):
        """End the session and disconnect from PersonaPlex Bridge."""
        self.session_state = VoiceSessionState.ENDED
        await self._disconnect_bridge()

    async def connect_bridge(self):
        """Connect to PersonaPlex Bridge WebSocket for Moshi STT/TTS."""
        if self._bridge_ws and not self._bridge_ws.closed:
            return
        if self.session_id is None:
            self.session_id = str(uuid4())
        params: Dict[str, str] = {}
        if self.conversation_id:
            params["conversation_id"] = self.conversation_id
        if self.user_id:
            params["user_id"] = self.user_id
        query = f"?{urlencode(params)}" if params else ""
        ws_url = f"{self.bridge_ws_base}/ws/{self.session_id}{query}"

        if self._bridge_http is None or self._bridge_http.closed:
            self._bridge_http = aiohttp.ClientSession()
        try:
            self._bridge_ws = await self._bridge_http.ws_connect(ws_url, heartbeat=30)
            self._bridge_task = asyncio.create_task(self._bridge_listen_loop())
            logger.info(f"Connected to PersonaPlex Bridge: {ws_url}")
        except Exception as e:
            logger.error(f"Failed to connect to PersonaPlex Bridge: {e}")

    async def _disconnect_bridge(self):
        if self._bridge_task:
            self._bridge_task.cancel()
            self._bridge_task = None
        if self._bridge_ws and not self._bridge_ws.closed:
            await self._bridge_ws.close()
        self._bridge_ws = None
        if self._bridge_http and not self._bridge_http.closed:
            await self._bridge_http.close()
        self._bridge_http = None

    async def _bridge_listen_loop(self):
        """Listen for Bridge messages (TTS audio + text)."""
        if not self._bridge_ws:
            return
        try:
            async for msg in self._bridge_ws:
                if msg.type == aiohttp.WSMsgType.BINARY:
                    if self.audio_callback:
                        await self.audio_callback(msg.data)
                elif msg.type == aiohttp.WSMsgType.TEXT:
                    await self._handle_bridge_text(msg.data)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    break
        except asyncio.CancelledError:
            return
        except Exception as e:
            logger.warning(f"Bridge listen loop error: {e}")

    async def _handle_bridge_text(self, payload: str):
        try:
            data = json.loads(payload)
        except Exception:
            return
        if data.get("type") == "text" and self.text_callback:
            await self.text_callback(data.get("text", ""))

    async def _send_bridge_json(self, payload: Dict[str, Any]):
        if not self._bridge_ws or self._bridge_ws.closed:
            return
        await self._bridge_ws.send_json(payload)

    async def send_audio_chunk(self, audio_bytes: bytes):
        """Forward audio to Bridge and perform local VAD for barge-in."""
        if self.session_state != VoiceSessionState.ACTIVE:
            return
        if (
            self.allow_interrupts
            and self._current_can_interrupt
            and self.state == VoiceState.SPEAKING
            and self._vad
        ):
            if self._speech_started_at is not None:
                elapsed_ms = (time.monotonic() - self._speech_started_at) * 1000.0
                if elapsed_ms < self.min_speech_before_interrupt:
                    return
            if self._vad.detect(audio_bytes):
                await self._handle_interrupt("barge-in")
                await self._send_bridge_json({"type": "barge_in"})
        if self.forward_audio_to_bridge and self._bridge_ws and not self._bridge_ws.closed:
            await self._bridge_ws.send_bytes(audio_bytes)
    
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
        self._current_can_interrupt = can_interrupt
        self.current_speech = text
        self.speech_position = 0
        self._speech_started_at = time.monotonic()
        
        # Add to conversation
        turn = ConversationTurn(role="assistant", content=text)
        self.conversation.append(turn)
        
        logger.info(f"Speaking: {text[:50]}...")
        
        # Send to speech system (Bridge or custom callback)
        try:
            if self.speech_callback:
                await self.speech_callback(text)
            else:
                await self._send_bridge_json({"text": text, "forward_to_moshi": True})
        except asyncio.CancelledError:
            turn.was_interrupted = True
            self.state = VoiceState.INTERRUPTED
            logger.info("Speech interrupted")
            return False
        except Exception as e:
            logger.error(f"Speech callback failed: {e}")
            self.state = VoiceState.IDLE
            return False

        # Fallback: estimate TTS completion for barge-in window
        self._schedule_tts_reset(text)
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
        
        if self.session_state == VoiceSessionState.PAUSED:
            await self.resume_session()
        if self.session_state != VoiceSessionState.ACTIVE:
            await self.start_session()

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
        if self.conversation and self.conversation[-1].role == "assistant":
            self.conversation[-1].was_interrupted = True
        
        # Brief acknowledgment
        try:
            if self.speech_callback:
                await self.speech_callback("Got it.")
            else:
                await self._send_bridge_json({"text": "Got it.", "forward_to_moshi": True})
        except Exception as e:
            logger.warning(f"Interrupt acknowledgement failed: {e}")

    def _schedule_tts_reset(self, text: str):
        """Estimate TTS duration to keep SPEAKING state for barge-in."""
        if self._tts_reset_task:
            self._tts_reset_task.cancel()
        # ~12 chars/sec baseline, min 1.2s, max 15s
        seconds = max(1.2, min(15.0, len(text) / 12.0))
        self._tts_reset_task = asyncio.create_task(self._reset_tts_state_after(seconds))

    async def _reset_tts_state_after(self, seconds: float):
        try:
            await asyncio.sleep(seconds)
        except asyncio.CancelledError:
            return
        if self.state == VoiceState.SPEAKING:
            self.current_speech = None
            self.state = VoiceState.IDLE
            self._speech_started_at = None
        if self._vad:
            self._vad.start_tts_cooldown()
    
    async def _process_input(self, transcript: str) -> Dict[str, Any]:
        """Process user input and generate response."""
        try:
            from mycosoft_mas.voice.intent_classifier import classify_voice_command
            from mycosoft_mas.voice.command_registry import get_command_registry
        except Exception as e:
            logger.error(f"Voice intent components unavailable: {e}")
            return {
                "intent": "unavailable",
                "response": "Voice intent system is not available.",
                "route": "error",
            }

        if self.conversation_id is None:
            self.conversation_id = str(uuid4())
        if self.session_id is None:
            self.session_id = str(uuid4())

        intent = classify_voice_command(transcript)
        registry = get_command_registry()
        command_match = registry.match(transcript)

        context = {
            "source": "voice-full-duplex",
            "modality": "voice",
            "conversation_id": self.conversation_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "voice_intent": {
                "category": intent.intent_category,
                "action": intent.intent_action,
                "confidence": intent.confidence,
                "priority": intent.priority.value,
            },
        }

        if command_match:
            registry.record_usage(command_match.command_id)
            command = registry.get_command(command_match.command_id)
            context["voice_command"] = {
                "command_id": command_match.command_id,
                "confidence": command_match.confidence,
                "handler_type": command.handler.handler_type if command else None,
                "handler_id": command.handler.handler_id if command else None,
                "endpoint": command.handler.endpoint if command else None,
                "method": command.handler.method if command else None,
                "matched_pattern": command_match.matched_pattern,
                "captured_groups": command_match.captured_groups,
            }
            response = await self._route_via_unified_router(transcript, context)
            return {
                "intent": intent.intent_category,
                "command_id": command_match.command_id,
                "response": response,
                "route": "unified_router",
            }

        response = await self._route_via_orchestrator(transcript, context)
        return {
            "intent": intent.intent_category,
            "response": response,
            "route": "voice_orchestrator",
        }

    async def _route_via_unified_router(self, transcript: str, context: Dict[str, Any]) -> str:
        """Route via unified router for agent/workflow/tool dispatch."""
        try:
            from mycosoft_mas.consciousness.unified_router import get_unified_router
            router = get_unified_router()
            result = await router.route_sync(transcript, context=context)
            return result.response or "No response available."
        except Exception as e:
            logger.error(f"Unified router failed: {e}")
            return "Unable to route the request through the unified router."

    async def _route_via_orchestrator(self, transcript: str, context: Dict[str, Any]) -> str:
        """Route via voice orchestrator for standard voice handling."""
        try:
            from mycosoft_mas.core.routers.voice_orchestrator_api import (
                VoiceOrchestratorRequest,
                get_orchestrator,
            )
            orchestrator = get_orchestrator()
            request = VoiceOrchestratorRequest(
                message=transcript,
                conversation_id=context.get("conversation_id"),
                session_id=context.get("session_id"),
                user_id=context.get("user_id"),
                source=context.get("source", "voice-full-duplex"),
                modality="voice",
                want_audio=False,
            )
            response = await orchestrator.process(request)
            return response.response_text
        except Exception as e:
            logger.error(f"Voice orchestrator failed: {e}")
            return "Unable to process the voice request."
    
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
            "session_state": self.session_state.value,
            "queue_size": len(self.announcement_queue),
            "conversation_turns": len(self.conversation),
            "allow_interrupts": self.allow_interrupts,
            "running": self._running,
            "bridge_connected": bool(self._bridge_ws and not self._bridge_ws.closed),
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
    "VoiceSessionState",
    "AnnouncementPriority",
    "QueuedAnnouncement",
    "ConversationTurn",
    "get_full_duplex_voice",
]
