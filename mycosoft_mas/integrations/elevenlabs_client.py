"""
ElevenLabs Integration Client for MYCA Voice System
Created: March 3, 2026

Provides text-to-speech, streaming audio, voice cloning, and full-duplex
voice management via the ElevenLabs API. Default voice is Arabella with
fallback to PersonaPlex nat2f when the API key is unavailable.

Environment Variables:
    ELEVENLABS_API_KEY: API key from https://elevenlabs.io
    ELEVENLABS_VOICE_ID: Override default Arabella voice ID
    ELEVENLABS_MODEL_ID: Override default model (eleven_multilingual_v2)
    PERSONAPLEX_BRIDGE_URL: PersonaPlex fallback URL
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple
from uuid import uuid4

import httpx

logger = logging.getLogger(__name__)

ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"

# Arabella voice ID on ElevenLabs -- MYCA's primary voice
DEFAULT_VOICE_ID = "pFZP5JQG7iQjIQuC4Bku"  # Arabella
DEFAULT_MODEL_ID = "eleven_multilingual_v2"
DEFAULT_OUTPUT_FORMAT = "mp3_44100_128"

# PersonaPlex fallback voice prompt
PERSONAPLEX_FALLBACK_VOICE = "NATF2.pt"


class EmotionalState(Enum):
    """Emotional states that map to voice setting adjustments."""
    NEUTRAL = "neutral"
    WARM = "warm"
    URGENT = "urgent"
    CALM = "calm"
    EXCITED = "excited"
    EMPATHETIC = "empathetic"
    AUTHORITATIVE = "authoritative"
    PLAYFUL = "playful"


class DuplexSessionState(Enum):
    """State of a full-duplex voice session."""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    LISTENING = "listening"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"
    ENDED = "ended"


@dataclass
class VoiceSettings:
    """ElevenLabs voice generation settings."""
    stability: float = 0.5
    similarity_boost: float = 0.75
    style: float = 0.0
    use_speaker_boost: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stability": self.stability,
            "similarity_boost": self.similarity_boost,
            "style": self.style,
            "use_speaker_boost": self.use_speaker_boost,
        }


@dataclass
class ElevenLabsConfig:
    """Configuration for the ElevenLabs integration."""
    api_key: str = ""
    base_url: str = ELEVENLABS_BASE_URL
    voice_id: str = DEFAULT_VOICE_ID
    model_id: str = DEFAULT_MODEL_ID
    output_format: str = DEFAULT_OUTPUT_FORMAT
    settings: VoiceSettings = field(default_factory=VoiceSettings)
    timeout: float = 30.0
    stream_chunk_size: int = 4096

    @classmethod
    def from_env(cls) -> "ElevenLabsConfig":
        """Build config from environment variables."""
        return cls(
            api_key=os.getenv("ELEVENLABS_API_KEY", ""),
            voice_id=os.getenv("ELEVENLABS_VOICE_ID", DEFAULT_VOICE_ID),
            model_id=os.getenv("ELEVENLABS_MODEL_ID", DEFAULT_MODEL_ID),
        )


@dataclass
class DuplexSession:
    """Tracks a full-duplex voice conversation session."""
    session_id: str
    state: DuplexSessionState = DuplexSessionState.INITIALIZING
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    turns: List[Dict[str, Any]] = field(default_factory=list)
    barge_in_count: int = 0
    total_audio_bytes: int = 0
    current_emotion: EmotionalState = EmotionalState.NEUTRAL

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "state": self.state.value,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "turn_count": len(self.turns),
            "barge_in_count": self.barge_in_count,
            "total_audio_bytes": self.total_audio_bytes,
            "current_emotion": self.current_emotion.value,
        }


class ElevenLabsClient:
    """
    Async client for the ElevenLabs text-to-speech API.

    Provides TTS generation, streaming, voice listing, cloning, and
    subscription management. Falls back gracefully when no API key is set.
    """

    def __init__(self, config: Optional[ElevenLabsConfig] = None):
        self.config = config or ElevenLabsConfig.from_env()
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def is_configured(self) -> bool:
        return bool(self.config.api_key)

    def _headers(self) -> Dict[str, str]:
        return {
            "xi-api-key": self.config.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                headers=self._headers(),
                timeout=self.config.timeout,
            )
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def text_to_speech(
        self,
        text: str,
        voice_id: Optional[str] = None,
        model_id: Optional[str] = None,
        output_format: Optional[str] = None,
        voice_settings: Optional[VoiceSettings] = None,
    ) -> bytes:
        """
        Convert text to speech audio.

        Args:
            text: Text to synthesize (max 5000 characters).
            voice_id: ElevenLabs voice ID. Defaults to Arabella.
            model_id: Model to use. Defaults to eleven_multilingual_v2.
            output_format: Audio format string. Defaults to mp3_44100_128.
            voice_settings: Override stability/similarity settings.

        Returns:
            Raw audio bytes in the requested format.

        Raises:
            RuntimeError: If the API key is not configured.
            httpx.HTTPStatusError: On non-2xx responses.
        """
        if not self.is_configured:
            raise RuntimeError("ELEVENLABS_API_KEY is not set")

        vid = voice_id or self.config.voice_id
        mid = model_id or self.config.model_id
        fmt = output_format or self.config.output_format
        settings = voice_settings or self.config.settings

        client = await self._get_client()
        payload = {
            "text": text[:5000],
            "model_id": mid,
            "voice_settings": settings.to_dict(),
        }

        resp = await client.post(
            f"/text-to-speech/{vid}",
            json=payload,
            params={"output_format": fmt},
            headers={**self._headers(), "Accept": "audio/mpeg"},
        )
        resp.raise_for_status()
        logger.info("TTS generated: %d bytes for %d chars", len(resp.content), len(text))
        return resp.content

    async def text_to_speech_stream(
        self,
        text: str,
        voice_id: Optional[str] = None,
        model_id: Optional[str] = None,
        voice_settings: Optional[VoiceSettings] = None,
    ) -> AsyncIterator[bytes]:
        """
        Stream text-to-speech audio in chunks.

        Yields audio data as it becomes available from the API, enabling
        low-latency playback before the full response is ready.

        Args:
            text: Text to synthesize.
            voice_id: Override voice ID.
            model_id: Override model ID.
            voice_settings: Override voice settings.

        Yields:
            Chunks of raw audio bytes.
        """
        if not self.is_configured:
            raise RuntimeError("ELEVENLABS_API_KEY is not set")

        vid = voice_id or self.config.voice_id
        mid = model_id or self.config.model_id
        settings = voice_settings or self.config.settings

        client = await self._get_client()
        payload = {
            "text": text[:5000],
            "model_id": mid,
            "voice_settings": settings.to_dict(),
        }

        async with client.stream(
            "POST",
            f"/text-to-speech/{vid}/stream",
            json=payload,
            headers={**self._headers(), "Accept": "audio/mpeg"},
        ) as resp:
            resp.raise_for_status()
            async for chunk in resp.aiter_bytes(self.config.stream_chunk_size):
                yield chunk

    async def list_voices(self) -> List[Dict[str, Any]]:
        """
        List all voices available on the account.

        Returns:
            List of voice metadata dicts with keys like name, voice_id,
            category, labels, etc.
        """
        if not self.is_configured:
            logger.warning("ElevenLabs not configured; returning empty voice list")
            return []

        client = await self._get_client()
        resp = await client.get("/voices")
        resp.raise_for_status()
        data = resp.json()
        voices = data.get("voices", [])
        logger.info("Listed %d voices from ElevenLabs", len(voices))
        return voices

    async def get_voice(self, voice_id: str) -> Dict[str, Any]:
        """
        Get detailed metadata for a specific voice.

        Args:
            voice_id: The ElevenLabs voice ID.

        Returns:
            Dict containing voice name, labels, settings, samples, etc.
        """
        if not self.is_configured:
            raise RuntimeError("ELEVENLABS_API_KEY is not set")

        client = await self._get_client()
        resp = await client.get(f"/voices/{voice_id}")
        resp.raise_for_status()
        return resp.json()

    async def clone_voice(
        self,
        name: str,
        description: str,
        audio_files: List[Tuple[str, bytes]],
        labels: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Clone a voice from audio samples.

        Args:
            name: Display name for the cloned voice.
            description: Description of the voice.
            audio_files: List of (filename, audio_bytes) tuples. At least one
                         sample is required; ElevenLabs recommends 1-25 samples
                         of clean speech, each 30 seconds to 3 minutes.
            labels: Optional metadata labels (e.g. accent, gender).

        Returns:
            The voice_id of the newly cloned voice.
        """
        if not self.is_configured:
            raise RuntimeError("ELEVENLABS_API_KEY is not set")

        if not audio_files:
            raise ValueError("At least one audio file is required for voice cloning")

        client = await self._get_client()
        files = [
            ("files", (fname, fdata, "audio/mpeg"))
            for fname, fdata in audio_files
        ]
        data = {"name": name, "description": description}
        if labels:
            import json
            data["labels"] = json.dumps(labels)

        resp = await client.post(
            "/voices/add",
            data=data,
            files=files,
            headers={"xi-api-key": self.config.api_key},
        )
        resp.raise_for_status()
        voice_id = resp.json().get("voice_id", "")
        logger.info("Cloned voice '%s' -> %s", name, voice_id)
        return voice_id

    async def health_check(self) -> bool:
        """
        Verify connectivity and API key validity.

        Returns:
            True if the ElevenLabs API is reachable and the key is valid.
        """
        if not self.is_configured:
            return False
        try:
            client = await self._get_client()
            resp = await client.get("/user")
            return resp.status_code == 200
        except Exception as exc:
            logger.warning("ElevenLabs health check failed: %s", exc)
            return False

    async def get_subscription_info(self) -> Dict[str, Any]:
        """
        Retrieve subscription usage and limits.

        Returns:
            Dict with character_count, character_limit, tier, next_reset, etc.
        """
        if not self.is_configured:
            return {"status": "not_configured"}

        client = await self._get_client()
        resp = await client.get("/user/subscription")
        resp.raise_for_status()
        info = resp.json()
        logger.info(
            "ElevenLabs subscription: %s/%s characters used",
            info.get("character_count", "?"),
            info.get("character_limit", "?"),
        )
        return info


class FullDuplexVoiceManager:
    """
    Manages full-duplex voice sessions for MYCA.

    Full duplex means MYCA can listen while talking. This manager coordinates
    barge-in detection, session lifecycle, and audio chunk routing between
    the ElevenLabs TTS backend and the caller.
    """

    def __init__(
        self,
        elevenlabs: Optional[ElevenLabsClient] = None,
        persona: Optional["MycaVoicePersona"] = None,
    ):
        self._elevenlabs = elevenlabs or ElevenLabsClient()
        self._persona = persona
        self._sessions: Dict[str, DuplexSession] = {}
        self._speaking_tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    @property
    def active_session_count(self) -> int:
        return sum(
            1 for s in self._sessions.values()
            if s.state not in (DuplexSessionState.ENDED,)
        )

    async def start_session(self) -> str:
        """
        Start a new full-duplex voice session.

        Returns:
            The unique session_id.
        """
        session_id = str(uuid4())
        session = DuplexSession(session_id=session_id)
        session.state = DuplexSessionState.ACTIVE
        async with self._lock:
            self._sessions[session_id] = session
        logger.info("Full-duplex session started: %s", session_id)
        return session_id

    async def process_audio_chunk(
        self,
        session_id: str,
        audio_data: bytes,
    ) -> Optional[bytes]:
        """
        Process an incoming audio chunk from the user.

        Handles barge-in detection: if the user speaks while MYCA is talking,
        the current TTS playback is cancelled and the session transitions to
        the INTERRUPTED state.

        Args:
            session_id: Active session ID.
            audio_data: Raw audio bytes from the user's microphone.

        Returns:
            Optional response audio bytes if a reply is ready, otherwise None.
        """
        session = self._sessions.get(session_id)
        if session is None or session.state == DuplexSessionState.ENDED:
            logger.warning("Audio chunk for unknown/ended session: %s", session_id)
            return None

        session.last_activity = datetime.utcnow()
        session.total_audio_bytes += len(audio_data)

        # Detect barge-in: user audio arriving while MYCA is speaking
        if session.state == DuplexSessionState.SPEAKING:
            if self._detect_speech_energy(audio_data):
                await self._handle_barge_in(session_id)
                return None

        # In a production system, audio_data would be forwarded to a
        # speech-to-text service, then the transcript routed through the
        # orchestrator. Return None here; responses are pushed via
        # speak_in_session().
        session.state = DuplexSessionState.LISTENING
        return None

    async def speak_in_session(
        self,
        session_id: str,
        text: str,
        emotion: Optional[EmotionalState] = None,
    ) -> Optional[bytes]:
        """
        Generate and return TTS audio for a session response.

        Args:
            session_id: Active session ID.
            text: Text for MYCA to speak.
            emotion: Optional emotional tone for voice adjustment.

        Returns:
            Audio bytes, or None if generation fails.
        """
        session = self._sessions.get(session_id)
        if session is None or session.state == DuplexSessionState.ENDED:
            return None

        session.state = DuplexSessionState.SPEAKING

        # Resolve voice settings from persona emotion mapping
        voice_settings = None
        if self._persona and emotion:
            voice_settings = self._persona.get_voice_settings(emotion)
            session.current_emotion = emotion

        try:
            audio = await self._elevenlabs.text_to_speech(
                text=text,
                voice_settings=voice_settings,
            )
            session.turns.append({
                "role": "assistant",
                "text": text,
                "emotion": (emotion or session.current_emotion).value,
                "timestamp": datetime.utcnow().isoformat(),
                "audio_bytes": len(audio),
            })
            return audio
        except Exception as exc:
            logger.error("TTS failed in session %s: %s", session_id, exc)
            session.state = DuplexSessionState.ACTIVE
            return None

    async def end_session(self, session_id: str) -> None:
        """
        End a full-duplex session and clean up resources.

        Args:
            session_id: The session to end.
        """
        session = self._sessions.get(session_id)
        if session is None:
            return

        # Cancel any in-progress speaking task
        task = self._speaking_tasks.pop(session_id, None)
        if task and not task.done():
            task.cancel()

        session.state = DuplexSessionState.ENDED
        logger.info(
            "Full-duplex session ended: %s (%d turns, %d barge-ins)",
            session_id,
            len(session.turns),
            session.barge_in_count,
        )

    async def _handle_barge_in(self, session_id: str) -> None:
        """Handle user interruption during MYCA speech."""
        session = self._sessions.get(session_id)
        if session is None:
            return

        session.state = DuplexSessionState.INTERRUPTED
        session.barge_in_count += 1

        # Cancel the current speaking task so playback stops immediately
        task = self._speaking_tasks.pop(session_id, None)
        if task and not task.done():
            task.cancel()

        logger.info("Barge-in detected in session %s (count: %d)", session_id, session.barge_in_count)

        # Transition back to listening so the user's input is captured
        session.state = DuplexSessionState.LISTENING

    @staticmethod
    def _detect_speech_energy(audio_data: bytes, threshold: int = 500) -> bool:
        """
        Simple energy-based voice activity detection on raw PCM-like data.

        This is a lightweight heuristic. In production, a proper VAD model
        (e.g. Silero VAD or the VoiceActivityDetector from consciousness
        module) should be used instead.

        Args:
            audio_data: Raw audio bytes.
            threshold: Minimum average absolute amplitude to count as speech.

        Returns:
            True if the chunk likely contains speech.
        """
        if len(audio_data) < 2:
            return False
        # Treat as 16-bit signed PCM samples
        total = 0
        sample_count = len(audio_data) // 2
        if sample_count == 0:
            return False
        for i in range(0, len(audio_data) - 1, 2):
            sample = int.from_bytes(audio_data[i:i + 2], byteorder="little", signed=True)
            total += abs(sample)
        avg_energy = total / sample_count
        return avg_energy > threshold

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Return session info dict, or None if not found."""
        session = self._sessions.get(session_id)
        return session.to_dict() if session else None

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate stats across all sessions."""
        active = [s for s in self._sessions.values() if s.state != DuplexSessionState.ENDED]
        return {
            "active_sessions": len(active),
            "total_sessions": len(self._sessions),
            "total_barge_ins": sum(s.barge_in_count for s in self._sessions.values()),
        }


# ---------------------------------------------------------------------------
# Voice emotion -> ElevenLabs settings mapping
# ---------------------------------------------------------------------------

EMOTION_VOICE_MAP: Dict[EmotionalState, VoiceSettings] = {
    EmotionalState.NEUTRAL: VoiceSettings(
        stability=0.50, similarity_boost=0.75, style=0.0,
    ),
    EmotionalState.WARM: VoiceSettings(
        stability=0.45, similarity_boost=0.80, style=0.15,
    ),
    EmotionalState.URGENT: VoiceSettings(
        stability=0.65, similarity_boost=0.70, style=0.30,
    ),
    EmotionalState.CALM: VoiceSettings(
        stability=0.70, similarity_boost=0.75, style=0.0,
    ),
    EmotionalState.EXCITED: VoiceSettings(
        stability=0.35, similarity_boost=0.80, style=0.40,
    ),
    EmotionalState.EMPATHETIC: VoiceSettings(
        stability=0.50, similarity_boost=0.85, style=0.10,
    ),
    EmotionalState.AUTHORITATIVE: VoiceSettings(
        stability=0.70, similarity_boost=0.70, style=0.20,
    ),
    EmotionalState.PLAYFUL: VoiceSettings(
        stability=0.30, similarity_boost=0.80, style=0.45,
    ),
}


class MycaVoicePersona:
    """
    Manages MYCA's voice identity across providers.

    Primary voice: Arabella on ElevenLabs
    Fallback voice: nat2f (NATF2.pt) on PersonaPlex/Moshi

    The persona dynamically adjusts voice parameters based on conversational
    context and emotional state, ensuring MYCA always sounds natural and
    contextually appropriate.
    """

    def __init__(
        self,
        elevenlabs: Optional[ElevenLabsClient] = None,
        personaplex_url: Optional[str] = None,
    ):
        self._elevenlabs = elevenlabs or ElevenLabsClient()
        self._personaplex_url = personaplex_url or os.getenv(
            "PERSONAPLEX_BRIDGE_URL", "ws://localhost:8999"
        )
        self._current_emotion = EmotionalState.NEUTRAL
        self._emotion_history: List[Dict[str, Any]] = []

    @property
    def primary_available(self) -> bool:
        """Whether the ElevenLabs (Arabella) voice is available."""
        return self._elevenlabs.is_configured

    @property
    def current_emotion(self) -> EmotionalState:
        return self._current_emotion

    def get_voice_settings(self, emotion: EmotionalState) -> VoiceSettings:
        """
        Map an emotional state to ElevenLabs voice settings.

        Args:
            emotion: The desired emotional tone.

        Returns:
            VoiceSettings tuned for the given emotion.
        """
        return EMOTION_VOICE_MAP.get(emotion, EMOTION_VOICE_MAP[EmotionalState.NEUTRAL])

    def set_emotion(self, emotion: EmotionalState, reason: str = "") -> None:
        """
        Update MYCA's current emotional state.

        Args:
            emotion: New emotional state.
            reason: Why the emotion changed (for logging/debugging).
        """
        prev = self._current_emotion
        self._current_emotion = emotion
        entry = {
            "from": prev.value,
            "to": emotion.value,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._emotion_history.append(entry)
        # Keep only the last 50 transitions
        if len(self._emotion_history) > 50:
            self._emotion_history = self._emotion_history[-50:]
        logger.info("MYCA emotion: %s -> %s (%s)", prev.value, emotion.value, reason)

    async def synthesize(
        self,
        text: str,
        emotion: Optional[EmotionalState] = None,
    ) -> Tuple[bytes, str]:
        """
        Synthesize speech using the best available provider.

        Tries ElevenLabs (Arabella) first, then falls back to PersonaPlex
        (nat2f) if the primary provider is unavailable.

        Args:
            text: Text to speak.
            emotion: Optional emotional tone override.

        Returns:
            Tuple of (audio_bytes, provider_name).
        """
        target_emotion = emotion or self._current_emotion
        if emotion:
            self.set_emotion(emotion, reason="explicit synthesis request")

        # Try ElevenLabs first
        if self._elevenlabs.is_configured:
            try:
                settings = self.get_voice_settings(target_emotion)
                audio = await self._elevenlabs.text_to_speech(
                    text=text,
                    voice_settings=settings,
                )
                return audio, "elevenlabs_arabella"
            except Exception as exc:
                logger.warning("ElevenLabs TTS failed, falling back: %s", exc)

        # Fallback to PersonaPlex nat2f
        audio = await self._personaplex_tts_fallback(text)
        return audio, "personaplex_nat2f"

    async def _personaplex_tts_fallback(self, text: str) -> bytes:
        """
        Fallback TTS via PersonaPlex HTTP endpoint.

        Sends the text to the PersonaPlex Moshi TTS service and returns
        the synthesized audio bytes.
        """
        http_url = self._personaplex_url.replace("ws://", "http://").replace("wss://", "https://")
        tts_url = f"{http_url}/api/tts"

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    tts_url,
                    json={
                        "text": text,
                        "voice_prompt": PERSONAPLEX_FALLBACK_VOICE,
                    },
                )
                resp.raise_for_status()
                return resp.content
        except Exception as exc:
            logger.error("PersonaPlex TTS fallback failed: %s", exc)
            return b""

    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of all voice providers.

        Returns:
            Dict with provider statuses and current persona info.
        """
        el_healthy = await self._elevenlabs.health_check()

        pp_healthy = False
        try:
            http_url = self._personaplex_url.replace("ws://", "http://").replace("wss://", "https://")
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{http_url}/health")
                pp_healthy = resp.status_code == 200
        except Exception:
            pass

        return {
            "elevenlabs": {
                "healthy": el_healthy,
                "voice": "Arabella",
                "voice_id": self._elevenlabs.config.voice_id,
            },
            "personaplex": {
                "healthy": pp_healthy,
                "voice": "nat2f",
                "voice_prompt": PERSONAPLEX_FALLBACK_VOICE,
            },
            "active_provider": "elevenlabs" if el_healthy else ("personaplex" if pp_healthy else "none"),
            "current_emotion": self._current_emotion.value,
        }

    def get_emotion_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return recent emotion transitions."""
        return self._emotion_history[-limit:]


# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

_client_instance: Optional[ElevenLabsClient] = None
_persona_instance: Optional[MycaVoicePersona] = None
_duplex_manager_instance: Optional[FullDuplexVoiceManager] = None


def get_elevenlabs_client() -> ElevenLabsClient:
    """Get or create the singleton ElevenLabsClient."""
    global _client_instance
    if _client_instance is None:
        _client_instance = ElevenLabsClient()
    return _client_instance


def get_myca_voice_persona() -> MycaVoicePersona:
    """Get or create the singleton MycaVoicePersona."""
    global _persona_instance
    if _persona_instance is None:
        _persona_instance = MycaVoicePersona(elevenlabs=get_elevenlabs_client())
    return _persona_instance


def get_duplex_voice_manager() -> FullDuplexVoiceManager:
    """Get or create the singleton FullDuplexVoiceManager."""
    global _duplex_manager_instance
    if _duplex_manager_instance is None:
        _duplex_manager_instance = FullDuplexVoiceManager(
            elevenlabs=get_elevenlabs_client(),
            persona=get_myca_voice_persona(),
        )
    return _duplex_manager_instance


__all__ = [
    "ElevenLabsConfig",
    "ElevenLabsClient",
    "FullDuplexVoiceManager",
    "MycaVoicePersona",
    "VoiceSettings",
    "EmotionalState",
    "DuplexSessionState",
    "DuplexSession",
    "EMOTION_VOICE_MAP",
    "get_elevenlabs_client",
    "get_myca_voice_persona",
    "get_duplex_voice_manager",
]
