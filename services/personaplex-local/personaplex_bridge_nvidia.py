#!/usr/bin/env python3
"""
PersonaPlex NVIDIA Bridge - February 2026 (v5.0.0 - Full Duplex + MAS Memory)

Architecture:
- Moshi handles full-duplex voice conversation (STT + LLM + TTS)
- Text is CLONED to MAS asynchronously for memory/knowledge (non-blocking)
- MAS does NOT interrupt Moshi's conversation flow
"""
import asyncio
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List
from uuid import uuid4

import aiohttp
import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("personaplex-bridge")

app = FastAPI(title="PersonaPlex NVIDIA Bridge", version="5.0.0")

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

# MAS for memory/knowledge (async, non-blocking)
MAS_ORCHESTRATOR_URL = os.getenv("MAS_ORCHESTRATOR_URL", "http://192.168.0.188:8001").rstrip("/")
MAS_MEMORY_ENDPOINT = "/voice/memory/log"  # Async memory endpoint
MAS_TIMEOUT = float(os.getenv("MAS_TIMEOUT", "5"))  # Short timeout, fire-and-forget

def load_myca_persona():
    """Load MYCA persona for Moshi's internal LLM."""
    try:
        # Try loading from config file first
        prompt_path = os.path.join(os.path.dirname(__file__), "../../config/myca_personaplex_prompt.txt")
        if os.path.exists(prompt_path):
            with open(prompt_path, "r") as f:
                return f.read().strip()
    except Exception as e:
        logger.warning(f"Could not load persona from file: {e}")
    
    # Fallback persona
    return """You are MYCA (Mycelium Yield & Cultivation Assistant), the AI voice of Mycosoft Labs.

IDENTITY:
- Created by Morgan at Mycosoft Labs
- You run on PersonaPlex, powered by NVIDIA Moshi for real-time voice
- You coordinate 227+ autonomous agents via MAS (Multi-Agent System)
- You have access to MINDEX (Mushroom Intelligence Index), Notion knowledge base, and scientific databases

KNOWLEDGE DOMAINS:
- Mushroom cultivation, mycology, and fungal biology
- Mycosoft devices: Mushroom 1, SporeBase, MycoBrain neuromorphic chip
- Infrastructure: Proxmox VMs, Docker containers, UniFi network
- Scientific computing, protein simulation, AlphaFold integration

PERSONALITY:
- Warm, curious, scientifically rigorous
- Speak naturally and conversationally
- Be concise but informative
- Show genuine interest in helping

CAPABILITIES:
- Answer questions about Mycosoft, mushrooms, and technology
- Discuss scientific topics and research
- Provide cultivation advice
- Coordinate with autonomous agents (background)

Remember: You ARE Mycosoft's AI - speak with confidence about what we build."""

MYCA_PERSONA = load_myca_persona()
logger.info(f"Loaded MYCA persona ({len(MYCA_PERSONA)} chars)")

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
    session_id: str
    conversation_id: str
    persona: str
    voice: str
    created_at: str
    # Conversation history for MAS memory
    transcript_history: List[dict] = field(default_factory=list)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def to_dict(self):
        return {"session_id": self.session_id, "conversation_id": self.conversation_id}

sessions = {}
moshi_available = False
http_client: Optional[httpx.AsyncClient] = None

async def get_http_client():
    global http_client
    if http_client is None:
        http_client = httpx.AsyncClient(timeout=MAS_TIMEOUT)
    return http_client

def normalize(text):
    return re.sub(r"\s+", " ", text).strip()

# ============================================================================
# MAS MEMORY CLONING (Async, Non-blocking)
# ============================================================================

async def clone_to_mas_memory(session: BridgeSession, speaker: str, text: str):
    """
    Asynchronously clone transcript to MAS for memory/knowledge building.
    This is fire-and-forget - does NOT block or interrupt Moshi conversation.
    """
    if not text or len(text.strip()) < 2:
        return
    
    text = normalize(text)
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Add to local history
    entry = {"speaker": speaker, "text": text, "timestamp": timestamp}
    async with session.lock:
        session.transcript_history.append(entry)
        # Keep last 50 entries
        if len(session.transcript_history) > 50:
            session.transcript_history = session.transcript_history[-50:]
    
    # Fire-and-forget to MAS (don't await response, just log errors)
    asyncio.create_task(_send_to_mas_memory(session, entry))

async def _send_to_mas_memory(session: BridgeSession, entry: dict):
    """Background task to send memory to MAS."""
    try:
        client = await get_http_client()
        payload = {
            "conversation_id": session.conversation_id,
            "session_id": session.session_id,
            "speaker": entry["speaker"],
            "text": entry["text"],
            "timestamp": entry["timestamp"],
            "source": "personaplex_voice"
        }
        
        # Try memory endpoint first, fallback to voice feedback
        endpoints = [
            f"{MAS_ORCHESTRATOR_URL}/voice/memory/log",
            f"{MAS_ORCHESTRATOR_URL}/voice/feedback"
        ]
        
        for endpoint in endpoints:
            try:
                resp = await client.post(endpoint, json=payload)
                if resp.status_code in (200, 201, 202):
                    logger.debug(f"[MAS] Memory logged: {entry['speaker']}: {entry['text'][:30]}...")
                    return
            except Exception:
                continue
        
        logger.debug(f"[MAS] Memory log failed (non-critical)")
        
    except Exception as e:
        # Non-critical - just log and continue
        logger.debug(f"[MAS] Memory clone error (non-critical): {e}")

# ============================================================================
# MOSHI HEALTH CHECK
# ============================================================================

async def check_moshi():
    global moshi_available
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get(f"http://{MOSHI_HOST}:{MOSHI_PORT}/", timeout=5)
            moshi_available = r.status_code in (200, 426)
    except Exception as e:
        if "426" in str(e):
            moshi_available = True
        else:
            moshi_available = False

@app.on_event("startup")
async def startup():
    await check_moshi()
    asyncio.create_task(periodic_check())

async def periodic_check():
    while True:
        await asyncio.sleep(30)
        await check_moshi()

@app.on_event("shutdown")
async def shutdown():
    global http_client
    if http_client:
        await http_client.aclose()

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": "5.0.0-full-duplex",
        "moshi_available": moshi_available,
        "architecture": "moshi_full_duplex_with_mas_memory_clone"
    }

@app.post("/session")
async def create_session(body: SessionCreate = None):
    body = body or SessionCreate()
    sid = str(uuid4())
    s = BridgeSession(
        session_id=sid,
        conversation_id=body.conversation_id or str(uuid4()),
        persona=body.persona,
        voice=body.voice,
        created_at=datetime.now(timezone.utc).isoformat()
    )
    sessions[sid] = s
    logger.info(f"Session created: {sid[:8]}")
    return s.to_dict()

@app.websocket("/ws/{session_id}")
async def ws_bridge(websocket: WebSocket, session_id: str):
    await websocket.accept()
    
    s = sessions.get(session_id) or BridgeSession(
        session_id=session_id,
        conversation_id=str(uuid4()),
        persona="myca",
        voice="myca",
        created_at=datetime.now(timezone.utc).isoformat()
    )
    sessions[session_id] = s
    
    # Build Moshi connection URL with MYCA persona
    import urllib.parse
    params = urllib.parse.urlencode({
        "text_prompt": MYCA_PERSONA,
        "voice_prompt": "NATF2.pt",
        "audio_temperature": "0.7",
        "text_temperature": "0.7"
    })
    
    try:
        async with aiohttp.ClientSession() as aio:
            async with aio.ws_connect(f"{MOSHI_WS_URL}?{params}") as moshi:
                # Handle Moshi handshake
                hs = await asyncio.wait_for(moshi.receive(), 30)
                
                handshake_ok = False
                if hs.type == aiohttp.WSMsgType.BINARY and hs.data == b'\x00':
                    handshake_ok = True
                elif hs.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(hs.data)
                        if data.get("type") == "connected":
                            handshake_ok = True
                            logger.info(f"Moshi connected: {data.get('session_id', 'unknown')}")
                    except:
                        pass
                
                if not handshake_ok:
                    await websocket.send_json({"type": "error", "message": "Moshi handshake failed"})
                    return
                
                # Send handshake to browser
                await websocket.send_bytes(b'\x00')
                logger.info(f"[{session_id[:8]}] Full-duplex bridge active")
                
                # Track last text to avoid duplicate memory clones
                last_user_text = ""
                last_myca_text = ""
                
                async def moshi_to_browser():
                    """Forward Moshi audio/text to browser, clone text to MAS memory."""
                    nonlocal last_myca_text
                    try:
                        async for msg in moshi:
                            if msg.type == aiohttp.WSMsgType.BINARY and len(msg.data) > 0:
                                kind = msg.data[0]
                                
                                # Audio (kind=1) - forward directly
                                if kind == 1:
                                    await websocket.send_bytes(msg.data)
                                
                                # Text (kind=2) - forward AND clone to MAS
                                elif kind == 2:
                                    text = msg.data[1:].decode("utf-8", errors="ignore")
                                    await websocket.send_json({"type": "text", "text": text})
                                    
                                    # Clone to MAS memory (async, non-blocking)
                                    normalized = normalize(text)
                                    if normalized and normalized != last_myca_text:
                                        last_myca_text = normalized
                                        await clone_to_mas_memory(s, "myca", normalized)
                                
                            elif msg.type == aiohttp.WSMsgType.TEXT:
                                # JSON messages from Moshi
                                await websocket.send_text(msg.data)
                                
                    except Exception as e:
                        logger.error(f"Moshi->Browser error: {e}")
                
                async def browser_to_moshi():
                    """Forward browser audio/text to Moshi, clone user speech to MAS memory."""
                    nonlocal last_user_text
                    try:
                        while True:
                            data = await websocket.receive()
                            
                            if "bytes" in data:
                                # Audio from browser -> Moshi
                                await moshi.send_bytes(data["bytes"])
                            
                            elif "text" in data:
                                # Text/JSON from browser
                                try:
                                    payload = json.loads(data["text"])
                                    text = normalize(payload.get("text", ""))
                                    
                                    # Clone user text to MAS memory
                                    if text and text != last_user_text:
                                        last_user_text = text
                                        await clone_to_mas_memory(s, "user", text)
                                    
                                    # Forward text to Moshi if needed
                                    if payload.get("forward_to_moshi", False) and text:
                                        await moshi.send_bytes(b"\x02" + text.encode("utf-8"))
                                        
                                except json.JSONDecodeError:
                                    pass
                                    
                    except WebSocketDisconnect:
                        logger.info(f"[{session_id[:8]}] Browser disconnected")
                    except Exception as e:
                        logger.error(f"Browser->Moshi error: {e}")
                
                # Run both directions concurrently
                await asyncio.gather(
                    moshi_to_browser(),
                    browser_to_moshi(),
                    return_exceptions=True
                )
                
    except Exception as e:
        logger.error(f"WebSocket bridge error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass

@app.get("/session/{session_id}/history")
async def get_session_history(session_id: str):
    """Get conversation history for a session."""
    s = sessions.get(session_id)
    if not s:
        return {"error": "Session not found"}
    return {"session_id": session_id, "history": s.transcript_history}

@app.get("/")
async def root():
    return RedirectResponse(f"http://{MOSHI_HOST}:{MOSHI_PORT}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8999)
