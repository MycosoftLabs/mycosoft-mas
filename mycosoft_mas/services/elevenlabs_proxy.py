"""
ElevenLabs TTS Proxy for Mycosoft MAS

This service provides an OpenAI-compatible TTS API wrapper around ElevenLabs,
with automatic fallback to local TTS when ElevenLabs is unavailable or unconfigured.
"""

import os
import httpx
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ElevenLabs TTS Proxy")

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "").strip()
FALLBACK_TTS_URL = os.getenv("FALLBACK_TTS_URL", "http://openedai-speech:8000")

# Voice mapping: OpenAI voice names -> ElevenLabs voice IDs
# Custom voice configured by user
VOICE_MAP = {
    "alloy": "aEO01A4wXwd1O8GPgGlF",  # User's custom voice (default)
    "echo": "aEO01A4wXwd1O8GPgGlF",   # User's custom voice
    "fable": "aEO01A4wXwd1O8GPgGlF",  # User's custom voice
    "onyx": "aEO01A4wXwd1O8GPgGlF",   # User's custom voice
    "nova": "aEO01A4wXwd1O8GPgGlF",   # User's custom voice
    "shimmer": "aEO01A4wXwd1O8GPgGlF",# User's custom voice
    "scarlett": "aEO01A4wXwd1O8GPgGlF",  # User's custom voice (Scarlett-style)
}


class TTSRequest(BaseModel):
    model: str = "tts-1"
    voice: str = "alloy"
    input: str
    response_format: str = "mp3"


@app.get("/v1/models")
async def list_models():
    """List available TTS models (OpenAI-compatible)."""
    return {
        "object": "list",
        "data": [
            {"id": "tts-1", "object": "model", "created": 0, "owned_by": "elevenlabs"},
            {"id": "tts-1-hd", "object": "model", "created": 0, "owned_by": "elevenlabs"},
        ],
    }


@app.post("/v1/audio/speech")
async def create_speech(request: TTSRequest):
    """
    Convert text to speech using ElevenLabs (with fallback to local TTS).
    OpenAI-compatible API.
    """
    if not request.input.strip():
        raise HTTPException(status_code=400, detail="Empty input text")

    # If ElevenLabs is configured, use it
    if ELEVENLABS_API_KEY:
        try:
            return await _elevenlabs_tts(request)
        except Exception as e:
            logger.warning(f"ElevenLabs TTS failed, falling back to local: {e}")

    # Fall back to local TTS
    return await _fallback_tts(request)


async def _elevenlabs_tts(request: TTSRequest) -> Response:
    """Call ElevenLabs API for premium TTS."""
    voice_id = VOICE_MAP.get(request.voice, VOICE_MAP["alloy"])

    # ElevenLabs API v1
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": request.input,
        "model_id": "eleven_monolingual_v1" if request.model == "tts-1" else "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
        },
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()

        # ElevenLabs returns audio/mpeg by default
        return Response(
            content=resp.content,
            media_type="audio/mpeg",
            headers={"X-TTS-Provider": "elevenlabs"},
        )


async def _fallback_tts(request: TTSRequest) -> Response:
    """Fall back to local openedai-speech."""
    url = f"{FALLBACK_TTS_URL}/v1/audio/speech"
    payload = {
        "model": request.model,
        "voice": request.voice if request.voice in ["alloy", "echo", "fable", "onyx", "nova", "shimmer"] else "alloy",
        "input": request.input,
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()

            return Response(
                content=resp.content,
                media_type="audio/mpeg",
                headers={"X-TTS-Provider": "openedai-speech"},
            )
    except Exception as e:
        logger.error(f"Fallback TTS also failed: {e}")
        # Return a minimal error response
        raise HTTPException(status_code=502, detail=f"Both ElevenLabs and fallback TTS failed: {e}")


@app.get("/health")
async def health():
    """Health check endpoint."""
    status = {"status": "ok", "provider": "elevenlabs" if ELEVENLABS_API_KEY else "local"}
    return status
