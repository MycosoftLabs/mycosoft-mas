"""
ElevenLabs TTS Proxy for Mycosoft MAS

This service provides an OpenAI-compatible TTS API wrapper around ElevenLabs,
with automatic fallback to local TTS when ElevenLabs is unavailable or unconfigured.

Enhanced for natural, conversational speech with proper text preprocessing.
"""

import os
import re
import httpx
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ElevenLabs TTS Proxy - MYCA Voice")

# Add CORS middleware for browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "").strip()
FALLBACK_TTS_URL = os.getenv("FALLBACK_TTS_URL", "http://openedai-speech:8000")

# MYCA/Arabella voice ID - Anabella voice from ElevenLabs
# MYCA is pronounced "My-Kah" (like the name Micah but spelled MYCA)
MYCA_VOICE_ID = "aEO01A4wXwd1O8GPgGlF"  # Anabella - MYCA's official voice (never change this)

# Model selection: Use multilingual_v2 for best quality natural speech
# Options: eleven_multilingual_v2 (best quality), eleven_turbo_v2_5 (fast+good), eleven_flash_v2_5 (fastest)
DEFAULT_MODEL = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")

# Voice mapping
VOICE_MAP = {
    "myca": MYCA_VOICE_ID,
    "arabella": MYCA_VOICE_ID,
    "alloy": MYCA_VOICE_ID,
    "echo": MYCA_VOICE_ID,
    "fable": MYCA_VOICE_ID,
    "onyx": MYCA_VOICE_ID,
    "nova": MYCA_VOICE_ID,
    "shimmer": MYCA_VOICE_ID,
    "scarlett": MYCA_VOICE_ID,
}


def clean_text_for_speech(text: str) -> str:
    """
    Clean and prepare text for natural TTS output.
    Removes markdown, special characters, and formats for conversational delivery.
    """
    if not text:
        return ""
    
    # Store original for logging
    original = text[:100] + "..." if len(text) > 100 else text
    
    # Remove markdown bold/italic markers (**, *, __, _)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **bold**
    text = re.sub(r'\*([^*]+)\*', r'\1', text)       # *italic*
    text = re.sub(r'__([^_]+)__', r'\1', text)       # __bold__
    text = re.sub(r'_([^_]+)_', r'\1', text)         # _italic_
    
    # Remove markdown headers
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    
    # Remove markdown links [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    
    # Remove markdown code blocks and inline code
    text = re.sub(r'```[^`]*```', '', text, flags=re.DOTALL)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    
    # Remove bullet points and list markers
    text = re.sub(r'^[\s]*[-*•]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[\s]*\d+\.\s+', '', text, flags=re.MULTILINE)
    
    # Remove standalone asterisks and other noise
    text = re.sub(r'\s*\*+\s*', ' ', text)
    text = re.sub(r'\s*_+\s*', ' ', text)
    
    # Clean up special characters that don't speak well
    text = text.replace('→', 'to')
    text = text.replace('←', 'from')
    text = text.replace('•', ',')
    text = text.replace('…', '...')
    text = text.replace('—', ', ')
    text = text.replace('–', ', ')
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace(''', "'").replace(''', "'")
    
    # Expand common abbreviations for natural speech
    abbreviations = {
        'VM': 'V M',
        'VMs': 'V Ms',
        'API': 'A P I',
        'APIs': 'A P Is',
        'CPU': 'C P U',
        'GPU': 'G P U',
        'RAM': 'ram',
        'NAS': 'nas',
        'URL': 'U R L',
        'HTTP': 'H T T P',
        'HTTPS': 'H T T P S',
        'JSON': 'jason',
        'SQL': 'sequel',
        'SSH': 'S S H',
        'ID': 'I D',
        'IDs': 'I Ds',
        'LLM': 'L L M',
        'AI': 'A I',
        'MAS': 'M A S',
        'MYCA': 'My-Kah',
        'TTS': 'T T S',
        'STT': 'S T T',
        'n8n': 'n 8 n',
        'OK': 'okay',
        'ok': 'okay',
    }
    
    for abbr, expansion in abbreviations.items():
        # Only replace whole words
        text = re.sub(rf'\b{abbr}\b', expansion, text)
    
    # Convert numbers with units for natural reading
    text = re.sub(r'(\d+)%', r'\1 percent', text)
    text = re.sub(r'(\d+)GB', r'\1 gigabytes', text)
    text = re.sub(r'(\d+)MB', r'\1 megabytes', text)
    text = re.sub(r'(\d+)KB', r'\1 kilobytes', text)
    text = re.sub(r'(\d+)ms', r'\1 milliseconds', text)
    
    # Add natural pauses after colons (for lists)
    text = re.sub(r':\s*\n', '. ', text)
    text = re.sub(r':\s+', ', ', text)
    
    # Clean up multiple spaces and newlines
    text = re.sub(r'\n+', '. ', text)
    text = re.sub(r'\s+', ' ', text)
    
    # Clean up multiple periods
    text = re.sub(r'\.{2,}', '.', text)
    text = re.sub(r'\.\s*\.', '.', text)
    
    # Ensure sentences end properly for natural pauses
    text = re.sub(r'([.!?])\s*([A-Z])', r'\1 \2', text)
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    # Ensure text ends with punctuation for proper cadence
    if text and text[-1] not in '.!?':
        text += '.'
    
    logger.debug(f"Text cleaned: '{original}' -> '{text[:100]}...'")
    
    return text


class TTSRequest(BaseModel):
    model: str = "tts-1"
    voice: str = "alloy"
    input: str
    response_format: str = "mp3"
    # Extended options
    speed: Optional[float] = None  # 0.25 to 4.0
    style: Optional[float] = None  # 0.0 to 1.0 (expressiveness)


@app.get("/v1/models")
async def list_models():
    """List available TTS models (OpenAI-compatible)."""
    return {
        "object": "list",
        "data": [
            {"id": "tts-1", "object": "model", "created": 0, "owned_by": "elevenlabs", "description": "Standard quality (eleven_turbo_v2_5)"},
            {"id": "tts-1-hd", "object": "model", "created": 0, "owned_by": "elevenlabs", "description": "High quality (eleven_multilingual_v2)"},
        ],
    }


@app.post("/v1/audio/speech")
async def create_speech(request: TTSRequest):
    """
    Convert text to speech using ElevenLabs with natural speech processing.
    OpenAI-compatible API.
    """
    # Clean the text for natural speech
    cleaned_text = clean_text_for_speech(request.input)
    
    if not cleaned_text:
        raise HTTPException(status_code=400, detail="Empty input text after cleaning")

    # If ElevenLabs is configured, use it
    if ELEVENLABS_API_KEY:
        try:
            return await _elevenlabs_tts(cleaned_text, request)
        except Exception as e:
            logger.warning(f"ElevenLabs TTS failed, falling back to local: {e}")

    # Fall back to local TTS
    return await _fallback_tts(cleaned_text, request)


async def _elevenlabs_tts(text: str, request: TTSRequest) -> Response:
    """
    Call ElevenLabs API for premium natural TTS.
    
    Model selection:
    - tts-1 -> eleven_turbo_v2_5 (fast, good quality)
    - tts-1-hd -> eleven_multilingual_v2 (best quality, most natural)
    
    Voice settings optimized for conversational speech:
    - Stability: 0.35-0.5 (lower = more expressive, higher = more consistent)
    - Similarity boost: 0.75 (voice fidelity)
    - Style: 0.0-0.3 (expressiveness)
    - Speaker boost: True (clarity)
    """
    voice_id = VOICE_MAP.get(request.voice.lower(), MYCA_VOICE_ID)
    
    # Select model based on OpenAI model mapping
    if request.model == "tts-1-hd":
        model_id = "eleven_multilingual_v2"  # Best quality, most natural
    else:
        model_id = "eleven_turbo_v2_5"  # Fast and good quality
    
    # Override with env if set
    if DEFAULT_MODEL and DEFAULT_MODEL != "eleven_multilingual_v2":
        model_id = DEFAULT_MODEL
    
    logger.info(f"MYCA TTS: model={model_id}, voice_id={voice_id}")
    logger.info(f"Text ({len(text)} chars): {text[:80]}...")

    # ElevenLabs streaming endpoint
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    
    # Voice settings optimized for natural conversational speech
    # Lower stability = more expressive/natural variation
    # Higher similarity = stays closer to original voice
    voice_settings = {
        "stability": 0.40,          # Slightly lower for more natural variation
        "similarity_boost": 0.75,   # Good voice fidelity
        "style": request.style if request.style is not None else 0.15,  # Slight expressiveness
        "use_speaker_boost": True,  # Enhanced clarity
    }
    
    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": voice_settings,
    }
    
    # For turbo models, enable streaming optimization
    if "turbo" in model_id or "flash" in model_id:
        payload["optimize_streaming_latency"] = 3

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        
        audio_size = len(resp.content)
        logger.info(f"MYCA TTS success: {audio_size} bytes, model={model_id}")

        return Response(
            content=resp.content,
            media_type="audio/mpeg",
            headers={
                "X-TTS-Provider": "elevenlabs",
                "X-Voice-ID": voice_id,
                "X-Model": model_id,
                "X-Voice-Name": "Arabella",
                "X-Text-Length": str(len(text)),
            },
        )


async def _fallback_tts(text: str, request: TTSRequest) -> Response:
    """Fall back to local openedai-speech."""
    logger.warning("Falling back to local TTS (openedai-speech)")
    url = f"{FALLBACK_TTS_URL}/v1/audio/speech"
    payload = {
        "model": request.model,
        "voice": request.voice if request.voice in ["alloy", "echo", "fable", "onyx", "nova", "shimmer"] else "alloy",
        "input": text,
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
        raise HTTPException(status_code=502, detail=f"Both ElevenLabs and fallback TTS failed: {e}")


@app.post("/v1/audio/speech/preview")
async def preview_cleaned_text(request: TTSRequest):
    """Preview how text will be cleaned before TTS (for debugging)."""
    original = request.input
    cleaned = clean_text_for_speech(original)
    return {
        "original": original,
        "cleaned": cleaned,
        "original_length": len(original),
        "cleaned_length": len(cleaned),
        "model_to_use": "eleven_multilingual_v2" if request.model == "tts-1-hd" else "eleven_turbo_v2_5",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "provider": "elevenlabs" if ELEVENLABS_API_KEY else "local",
        "voice_id": MYCA_VOICE_ID,
        "voice_name": "Arabella (MYCA)",
        "default_model": DEFAULT_MODEL,
        "features": [
            "text_cleaning",
            "markdown_removal", 
            "abbreviation_expansion",
            "natural_pauses",
            "conversational_voice_settings",
        ],
    }
