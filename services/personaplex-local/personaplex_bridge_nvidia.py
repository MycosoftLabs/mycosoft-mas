#!/usr/bin/env python3
'''
PersonaPlex NVIDIA Bridge - February 2026 (Refactored)

PURE I/O LAYER - No Decision Making Here

This bridge ONLY handles:
1. Audio I/O with Moshi server
2. Transcript streaming (partial + final)
3. Forwarding ALL user intent to single orchestrator endpoint
4. Speaking orchestrator responses via Moshi TTS

ALL decisions are made by MYCA Orchestrator:
- Tool usage
- Memory writes
- n8n workflow execution
- Agent routing
- Safety confirmation
'''
import asyncio
import base64
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

import aiohttp
import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("personaplex-bridge")

app = FastAPI(title="PersonaPlex NVIDIA Bridge", version="4.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
MOSHI_HOST = os.getenv("MOSHI_HOST", "localhost")
MOSHI_PORT = int(os.getenv("MOSHI_PORT", "8998"))
MOSHI_WS_URL = f"ws://{MOSHI_HOST}:{MOSHI_PORT}/api/chat"
MAS_ORCHESTRATOR_URL = os.getenv("MAS_ORCHESTRATOR_URL", "http://192.168.0.188:8001").rstrip("/")
MAS_VOICE_ENDPOINT = "/voice/orchestrator/chat"
MAS_TIMEOUT = float(os.getenv("MAS_TIMEOUT", "15"))
TRANSCRIPT_DEDUP_SECONDS = float(os.getenv("TRANSCRIPT_DEDUP_SECONDS", "1.5"))

# Load prompts from PromptManager if available, else use defaults
def load_myca_persona():
    try:
        from mycosoft_mas.core.prompt_manager import get_prompt_manager
        pm = get_prompt_manager()
        return pm.get_voice_prompt_for_moshi()
    except ImportError:
        return '''You are MYCA, the AI operator for Mycosoft's Multi-Agent System.
Confident but humble. Warm. Proactive. Patient. Honest.
You coordinate agents, monitor systems, and help users.
Speak naturally and concisely. Welcome to Mycosoft.'''

MYCA_PERSONA = load_myca_persona()

VOICE_PROMPTS = {
    "myca": "NATF2.pt",
    "default": "NATF2.pt",
}


# ============================================================================
# Models
# ============================================================================

class SessionCreate(BaseModel):
    conversation_id: Optional[str] = None
    persona: str = "myca"
    voice: str = "myca"

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    text: str
    persona: str = "myca"


@dataclass
class BridgeSession:
    """
    Session state for I/O tracking only.
    NO decision-making state - that's in orchestrator.
    """
    session_id: str
    conversation_id: str
    persona: str
    voice: str
    voice_prompt: str
    text_prompt: str
    created_at: str
    # Deduplication only - not decision state
    last_transcript: Optional[str] = None
    last_transcript_at: float = 0.0
    last_response: Optional[str] = None
    last_response_at: float = 0.0
    # RTF tracking
    rtf_samples: list = field(default_factory=list)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def to_dict(self) -> dict:
        rtf_avg = sum(self.rtf_samples) / len(self.rtf_samples) if self.rtf_samples else 0.0
        return {
            "session_id": self.session_id,
            "conversation_id": self.conversation_id,
            "persona": self.persona,
            "voice": self.voice,
            "voice_prompt": self.voice_prompt,
            "created_at": self.created_at,
            "rtf_avg": round(rtf_avg, 3),
        }
    
    def record_rtf(self, generation_ms: float, audio_duration_ms: float):
        """Record RTF sample for monitoring."""
        if audio_duration_ms > 0:
            rtf = generation_ms / audio_duration_ms
            self.rtf_samples.append(rtf)
            # Keep last 100 samples
            if len(self.rtf_samples) > 100:
                self.rtf_samples = self.rtf_samples[-100:]


sessions: dict[str, BridgeSession] = {}
moshi_available = False
last_check = None


# ============================================================================
# HTTP Client
# ============================================================================

async def get_http_client() -> httpx.AsyncClient:
    client = getattr(app.state, "http", None)
    if client is None:
        client = httpx.AsyncClient(timeout=MAS_TIMEOUT)
        app.state.http = client
    return client


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_response_text(payload: object) -> Optional[str]:
    """Extract response text from orchestrator response."""
    if isinstance(payload, dict):
        for key in ("response_text", "response", "text", "message", "answer"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    if isinstance(payload, list) and payload:
        first = payload[0]
        if isinstance(first, str) and first.strip():
            return first.strip()
        if isinstance(first, dict):
            for key in ("response_text", "response", "text", "message", "answer"):
                value = first.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
    return None


# ============================================================================
# Orchestrator Integration (Single Decision Point)
# ============================================================================

async def call_orchestrator(session: BridgeSession, message: str, modality: str = "voice") -> tuple[str, dict]:
    """
    Call the MYCA orchestrator - the ONLY decision point.
    
    ALL user intent is forwarded here. The orchestrator decides:
    - Whether to call tools
    - Whether to write memory
    - Whether to trigger workflows
    - How to respond
    
    Args:
        session: Current bridge session
        message: User message/transcript
        modality: 'voice' or 'text'
        
    Returns:
        (response_text, full_response_data)
    """
    if not MAS_ORCHESTRATOR_URL:
        raise RuntimeError("MAS_ORCHESTRATOR_URL is not configured")
    
    client = await get_http_client()
    
    # Standard orchestrator request format
    payload = {
        "message": message,
        "conversation_id": session.conversation_id,
        "session_id": session.session_id,
        "source": "personaplex",
        "modality": modality,
    }
    
    logger.info(f"[{session.session_id}] -> Orchestrator: {message[:100]}...")
    
    response = await client.post(
        f"{MAS_ORCHESTRATOR_URL}{MAS_VOICE_ENDPOINT}",
        json=payload
    )
    response.raise_for_status()
    data = response.json()
    
    response_text = extract_response_text(data)
    if not response_text:
        raise RuntimeError("Orchestrator response missing response_text")
    
    logger.info(f"[{session.session_id}] <- Orchestrator: {response_text[:100]}...")
    
    return response_text, data


async def send_moshi_text(moshi_ws: aiohttp.ClientWebSocketResponse, text: str) -> None:
    """Send text to Moshi for speech synthesis."""
    message = normalize_text(text)
    if not message:
        return
    await moshi_ws.send_bytes(b"\x02" + message.encode("utf-8"))
    logger.debug(f"Sent to Moshi TTS: {message[:50]}...")


# ============================================================================
# Health Check
# ============================================================================

async def check_moshi_health():
    global moshi_available, last_check
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"http://{MOSHI_HOST}:{MOSHI_PORT}/", timeout=5.0)
            if resp.status_code == 200 and ("moshi" in resp.text.lower() or "personaplex" in resp.text.lower()):
                moshi_available = True
                last_check = datetime.now(timezone.utc).isoformat()
                logger.info("NVIDIA Moshi server is available")
                return True
    except Exception as e:
        logger.warning(f"Moshi health check failed: {e}")
    moshi_available = False
    last_check = datetime.now(timezone.utc).isoformat()
    return False


# ============================================================================
# Lifecycle Events
# ============================================================================

@app.on_event("startup")
async def startup():
    await check_moshi_health()
    asyncio.create_task(periodic_check())

@app.on_event("shutdown")
async def shutdown():
    client = getattr(app.state, "http", None)
    if client:
        await client.aclose()
        app.state.http = None

async def periodic_check():
    while True:
        await asyncio.sleep(30)
        await check_moshi_health()


# ============================================================================
# REST Endpoints
# ============================================================================

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "personaplex-nvidia-bridge",
        "version": "4.0.0",
        "architecture": "pure-io",
        "moshi_available": moshi_available,
        "moshi_url": f"http://{MOSHI_HOST}:{MOSHI_PORT}",
        "moshi_ws_url": MOSHI_WS_URL,
        "mas_orchestrator": MAS_ORCHESTRATOR_URL,
        "timestamp": last_check or datetime.now(timezone.utc).isoformat()
    }

@app.post("/session")
async def create_session(req: SessionCreate):
    sid = str(uuid4())
    cid = req.conversation_id or str(uuid4())
    voice_prompt = VOICE_PROMPTS.get(req.voice, VOICE_PROMPTS["default"])
    
    sessions[sid] = BridgeSession(
        session_id=sid,
        conversation_id=cid,
        persona=req.persona,
        voice=req.voice,
        voice_prompt=voice_prompt,
        text_prompt=MYCA_PERSONA,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    
    return {
        "session_id": sid,
        "conversation_id": cid,
        "mode": "personaplex" if moshi_available else "degraded",
        "moshi_available": moshi_available,
    }

@app.get("/session/{session_id}")
async def get_session(session_id: str):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.to_dict()

@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    if session_id in sessions:
        del sessions[session_id]
        return {"status": "deleted", "session_id": session_id}
    raise HTTPException(status_code=404, detail="Session not found")


@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    REST chat endpoint - forwards to orchestrator, returns response.
    
    For audio: Use WebSocket endpoint instead.
    """
    session_id = request.session_id
    if session_id and session_id in sessions:
        session = sessions[session_id]
    else:
        session_id = str(uuid4())
        session = BridgeSession(
            session_id=session_id,
            conversation_id=str(uuid4()),
            persona=request.persona,
            voice="myca",
            voice_prompt=VOICE_PROMPTS["default"],
            text_prompt=MYCA_PERSONA,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        sessions[session_id] = session
    
    text = normalize_text(request.text)
    if not text:
        raise HTTPException(status_code=400, detail="Empty message")
    
    try:
        response_text, data = await call_orchestrator(session, text, modality="text")
        return {
            "session_id": session.session_id,
            "response_text": response_text,
            "conversation_id": session.conversation_id,
            "actions_taken": data.get("actions_taken", []),
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


# ============================================================================
# WebSocket Bridge (Pure Audio I/O)
# ============================================================================

@app.websocket("/ws/{session_id}")
async def websocket_bridge(websocket: WebSocket, session_id: str):
    """
    WebSocket bridge for full-duplex voice.
    
    This is PURE I/O:
    - Receives audio from browser, forwards to Moshi
    - Receives audio from Moshi, forwards to browser
    - Receives transcript from Moshi, forwards to orchestrator
    - Receives response from orchestrator, sends to Moshi for TTS
    """
    await websocket.accept()
    
    session = sessions.get(session_id)
    if session is None:
        session = BridgeSession(
            session_id=session_id,
            conversation_id=str(uuid4()),
            persona="myca",
            voice="myca",
            voice_prompt=VOICE_PROMPTS["default"],
            text_prompt=MYCA_PERSONA,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        sessions[session_id] = session
    
    import urllib.parse
    params = urllib.parse.urlencode({
        "text_prompt": session.text_prompt or MYCA_PERSONA,
        "voice_prompt": session.voice_prompt or "NATF2.pt",
        "audio_temperature": "0.7",
        "text_temperature": "0.7",
        "text_topk": "25",
        "audio_topk": "250",
        "pad_mult": "0",
    })
    moshi_url = f"{MOSHI_WS_URL}?{params}"
    logger.info(f"Connecting to Moshi: {moshi_url}")
    
    try:
        async with aiohttp.ClientSession() as aio_session:
            async with aio_session.ws_connect(moshi_url) as moshi_ws:
                handshake = await asyncio.wait_for(moshi_ws.receive(), timeout=30.0)
                if handshake.type == aiohttp.WSMsgType.BINARY and handshake.data == b'\x00':
                    logger.info(f"Moshi handshake OK for {session_id}")
                    await websocket.send_json({
                        "type": "connected",
                        "session_id": session_id,
                        "backend": "nvidia-personaplex",
                        "architecture": "pure-io",
                    })
                else:
                    await websocket.send_json({"type": "error", "message": "Handshake failed"})
                    return
                
                async def forward_moshi_to_browser():
                    """Forward Moshi output to browser (audio + text)."""
                    try:
                        async for msg in moshi_ws:
                            if msg.type == aiohttp.WSMsgType.BINARY:
                                data = msg.data
                                if len(data) > 0:
                                    kind = data[0]
                                    payload = data[1:]
                                    if kind == 1:  # Audio
                                        await websocket.send_bytes(payload)
                                    elif kind == 2:  # Text from Moshi
                                        text = payload.decode("utf-8")
                                        normalized = normalize_text(text)
                                        await websocket.send_json({"type": "text", "text": text})
                                        
                                        # Forward to orchestrator
                                        if normalized:
                                            await handle_transcript(normalized, session, moshi_ws, websocket)
                            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                break
                    except Exception as e:
                        logger.error(f"Moshi->Browser error: {e}")
                
                async def forward_browser_to_moshi():
                    """Forward browser input to Moshi (audio + text)."""
                    try:
                        while True:
                            data = await websocket.receive()
                            if "bytes" in data:
                                # Audio data - forward with kind byte
                                await moshi_ws.send_bytes(b'\x01' + data["bytes"])
                            elif "text" in data:
                                # Text input from browser
                                await handle_browser_input(data["text"], session, moshi_ws, websocket)
                    except WebSocketDisconnect:
                        logger.info(f"Browser disconnected: {session_id}")
                    except Exception as e:
                        logger.error(f"Browser->Moshi error: {e}")
                
                await asyncio.gather(
                    forward_moshi_to_browser(),
                    forward_browser_to_moshi(),
                    return_exceptions=True
                )
    except Exception as e:
        logger.error(f"WebSocket bridge error: {e}")
        await websocket.send_json({"type": "error", "message": str(e)})


async def handle_transcript(text: str, session: BridgeSession, moshi_ws, websocket) -> None:
    """
    Handle transcript from Moshi - forward to orchestrator.
    
    NO local decision making. ALL transcripts go to orchestrator.
    Only deduplication is done here.
    """
    normalized = normalize_text(text)
    if not normalized:
        return
    
    now = time.monotonic()
    
    # Deduplication only
    async with session.lock:
        # Don't forward exact duplicates within time window
        if session.last_transcript == normalized and now - session.last_transcript_at < TRANSCRIPT_DEDUP_SECONDS:
            return
        # Don't forward if it's the echo of last response
        if session.last_response and normalized == session.last_response and now - session.last_response_at < TRANSCRIPT_DEDUP_SECONDS:
            return
        session.last_transcript = normalized
        session.last_transcript_at = now
    
    # Forward ALL transcripts to orchestrator - no local intent classification
    try:
        start_time = time.monotonic()
        response_text, data = await call_orchestrator(session, normalized, modality="voice")
        generation_time = (time.monotonic() - start_time) * 1000
        
        # Track response for deduplication
        session.last_response = normalize_text(response_text)
        session.last_response_at = time.monotonic()
        
        # Send response metadata to browser
        await websocket.send_json({
            "type": "orchestrator_response",
            "text": response_text,
            "source_text": normalized,
            "session_id": session.session_id,
            "actions_taken": data.get("actions_taken", []),
            "generation_ms": round(generation_time),
        })
        
        # Send response to Moshi for TTS
        await send_moshi_text(moshi_ws, response_text)
        
    except Exception as e:
        logger.error(f"Orchestrator call failed: {e}")
        await websocket.send_json({
            "type": "error",
            "message": f"Orchestrator error: {str(e)}",
            "source_text": normalized,
            "session_id": session.session_id,
        })


async def handle_browser_input(raw_text: str, session: BridgeSession, moshi_ws, websocket) -> None:
    """
    Handle text input from browser.
    
    Forwards to orchestrator, then speaks response via Moshi.
    """
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        payload = {"type": "user_text", "text": raw_text}
    
    if not isinstance(payload, dict):
        return
    
    text = normalize_text(payload.get("text", ""))
    if not text:
        return
    
    # Forward to orchestrator
    try:
        response_text, data = await call_orchestrator(session, text, modality="text")
        
        # Track for deduplication
        session.last_response = normalize_text(response_text)
        session.last_response_at = time.monotonic()
        
        # Send metadata to browser
        await websocket.send_json({
            "type": "orchestrator_response",
            "text": response_text,
            "source_text": text,
            "session_id": session.session_id,
            "actions_taken": data.get("actions_taken", []),
        })
        
        # Send to Moshi for TTS
        await send_moshi_text(moshi_ws, response_text)
        
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e),
            "source_text": text,
            "session_id": session.session_id,
        })


@app.get("/")
async def redirect_to_moshi():
    return RedirectResponse(url=f"http://{MOSHI_HOST}:{MOSHI_PORT}")

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting PersonaPlex NVIDIA Bridge (Pure I/O) on port 8999")
    uvicorn.run(app, host="0.0.0.0", port=8999)
