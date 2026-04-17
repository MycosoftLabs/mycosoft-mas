"""PersonaPlex bridge — voice embeddings, ASR/TTS via HTTP gateway."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator
from typing import Any

import httpx

from mycosoft_mas.harness.config import HarnessConfig

logger = logging.getLogger(__name__)

# NATF0 … VARM4 — symbolic persona slots (see PersonaPlex docs)
VOICE_EMBEDDINGS = ("NATF0", "NATF1", "VARM0", "VARM1", "VARM2", "VARM3", "VARM4")


class PersonaPlexInterface:
    """HTTP façade over the PersonaPlex bridge for ASR/TTS."""

    def __init__(self, config: HarnessConfig, persona_id: str = "NATF0") -> None:
        self._base = config.personaplex_bridge_url
        self._persona_id = persona_id if persona_id in VOICE_EMBEDDINGS else "NATF0"

    async def transcribe_stream(
        self,
        audio_stream: AsyncIterator[bytes],
        *,
        language: str = "en",
    ) -> AsyncIterator[str]:
        """Streaming ASR — push audio chunks, yield partial transcripts."""
        # Bridge API varies by deployment; this pattern posts chunks to /asr/stream if present
        async for chunk in audio_stream:
            if not chunk:
                continue
            url = f"{self._base}/transcribe"
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    r = await client.post(
                        url,
                        content=chunk,
                        headers={
                            "Content-Type": "application/octet-stream",
                            "X-Persona": self._persona_id,
                            "Accept": "text/plain",
                        },
                    )
                    if r.is_success and r.text:
                        yield r.text.strip()
            except Exception as e:
                logger.warning("personaplex transcribe chunk failed: %s", e)

    async def transcribe(self, audio: bytes) -> str:
        """Single-shot ASR over full buffer."""
        url = f"{self._base}/transcribe"
        async with httpx.AsyncClient(timeout=45.0) as client:
            r = await client.post(
                url,
                content=audio,
                headers={
                    "Content-Type": "application/octet-stream",
                    "X-Persona": self._persona_id,
                },
            )
            if r.status_code >= 400:
                return ""
            return (r.text or "").strip()

    async def speak(self, text: str) -> bytes:
        """TTS — returns audio bytes (PCM or container per bridge)."""
        url = f"{self._base}/tts"
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                url,
                json={"text": text, "persona": self._persona_id},
                headers={"Content-Type": "application/json"},
            )
            r.raise_for_status()
            return r.content

    def interrupt_token(self) -> str:
        """Correlation token for Nemotron cancellation + barge-in coordination."""
        return str(uuid.uuid4())


class FullDuplexVoiceSession:
    """Coordinates listen + speak; use separate tasks for full-duplex."""

    def __init__(self, iface: PersonaPlexInterface) -> None:
        self._iface = iface
        self._speak_lock = asyncio.Lock()

    async def speak_while_listening(self, text: str, listen: AsyncIterator[bytes]) -> None:
        async with self._speak_lock:
            audio = await self._iface.speak(text)
            # Caller would play audio; concurrently forward `listen` to transcribe_stream
            _ = audio
        async for _chunk in listen:
            pass


def persona_plex_from_env() -> PersonaPlexInterface:
    return PersonaPlexInterface(HarnessConfig.from_env())
