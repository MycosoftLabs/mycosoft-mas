#!/usr/bin/env python3
'''
PersonaPlex NVIDIA Bridge - January 29, 2026
Proper integration with NVIDIA PersonaPlex server as intended

This bridge:
1. Connects to NVIDIA Moshi server at /api/chat endpoint
2. Uses proper binary Opus audio protocol
3. Handles WebSocket with query parameters (text_prompt, voice_prompt, etc.)
4. Integrates with MYCA orchestrator for tool calls
5. Provides REST API for website integration
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

app = FastAPI(title="PersonaPlex NVIDIA Bridge", version="3.0.0")

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
MAS_CHAT_PATH = os.getenv("MAS_CHAT_PATH", "/voice/orchestrator/chat")
MAS_TIMEOUT = float(os.getenv("MAS_TIMEOUT", "15"))
MAS_MIN_INTERVAL = float(os.getenv("MAS_MIN_INTERVAL", "1.2"))
ENABLE_MAS_ROUTING = os.getenv("ENABLE_MAS_ROUTING", "1") != "0"
ENABLE_MOSHI_TEXT_INJECTION = os.getenv("ENABLE_MOSHI_TEXT_INJECTION", "1") != "0"
TRANSCRIPT_DEDUP_SECONDS = float(os.getenv("TRANSCRIPT_DEDUP_SECONDS", "2.0"))

# MYCA Persona Prompt (as NVIDIA PersonaPlex expects)
MYCA_PERSONA = '''You are MYCA (Mycosoft Autonomous Cognitive Agent), an AI assistant for Mycosoft.
You help users manage their infrastructure, monitor systems, and execute tasks.
You can control Proxmox VMs, UniFi network devices, and coordinate 40+ specialized agents.
You are calm, confident, and concise. You speak naturally and can be interrupted.
When users ask to perform actions, explain what you are doing and confirm before destructive operations.'''

VOICE_PROMPTS = {
    "myca": "NATF2.pt",
    "default": "NATF2.pt",
    "female_casual": "NATF2.pt",
    "male_casual": "NATM2.pt",
}

class SessionCreate(BaseModel):
    conversation_id: Optional[str] = None
    mode: str = "personaplex"
    persona: str = "myca"
    voice: str = "myca"

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    text: str
    persona: str = "myca"
    voice_prompt: Optional[str] = None

@dataclass
class BridgeSession:
    session_id: str
    conversation_id: str
    persona: str
    voice: str
    voice_prompt: str
    text_prompt: str
    created_at: str
    last_moshi_text: Optional[str] = None
    last_moshi_text_at: float = 0.0
    last_mas_call_at: float = 0.0
    last_mas_response: Optional[str] = None
    last_mas_response_at: float = 0.0
    pending_confirmation: Optional[str] = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "conversation_id": self.conversation_id,
            "persona": self.persona,
            "voice": self.voice,
            "voice_prompt": self.voice_prompt,
            "created_at": self.created_at,
            "pending_confirmation": self.pending_confirmation is not None,
        }


sessions: dict[str, BridgeSession] = {}
moshi_available = False
last_check = None

ACTION_PATTERNS = [
    r"\b(turn on|turn off|start|stop|restart|reboot|shutdown)\b",
    r"\b(deploy|rebuild|clear|purge|reset|delete|remove)\b",
    r"\b(enable|disable|open|close|connect|disconnect)\b",
]
QUERY_PATTERNS = [
    r"\b(status|health|check|list|show|how many|what is|what are)\b",
]
CONFIRM_PATTERNS = [r"\b(yes|yeah|confirm|proceed|do it|go ahead)\b"]
CANCEL_PATTERNS = [r"\b(no|cancel|abort|never mind)\b"]

async def check_moshi_health():
    global moshi_available, last_check
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"http://{MOSHI_HOST}:{MOSHI_PORT}/", timeout=5.0)
            if resp.status_code == 200 and "moshi" in resp.text.lower():
                moshi_available = True
                last_check = datetime.now(timezone.utc).isoformat()
                logger.info("NVIDIA Moshi server is available")
                return True
    except Exception as e:
        logger.warning(f"Moshi health check failed: {e}")
    moshi_available = False
    last_check = datetime.now(timezone.utc).isoformat()
    return False

def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def match_any(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)

def classify_intent(text: str) -> dict:
    normalized = normalize_text(text)
    if not normalized:
        return {"type": "empty", "requires_tool": False, "requires_confirmation": False}
    if match_any(CONFIRM_PATTERNS, normalized):
        return {"type": "confirm", "requires_tool": True, "requires_confirmation": False}
    if match_any(CANCEL_PATTERNS, normalized):
        return {"type": "cancel", "requires_tool": False, "requires_confirmation": False}
    if match_any(ACTION_PATTERNS, normalized):
        needs_confirmation = any(k in normalized.lower() for k in ["delete", "remove", "shutdown", "purge", "reset", "clear"])
        return {"type": "action", "requires_tool": True, "requires_confirmation": needs_confirmation}
    if match_any(QUERY_PATTERNS, normalized):
        return {"type": "query", "requires_tool": True, "requires_confirmation": False}
    return {"type": "chitchat", "requires_tool": False, "requires_confirmation": False}

async def get_http_client() -> httpx.AsyncClient:
    client = getattr(app.state, "http", None)
    if client is None:
        client = httpx.AsyncClient(timeout=MAS_TIMEOUT)
        app.state.http = client
    return client

def extract_response_text(payload: object) -> Optional[str]:
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

async def call_mas(session: BridgeSession, message: str) -> tuple[str, dict]:
    if not MAS_ORCHESTRATOR_URL:
        raise RuntimeError("MAS_ORCHESTRATOR_URL is not configured")
    client = await get_http_client()
    payload = {
        "message": message,
        "conversation_id": session.conversation_id,
        "session_id": session.session_id,
        "source": "personaplex-nvidia-bridge",
        "persona": session.persona,
        "voice_prompt": session.voice_prompt,
    }
    response = await client.post(f"{MAS_ORCHESTRATOR_URL}{MAS_CHAT_PATH}", json=payload)
    response.raise_for_status()
    data = response.json()
    response_text = extract_response_text(data)
    if not response_text:
        raise RuntimeError("MAS response missing response_text")
    return response_text, data

async def send_moshi_text(moshi_ws: aiohttp.ClientWebSocketResponse, text: str) -> None:
    if not ENABLE_MOSHI_TEXT_INJECTION:
        return
    message = normalize_text(text)
    if not message:
        return
    await moshi_ws.send_bytes(b"\x02" + message.encode("utf-8"))

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

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "personaplex-nvidia-bridge",
        "moshi_available": moshi_available,
        "moshi_url": f"http://{MOSHI_HOST}:{MOSHI_PORT}",
        "moshi_ws_url": MOSHI_WS_URL,
        "mas_orchestrator": MAS_ORCHESTRATOR_URL,
        "mas_routing_enabled": ENABLE_MAS_ROUTING,
        "moshi_text_injection": ENABLE_MOSHI_TEXT_INJECTION,
        "timestamp": last_check or datetime.now(timezone.utc).isoformat()
    }

@app.post("/session")
async def create_session(req: SessionCreate):
    sid = str(uuid4())
    cid = req.conversation_id or str(uuid4())
    voice_prompt = VOICE_PROMPTS.get(req.voice, VOICE_PROMPTS["default"])
    text_prompt = MYCA_PERSONA if req.persona == "myca" else ""
    
    sessions[sid] = BridgeSession(
        session_id=sid,
        conversation_id=cid,
        persona=req.persona,
        voice=req.voice,
        voice_prompt=voice_prompt,
        text_prompt=text_prompt,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    
    return {
        "session_id": sid,
        "conversation_id": cid,
        "mode": "personaplex" if moshi_available else "elevenlabs",
        "moshi_available": moshi_available,
        "voice_prompt": voice_prompt,
        "ws_url": f"ws://localhost:8999/ws/{sid}",
        "direct_moshi_url": f"http://{MOSHI_HOST}:{MOSHI_PORT}",
        "created_at": sessions[sid].created_at
    }

@app.get("/sessions")
async def list_sessions():
    return {"sessions": [session.to_dict() for session in sessions.values()], "count": len(sessions)}

@app.delete("/session/{session_id}")
async def end_session(session_id: str):
    if session_id in sessions:
        del sessions[session_id]
    return {"ended": True, "session_id": session_id}

@app.get("/voices")
async def list_voices():
    return {
        "voices": [
            {"id": "NATF2.pt", "name": "Natural Female 2 (MYCA)", "gender": "female"},
            {"id": "NATF0.pt", "name": "Natural Female 0", "gender": "female"},
            {"id": "NATM2.pt", "name": "Natural Male 2", "gender": "male"},
            {"id": "NATM0.pt", "name": "Natural Male 0", "gender": "male"},
        ],
        "default": "NATF2.pt"
    }

@app.post("/chat")
async def chat(request: ChatRequest):
    if not moshi_available:
        raise HTTPException(status_code=503, detail="PersonaPlex (Moshi) is not available")
    text = normalize_text(request.text)
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")
    if not ENABLE_MOSHI_TEXT_INJECTION:
        raise HTTPException(status_code=503, detail="Moshi text injection disabled")

    session = sessions.get(request.session_id or "")
    if session is None:
        session = BridgeSession(
            session_id=request.session_id or str(uuid4()),
            conversation_id=str(uuid4()),
            persona=request.persona,
            voice="myca",
            voice_prompt=request.voice_prompt or VOICE_PROMPTS["default"],
            text_prompt=MYCA_PERSONA if request.persona == "myca" else "",
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    import urllib.parse
    params = urllib.parse.urlencode({
        "text_prompt": session.text_prompt or MYCA_PERSONA,
        "voice_prompt": request.voice_prompt or session.voice_prompt or "NATF2.pt",
        "audio_temperature": "0.8",
        "text_temperature": "0.8",
        "text_topk": "25",
        "audio_topk": "250",
    })
    moshi_url = f"{MOSHI_WS_URL}?{params}"
    audio_chunks: list[bytes] = []
    response_text: Optional[str] = None

    async with aiohttp.ClientSession() as aio_session:
        async with aio_session.ws_connect(moshi_url) as moshi_ws:
            handshake = await asyncio.wait_for(moshi_ws.receive(), timeout=30.0)
            if handshake.type != aiohttp.WSMsgType.BINARY or handshake.data != b"\x00":
                raise HTTPException(status_code=502, detail="Moshi handshake failed")

            await send_moshi_text(moshi_ws, text)

            last_audio_at = time.monotonic()
            while True:
                try:
                    msg = await asyncio.wait_for(moshi_ws.receive(), timeout=1.5)
                except asyncio.TimeoutError:
                    if audio_chunks and time.monotonic() - last_audio_at > 0.6:
                        break
                    continue

                if msg.type == aiohttp.WSMsgType.BINARY:
                    data = msg.data
                    if not data:
                        continue
                    kind = data[0]
                    payload = data[1:]
                    if kind == 1 and payload:
                        audio_chunks.append(payload)
                        last_audio_at = time.monotonic()
                    elif kind == 2 and payload:
                        decoded = payload.decode("utf-8", errors="ignore").strip()
                        if decoded:
                            response_text = decoded
                elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                    break

    audio_bytes = b"".join(audio_chunks)
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8") if audio_bytes else None

    return {
        "session_id": session.session_id,
        "response_text": response_text or text,
        "has_audio": bool(audio_bytes),
        "audio_mime": "audio/ogg; codecs=opus",
        "audio_base64": audio_b64,
    }

@app.websocket("/ws/{session_id}")
async def websocket_bridge(websocket: WebSocket, session_id: str):
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
        "audio_temperature": "0.8",
        "text_temperature": "0.8",
        "text_topk": "25",
        "audio_topk": "250",
    })
    moshi_url = f"{MOSHI_WS_URL}?{params}"
    logger.info(f"Connecting to Moshi: {moshi_url}")
    
    try:
        async with aiohttp.ClientSession() as aio_session:
            async with aio_session.ws_connect(moshi_url) as moshi_ws:
                handshake = await asyncio.wait_for(moshi_ws.receive(), timeout=30.0)
                if handshake.type == aiohttp.WSMsgType.BINARY and handshake.data == b'\x00':
                    logger.info(f"Moshi handshake OK for {session_id}")
                    await websocket.send_json({"type": "connected", "session_id": session_id, "backend": "nvidia-personaplex"})
                else:
                    await websocket.send_json({"type": "error", "message": "Handshake failed"})
                    return
                
                async def forward_to_browser():
                    try:
                        async for msg in moshi_ws:
                            if msg.type == aiohttp.WSMsgType.BINARY:
                                data = msg.data
                                if len(data) > 0:
                                    kind = data[0]
                                    payload = data[1:]
                                    if kind == 1:
                                        await websocket.send_bytes(payload)
                                    elif kind == 2:
                                        text = payload.decode("utf-8")
                                        normalized = normalize_text(text)
                                        await websocket.send_json({"type": "text", "text": text})
                                        if ENABLE_MAS_ROUTING and normalized:
                                            await handle_moshi_text(normalized, session, moshi_ws, websocket)
                            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                break
                    except Exception as e:
                        logger.error(f"Forward to browser error: {e}")
                
                async def forward_to_moshi():
                    try:
                        while True:
                            data = await websocket.receive()
                            if "bytes" in data:
                                await moshi_ws.send_bytes(b'\x01' + data["bytes"])
                            elif "text" in data:
                                await handle_browser_text(data["text"], session, moshi_ws, websocket)
                    except WebSocketDisconnect:
                        logger.info(f"Browser disconnected: {session_id}")
                    except Exception as e:
                        logger.error(f"Forward to Moshi error: {e}")
                
                await asyncio.gather(forward_to_browser(), forward_to_moshi(), return_exceptions=True)
    except Exception as e:
        logger.error(f"WebSocket bridge error: {e}")
        await websocket.send_json({"type": "error", "message": str(e)})

async def handle_browser_text(raw_text: str, session: BridgeSession, moshi_ws: aiohttp.ClientWebSocketResponse, websocket: WebSocket) -> None:
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        payload = {"type": "user_text", "text": raw_text}

    if not isinstance(payload, dict):
        return

    message_type = payload.get("type", "user_text")
    text = normalize_text(payload.get("text", ""))
    if not text:
        return

    if message_type in ("user_text", "text_input"):
        await route_to_mas(text, session, moshi_ws, websocket, source="browser")
        return

    if message_type == "confirm" and session.pending_confirmation:
        await route_to_mas(session.pending_confirmation, session, moshi_ws, websocket, source="confirmation")
        session.pending_confirmation = None
        return

async def handle_moshi_text(text: str, session: BridgeSession, moshi_ws: aiohttp.ClientWebSocketResponse, websocket: WebSocket) -> None:
    normalized = normalize_text(text)
    if not normalized:
        return

    now = time.monotonic()
    async with session.lock:
        if session.last_moshi_text == normalized and now - session.last_moshi_text_at < TRANSCRIPT_DEDUP_SECONDS:
            return
        if session.last_mas_response and normalized == session.last_mas_response and now - session.last_mas_response_at < TRANSCRIPT_DEDUP_SECONDS:
            return
        session.last_moshi_text = normalized
        session.last_moshi_text_at = now

    intent = classify_intent(normalized)
    if intent["type"] == "cancel":
        session.pending_confirmation = None
        await websocket.send_json({"type": "confirmation_cancelled", "text": normalized, "session_id": session.session_id})
        return

    if intent["type"] == "confirm" and session.pending_confirmation:
        await route_to_mas(session.pending_confirmation, session, moshi_ws, websocket, source="confirmation")
        session.pending_confirmation = None
        return

    if intent["requires_confirmation"]:
        session.pending_confirmation = normalized
        confirmation_prompt = f"Confirmation required for: {normalized}"
        session.last_mas_response = normalize_text(confirmation_prompt)
        session.last_mas_response_at = time.monotonic()
        await websocket.send_json({
            "type": "confirmation_required",
            "text": normalized,
            "session_id": session.session_id,
        })
        await send_moshi_text(moshi_ws, confirmation_prompt)
        return

    if intent["requires_tool"]:
        await route_to_mas(normalized, session, moshi_ws, websocket, source="moshi")

async def route_to_mas(text: str, session: BridgeSession, moshi_ws: aiohttp.ClientWebSocketResponse, websocket: WebSocket, source: str) -> None:
    now = time.monotonic()
    async with session.lock:
        if now - session.last_mas_call_at < MAS_MIN_INTERVAL:
            return
        session.last_mas_call_at = now

    try:
        response_text, data = await call_mas(session, text)
        session.last_mas_response = normalize_text(response_text)
        session.last_mas_response_at = time.monotonic()
        await websocket.send_json({
            "type": "mas_result",
            "text": response_text,
            "source_text": text,
            "session_id": session.session_id,
            "meta": {
                "source": source,
                "conversation_id": session.conversation_id,
            },
        })
        await send_moshi_text(moshi_ws, response_text)
    except Exception as exc:
        await websocket.send_json({
            "type": "mas_error",
            "message": str(exc),
            "source_text": text,
            "session_id": session.session_id,
        })

@app.get("/")
async def redirect_to_moshi():
    return RedirectResponse(url=f"http://{MOSHI_HOST}:{MOSHI_PORT}")

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting PersonaPlex NVIDIA Bridge on port 8999")
    uvicorn.run(app, host="0.0.0.0", port=8999)
