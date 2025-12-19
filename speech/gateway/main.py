"""
MYCA Speech Gateway Service

Handles audio → STT → n8n → TTS → audio pipeline with Vault secret management.
"""

import os
import uuid
import time
import base64
import logging
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="MYCA Speech Gateway", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
N8N_BASE_URL = os.getenv("N8N_BASE_URL", "http://localhost:5678")
N8N_WEBHOOK_PATH = os.getenv("N8N_WEBHOOK_PATH", "/webhook/myca-command")
VAULT_ADDR = os.getenv("VAULT_ADDR", "http://localhost:8200")
VAULT_TOKEN = os.getenv("VAULT_TOKEN", "")
VAULT_SECRET_PATH = os.getenv("VAULT_SECRET_PATH", "secret/data/myca/speech")
AUDIT_LOG_PATH = Path(os.getenv("AUDIT_LOG_PATH", "data/speech_audit.jsonl"))
STORE_RAW_AUDIO = os.getenv("STORE_RAW_AUDIO", "false").lower() == "true"
RAW_AUDIO_PATH = Path(os.getenv("RAW_AUDIO_PATH", "data/speech_audio"))

# Create directories
AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
if STORE_RAW_AUDIO:
    RAW_AUDIO_PATH.mkdir(parents=True, exist_ok=True)

# Rate limiting (simple token bucket)
_rate_limit_tokens = 10
_rate_limit_max = 10
_rate_limit_refill_rate = 1.0  # tokens per second
_last_refill = time.time()


class SpeechTurnRequest(BaseModel):
    """Request model for speech turn."""
    request_id: Optional[str] = None
    store_audio: bool = False
    wake_word_enabled: bool = False
    provider: str = "openai"  # "openai" or "browser"


class SpeechTurnResponse(BaseModel):
    """Response model for speech turn."""
    request_id: str
    transcript: str
    myca_text: str
    tts_audio_base64: Optional[str] = None
    timings_ms: Dict[str, float]
    require_confirm: bool = False
    confirmation_request_id: Optional[str] = None


# Vault client (simplified - can be enhanced with hvac library)
async def get_vault_secret(key: str) -> Optional[str]:
    """
    Retrieve secret from Vault.
    
    Falls back to environment variable if Vault is not available.
    """
    # Try Vault first
    if VAULT_ADDR and VAULT_TOKEN:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(
                    f"{VAULT_ADDR}/v1/{VAULT_SECRET_PATH}/{key}",
                    headers={"X-Vault-Token": VAULT_TOKEN}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("data", {}).get("data", {}).get(key)
        except Exception as e:
            logger.warning(f"Vault retrieval failed for {key}: {e}, falling back to env")
    
    # Fallback to environment variable
    env_key = key.upper().replace("-", "_")
    return os.getenv(env_key) or os.getenv(f"OPENAI_{env_key}")


async def get_openai_api_key() -> str:
    """Get OpenAI API key from Vault or env."""
    key = await get_vault_secret("openai-api-key")
    if not key:
        raise HTTPException(
            status_code=503,
            detail="OpenAI API key not found in Vault or environment"
        )
    return key


# Rate limiting
def check_rate_limit() -> bool:
    """Check if request is within rate limit."""
    global _rate_limit_tokens, _last_refill
    
    now = time.time()
    elapsed = now - _last_refill
    _rate_limit_tokens = min(
        _rate_limit_max,
        _rate_limit_tokens + elapsed * _rate_limit_refill_rate
    )
    _last_refill = now
    
    if _rate_limit_tokens >= 1:
        _rate_limit_tokens -= 1
        return True
    return False


# STT Providers
async def stt_openai(audio_data: bytes, api_key: str) -> str:
    """Transcribe audio using OpenAI Whisper API."""
    async with httpx.AsyncClient(timeout=30) as client:
        files = {"file": ("audio.webm", audio_data, "audio/webm")}
        data = {"model": "whisper-1"}
        headers = {"Authorization": f"Bearer {api_key}"}
        
        resp = await client.post(
            "https://api.openai.com/v1/audio/transcriptions",
            files=files,
            data=data,
            headers=headers
        )
        resp.raise_for_status()
        result = resp.json()
        return result.get("text", "").strip()


# TTS Providers
async def tts_openai(text: str, api_key: str, voice: str = "alloy") -> bytes:
    """Generate speech using OpenAI TTS API."""
    async with httpx.AsyncClient(timeout=30) as client:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "tts-1",
            "input": text,
            "voice": voice
        }
        
        resp = await client.post(
            "https://api.openai.com/v1/audio/speech",
            json=payload,
            headers=headers
        )
        resp.raise_for_status()
        return resp.content


# Audit logging
def write_audit_event(event: Dict[str, Any]):
    """Write audit event to JSONL file."""
    try:
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"{json.dumps(event)}\n")
    except Exception as e:
        logger.error(f"Failed to write audit event: {e}")


# Safety check
def check_destructive_command(transcript: str) -> bool:
    """Check if transcript contains destructive commands."""
    destructive_keywords = [
        "delete", "destroy", "rollback", "factory reset", "wipe",
        "erase", "remove all", "clear all", "format", "reset everything"
    ]
    transcript_lower = transcript.lower()
    return any(keyword in transcript_lower for keyword in destructive_keywords)


# Wake word check
def check_wake_word(transcript: str) -> bool:
    """Check if transcript starts with wake word."""
    return transcript.lower().strip().startswith("myca")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "speech-gateway",
        "n8n_url": N8N_BASE_URL,
        "vault_configured": bool(VAULT_ADDR and VAULT_TOKEN)
    }


@app.get("/voices")
async def list_voices():
    """List available TTS voices."""
    return {
        "voices": [
            {"id": "alloy", "name": "Alloy", "gender": "neutral"},
            {"id": "echo", "name": "Echo", "gender": "male"},
            {"id": "fable", "name": "Fable", "gender": "male"},
            {"id": "onyx", "name": "Onyx", "gender": "male"},
            {"id": "nova", "name": "Nova", "gender": "female"},
            {"id": "shimmer", "name": "Shimmer", "gender": "female"},
        ],
        "provider": "openai"
    }


@app.post("/speech/turn", response_model=SpeechTurnResponse)
async def speech_turn(
    audio: UploadFile = File(...),
    request_id: Optional[str] = Form(None),
    store_audio: bool = Form(False),
    wake_word_enabled: bool = Form(False),
    provider: str = Form("openai"),
    voice: str = Form("alloy"),
    context: Optional[str] = Form(None)
):
    """
    Process a speech turn: STT → n8n → TTS.
    
    Returns transcript, MYCA response text, and TTS audio.
    """
    start_time = time.time()
    timings = {}
    
    # Rate limiting
    if not check_rate_limit():
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Generate request ID
    req_id = request_id or str(uuid.uuid4())
    
    # Read audio
    audio_start = time.time()
    audio_data = await audio.read()
    timings["audio_read_ms"] = (time.time() - audio_start) * 1000
    
    # Store raw audio if requested
    if store_audio or STORE_RAW_AUDIO:
        audio_file = RAW_AUDIO_PATH / f"{req_id}.webm"
        audio_file.write_bytes(audio_data)
    
    # STT
    stt_start = time.time()
    try:
        if provider == "openai":
            api_key = await get_openai_api_key()
            transcript = await stt_openai(audio_data, api_key)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
    except Exception as e:
        logger.error(f"STT failed: {e}")
        raise HTTPException(status_code=500, detail=f"STT failed: {str(e)}")
    
    timings["stt_ms"] = (time.time() - stt_start) * 1000
    
    if not transcript:
        raise HTTPException(status_code=400, detail="No transcript generated")
    
    # Wake word check
    if wake_word_enabled and not check_wake_word(transcript):
        return SpeechTurnResponse(
            request_id=req_id,
            transcript=transcript,
            myca_text="",
            timings_ms=timings,
            require_confirm=False
        )
    
    # Safety check
    is_destructive = check_destructive_command(transcript)
    
    # Call n8n webhook
    n8n_start = time.time()
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            payload = {
                "request_id": req_id,
                "transcript": transcript,
                "actor": "user",
                "context": context,
                "require_confirm": is_destructive
            }
            
            resp = await client.post(
                f"{N8N_BASE_URL}{N8N_SPEECH_WEBHOOK_PATH}",
                json=payload
            )
            resp.raise_for_status()
            n8n_response = resp.json()
    except Exception as e:
        logger.error(f"n8n webhook failed: {e}")
        raise HTTPException(status_code=500, detail=f"n8n webhook failed: {str(e)}")
    
    timings["n8n_ms"] = (time.time() - n8n_start) * 1000
    
    # Extract MYCA response
    myca_text = n8n_response.get("response_text") or n8n_response.get("response") or n8n_response.get("myca_text", "")
    require_confirm = n8n_response.get("require_confirm", False)
    confirmation_request_id = n8n_response.get("confirmation_request_id")
    
    # TTS
    tts_audio_base64 = None
    if myca_text:
        tts_start = time.time()
        try:
            if provider == "openai":
                api_key = await get_openai_api_key()
                tts_audio = await tts_openai(myca_text, api_key, voice)
                tts_audio_base64 = base64.b64encode(tts_audio).decode("utf-8")
        except Exception as e:
            logger.error(f"TTS failed: {e}")
            # Don't fail the request if TTS fails
        
        timings["tts_ms"] = (time.time() - tts_start) * 1000
    
    timings["total_ms"] = (time.time() - start_time) * 1000
    
    # Audit logging
    audit_event = {
        "request_id": req_id,
        "timestamp": datetime.utcnow().isoformat(),
        "transcript": transcript,
        "myca_text": myca_text,
        "is_destructive": is_destructive,
        "require_confirm": require_confirm,
        "timings_ms": timings,
        "provider": provider,
        "voice": voice
    }
    write_audit_event(audit_event)
    
    return SpeechTurnResponse(
        request_id=req_id,
        transcript=transcript,
        myca_text=myca_text,
        tts_audio_base64=tts_audio_base64,
        timings_ms=timings,
        require_confirm=require_confirm,
        confirmation_request_id=confirmation_request_id
    )


@app.post("/speech/confirm")
async def confirm_action(
    request_id: str = Form(...),
    confirmation_phrase: str = Form(...)
):
    """
    Confirm a destructive action.
    
    Expected phrase format: "Confirm action request_id <id>"
    """
    expected_phrase = f"confirm action request_id {request_id}".lower()
    if confirmation_phrase.lower().strip() != expected_phrase:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid confirmation phrase. Expected: '{expected_phrase}'"
        )
    
    # Call n8n to execute confirmed action
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            payload = {
                "request_id": request_id,
                "action": "confirm",
                "confirmation_phrase": confirmation_phrase
            }
            
            resp = await client.post(
                f"{N8N_BASE_URL}/webhook/myca/command",
                json=payload
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error(f"Confirmation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Confirmation failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
