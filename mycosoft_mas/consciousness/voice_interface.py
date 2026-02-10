"""
MYCA Voice Interface

Full-duplex voice integration through PersonaPlex.
Voice and text go through the same consciousness pipeline.

This enables:
- Voice input processed identically to text
- Voice output through PersonaPlex TTS
- MYCA-initiated voice (outbound calls)
- Full agent/tool access from voice commands

Author: Morgan Rockwell / MYCA
Created: February 10, 2026
"""

import asyncio
import logging
import httpx
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, AsyncGenerator, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

if TYPE_CHECKING:
    from mycosoft_mas.consciousness.core import MYCAConsciousness

logger = logging.getLogger(__name__)


class VoiceState(Enum):
    """Current state of the voice system."""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    FULL_DUPLEX = "full_duplex"  # Simultaneous listen/speak


class VoiceMode(Enum):
    """Voice interaction mode."""
    PUSH_TO_TALK = "push_to_talk"
    VOICE_ACTIVITY = "voice_activity"
    FULL_DUPLEX = "full_duplex"
    MUTED = "muted"


@dataclass
class VoiceSession:
    """A voice conversation session."""
    id: str
    user_id: str
    started_at: datetime
    mode: VoiceMode = VoiceMode.FULL_DUPLEX
    is_active: bool = True
    personaplex_connected: bool = False
    last_user_speech: Optional[datetime] = None
    last_myca_speech: Optional[datetime] = None
    transcripts: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class VoiceMessage:
    """A voice message (input or output)."""
    id: str
    direction: str  # "inbound" or "outbound"
    text: str
    timestamp: datetime
    audio_path: Optional[str] = None
    duration_ms: Optional[int] = None


class VoiceInterface:
    """
    MYCA's voice interface.
    
    Integrates with PersonaPlex for full-duplex voice conversations.
    Voice input goes through the same consciousness pipeline as text.
    """
    
    # PersonaPlex endpoints
    PERSONAPLEX_API = "http://localhost:8998"  # Local GPU service
    PERSONAPLEX_BRIDGE = "http://localhost:8999"  # Bridge service
    MAS_VOICE_API = "http://192.168.0.188:8001/api/voice"  # MAS voice endpoints
    
    def __init__(self, consciousness: "MYCAConsciousness"):
        self._consciousness = consciousness
        self._http_client: Optional[httpx.AsyncClient] = None
        
        # State
        self._state = VoiceState.IDLE
        self._active_sessions: Dict[str, VoiceSession] = {}
        self._current_session_id: Optional[str] = None
        
        # PersonaPlex connection
        self._personaplex_available = False
        self._tts_voice = "en_GB-northern_english_male-medium"
        
        # Callbacks for UI integration
        self._on_state_change: Optional[Callable] = None
        self._on_transcript: Optional[Callable] = None
        self._on_myca_speaking: Optional[Callable] = None
        
        # Queue for outbound speech (MYCA-initiated)
        self._outbound_queue: asyncio.Queue = asyncio.Queue()
    
    async def initialize(self) -> bool:
        """Initialize the voice interface and check PersonaPlex availability."""
        self._http_client = httpx.AsyncClient(timeout=30.0)
        
        # Check PersonaPlex
        await self._check_personaplex()
        
        if self._personaplex_available:
            logger.info("Voice interface initialized with PersonaPlex")
        else:
            logger.warning("Voice interface initialized without PersonaPlex (text-only mode)")
        
        return self._personaplex_available
    
    async def _check_personaplex(self) -> None:
        """Check if PersonaPlex is available."""
        try:
            if self._http_client:
                response = await self._http_client.get(
                    f"{self.PERSONAPLEX_API}/health",
                    timeout=5.0
                )
                self._personaplex_available = response.status_code == 200
                logger.info(f"PersonaPlex health check: {response.status_code}")
        except Exception as e:
            logger.debug(f"PersonaPlex not available: {e}")
            self._personaplex_available = False
    
    @property
    def state(self) -> VoiceState:
        """Get current voice state."""
        return self._state
    
    @property
    def is_available(self) -> bool:
        """Check if voice is available."""
        return self._personaplex_available
    
    @property
    def current_session(self) -> Optional[VoiceSession]:
        """Get the current voice session."""
        if self._current_session_id:
            return self._active_sessions.get(self._current_session_id)
        return None
    
    async def start_session(
        self,
        user_id: str,
        mode: VoiceMode = VoiceMode.FULL_DUPLEX
    ) -> VoiceSession:
        """Start a new voice session."""
        session_id = f"voice_{datetime.now(timezone.utc).timestamp()}"
        
        session = VoiceSession(
            id=session_id,
            user_id=user_id,
            started_at=datetime.now(timezone.utc),
            mode=mode,
            personaplex_connected=self._personaplex_available
        )
        
        self._active_sessions[session_id] = session
        self._current_session_id = session_id
        
        # Connect to PersonaPlex if available
        if self._personaplex_available:
            await self._connect_personaplex(session)
        
        self._state = VoiceState.LISTENING if mode != VoiceMode.MUTED else VoiceState.IDLE
        
        logger.info(f"Voice session started: {session_id} for user {user_id}")
        return session
    
    async def end_session(self, session_id: Optional[str] = None) -> None:
        """End a voice session."""
        sid = session_id or self._current_session_id
        if sid and sid in self._active_sessions:
            session = self._active_sessions[sid]
            session.is_active = False
            
            # Disconnect from PersonaPlex
            if session.personaplex_connected:
                await self._disconnect_personaplex(session)
            
            if sid == self._current_session_id:
                self._current_session_id = None
            
            del self._active_sessions[sid]
            self._state = VoiceState.IDLE
            
            logger.info(f"Voice session ended: {sid}")
    
    async def _connect_personaplex(self, session: VoiceSession) -> None:
        """Connect to PersonaPlex for a session."""
        try:
            if self._http_client:
                response = await self._http_client.post(
                    f"{self.PERSONAPLEX_BRIDGE}/session/start",
                    json={
                        "session_id": session.id,
                        "user_id": session.user_id,
                        "mode": session.mode.value,
                        "voice": self._tts_voice,
                    }
                )
                if response.status_code == 200:
                    session.personaplex_connected = True
                    logger.info(f"PersonaPlex connected for session {session.id}")
        except Exception as e:
            logger.warning(f"Could not connect PersonaPlex: {e}")
    
    async def _disconnect_personaplex(self, session: VoiceSession) -> None:
        """Disconnect from PersonaPlex."""
        try:
            if self._http_client:
                await self._http_client.post(
                    f"{self.PERSONAPLEX_BRIDGE}/session/end",
                    json={"session_id": session.id}
                )
        except Exception as e:
            logger.debug(f"PersonaPlex disconnect error: {e}")
    
    async def process_voice_input(
        self,
        audio_data: Optional[bytes] = None,
        transcript: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Process voice input through the consciousness pipeline.
        
        Voice input is processed identically to text - it goes through
        the same attention, working memory, and deliberation systems.
        
        Args:
            audio_data: Raw audio bytes (if doing local transcription)
            transcript: Pre-transcribed text (if using external STT)
            user_id: User identifier
            session_id: Voice session identifier
        
        Yields:
            Response chunks for streaming
        """
        self._state = VoiceState.PROCESSING
        
        # Get or use transcript
        text = transcript
        if not text and audio_data:
            text = await self._transcribe(audio_data)
        
        if not text:
            self._state = VoiceState.LISTENING
            yield "I didn't catch that. Could you repeat?"
            return
        
        # Record the input
        session = self._active_sessions.get(session_id or self._current_session_id or "")
        if session:
            session.last_user_speech = datetime.now(timezone.utc)
            session.transcripts.append({
                "role": "user",
                "content": text,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        
        # Log for callback
        if self._on_transcript:
            self._on_transcript("user", text)
        
        # Process through consciousness - same path as text!
        response_chunks = []
        async for chunk in self._consciousness.process_input(
            content=text,
            source="voice",  # Flag that this came from voice
            session_id=session_id,
            user_id=user_id
        ):
            response_chunks.append(chunk)
            yield chunk
        
        full_response = "".join(response_chunks)
        
        # Record MYCA's response
        if session:
            session.last_myca_speech = datetime.now(timezone.utc)
            session.transcripts.append({
                "role": "assistant",
                "content": full_response,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        
        self._state = VoiceState.LISTENING
    
    async def _transcribe(self, audio_data: bytes) -> Optional[str]:
        """Transcribe audio to text using Whisper or PersonaPlex."""
        try:
            if self._http_client and self._personaplex_available:
                # Use PersonaPlex's built-in Whisper
                response = await self._http_client.post(
                    f"{self.PERSONAPLEX_API}/transcribe",
                    content=audio_data,
                    headers={"Content-Type": "audio/wav"}
                )
                if response.status_code == 200:
                    result = response.json()
                    return result.get("text")
        except Exception as e:
            logger.warning(f"Transcription failed: {e}")
        return None
    
    async def speak(self, text: str, interrupt: bool = False) -> None:
        """
        MYCA speaks through PersonaPlex.
        
        Args:
            text: What to say
            interrupt: Whether to interrupt current speech
        """
        if not text.strip():
            return
        
        self._state = VoiceState.SPEAKING
        
        if self._on_myca_speaking:
            self._on_myca_speaking(text)
        
        if self._personaplex_available:
            try:
                if self._http_client:
                    await self._http_client.post(
                        f"{self.PERSONAPLEX_BRIDGE}/speak",
                        json={
                            "text": text,
                            "interrupt": interrupt,
                            "voice": self._tts_voice,
                            "session_id": self._current_session_id
                        }
                    )
            except Exception as e:
                logger.warning(f"PersonaPlex speak failed: {e}")
        else:
            # Log that we would speak
            logger.info(f"MYCA would say: {text[:100]}...")
        
        # After speaking, return to listening
        if self.current_session:
            self._state = VoiceState.LISTENING
        else:
            self._state = VoiceState.IDLE
    
    async def speak_stream(
        self,
        text_generator: AsyncGenerator[str, None]
    ) -> None:
        """
        Stream speech as text is generated.
        
        Args:
            text_generator: Async generator yielding text chunks
        """
        self._state = VoiceState.SPEAKING
        
        buffer = ""
        sentence_endings = ".!?"
        
        async for chunk in text_generator:
            buffer += chunk
            
            # Check for sentence boundary
            for i, char in enumerate(buffer):
                if char in sentence_endings and i < len(buffer) - 1:
                    sentence = buffer[:i+1].strip()
                    if sentence:
                        await self.speak(sentence)
                    buffer = buffer[i+1:]
                    break
        
        # Speak any remaining text
        if buffer.strip():
            await self.speak(buffer.strip())
        
        self._state = VoiceState.LISTENING if self.current_session else VoiceState.IDLE
    
    async def initiate_call(
        self,
        user_id: str,
        message: str,
        priority: str = "normal"
    ) -> bool:
        """
        MYCA initiates a voice call to a user.
        
        This enables MYCA to proactively reach out with alerts,
        updates, or ideas.
        
        Args:
            user_id: Who to call
            message: What to say
            priority: "low", "normal", "high", "urgent"
        
        Returns:
            Whether the call was initiated
        """
        logger.info(f"MYCA initiating call to {user_id}: {message[:50]}...")
        
        # For now, queue the message
        await self._outbound_queue.put({
            "user_id": user_id,
            "message": message,
            "priority": priority,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # If PersonaPlex available, try to initiate
        if self._personaplex_available:
            try:
                if self._http_client:
                    response = await self._http_client.post(
                        f"{self.PERSONAPLEX_BRIDGE}/call/initiate",
                        json={
                            "user_id": user_id,
                            "message": message,
                            "priority": priority
                        }
                    )
                    return response.status_code == 200
            except Exception as e:
                logger.warning(f"Could not initiate call: {e}")
        
        return False
    
    async def alert_morgan(self, message: str, priority: str = "normal") -> bool:
        """
        Special shortcut to alert Morgan specifically.
        
        Args:
            message: What to tell Morgan
            priority: "low", "normal", "high", "urgent"
        
        Returns:
            Whether the alert was sent
        """
        return await self.initiate_call(
            user_id="morgan",
            message=message,
            priority=priority
        )
    
    async def get_pending_outbound(self) -> List[Dict[str, Any]]:
        """Get pending outbound messages."""
        messages = []
        while not self._outbound_queue.empty():
            try:
                msg = self._outbound_queue.get_nowait()
                messages.append(msg)
            except asyncio.QueueEmpty:
                break
        return messages
    
    def set_voice(self, voice_id: str) -> None:
        """Set the TTS voice for PersonaPlex."""
        self._tts_voice = voice_id
    
    def set_callbacks(
        self,
        on_state_change: Optional[Callable] = None,
        on_transcript: Optional[Callable] = None,
        on_myca_speaking: Optional[Callable] = None
    ) -> None:
        """Set callbacks for UI integration."""
        if on_state_change:
            self._on_state_change = on_state_change
        if on_transcript:
            self._on_transcript = on_transcript
        if on_myca_speaking:
            self._on_myca_speaking = on_myca_speaking
    
    async def cleanup(self) -> None:
        """Cleanup voice interface resources."""
        # End all sessions
        for session_id in list(self._active_sessions.keys()):
            await self.end_session(session_id)
        
        # Close HTTP client
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert voice interface state to dictionary."""
        return {
            "state": self._state.value,
            "personaplex_available": self._personaplex_available,
            "active_sessions": len(self._active_sessions),
            "current_session_id": self._current_session_id,
            "tts_voice": self._tts_voice,
            "pending_outbound": self._outbound_queue.qsize(),
        }
