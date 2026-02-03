#!/usr/bin/env python3
"""
PersonaPlex NVIDIA Bridge - February 2026 (v5.1.0 - Full Duplex + MAS Event Stream)

Architecture:
- Moshi handles full-duplex voice conversation (STT + LLM + TTS)
- Text is CLONED to MAS asynchronously for memory/knowledge (non-blocking)
- MAS EVENT STREAM feeds back into Moshi in real-time (agent updates, tool calls, etc.)
"""
import asyncio
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Set
from uuid import uuid4

import aiohttp
import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("personaplex-bridge")

app = FastAPI(title="PersonaPlex NVIDIA Bridge", version="5.1.0")

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

# MAS for memory/knowledge and event stream
MAS_ORCHESTRATOR_URL = os.getenv("MAS_ORCHESTRATOR_URL", "http://192.168.0.188:8001").rstrip("/")
MAS_TIMEOUT = float(os.getenv("MAS_TIMEOUT", "5"))
MAS_EVENT_POLL_INTERVAL = float(os.getenv("MAS_EVENT_POLL_INTERVAL", "2.0"))  # Poll every 2s

def load_myca_persona():
    """Load MYCA persona for Moshi's internal LLM (short version for URL params)."""
    try:
        # Use short prompt to avoid URL length limits
        prompt_path = os.path.join(os.path.dirname(__file__), "../../config/myca_personaplex_prompt_short.txt")
        if os.path.exists(prompt_path):
            with open(prompt_path, "r") as f:
                return f.read().strip()
        # Fallback to long prompt
        prompt_path = os.path.join(os.path.dirname(__file__), "../../config/myca_personaplex_prompt.txt")
        if os.path.exists(prompt_path):
            with open(prompt_path, "r") as f:
                return f.read().strip()[:800]  # Truncate if needed
    except Exception as e:
        logger.warning(f"Could not load persona from file: {e}")
    
    return """You are MYCA (Mycelium Yield & Cultivation Assistant), the AI voice of Mycosoft Labs.

IDENTITY:
- Created by Morgan at Mycosoft Labs
- You run on PersonaPlex, powered by NVIDIA Moshi for real-time voice
- You coordinate 227+ autonomous agents via MAS (Multi-Agent System)
- You have access to MINDEX, Notion knowledge base, and scientific databases

REAL-TIME AWARENESS:
- You may receive system events during conversation (agent updates, tool results, etc.)
- When you receive an event, naturally acknowledge it: "One moment, I just got an update..."
- Integrate the information smoothly into the conversation

KNOWLEDGE DOMAINS:
- Mushroom cultivation, mycology, and fungal biology
- Mycosoft devices: Mushroom 1, SporeBase, MycoBrain neuromorphic chip
- Infrastructure: Proxmox VMs, Docker containers, UniFi network

PERSONALITY:
- Warm, curious, scientifically rigorous
- Speak naturally and conversationally
- Be concise but informative"""

MYCA_PERSONA = load_myca_persona()

class SessionCreate(BaseModel):
    conversation_id: Optional[str] = None
    persona: str = "myca"
    voice: str = "myca"

@dataclass
class BridgeSession:
    session_id: str
    conversation_id: str
    persona: str
    voice: str
    created_at: str
    transcript_history: List[dict] = field(default_factory=list)
    pending_events: List[dict] = field(default_factory=list)
    event_ids_seen: Set[str] = field(default_factory=set)
    last_event_check: float = 0.0
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
# MAS EVENT STREAM - Real-time feedback to Moshi
# ============================================================================

async def poll_mas_events(session: BridgeSession) -> List[dict]:
    """
    Poll MAS for new events (agent updates, tool calls, memory insights).
    Returns list of new events to inject into Moshi.
    """
    try:
        client = await get_http_client()
        
        # Poll the MAS event stream endpoint
        resp = await client.get(
            f"{MAS_ORCHESTRATOR_URL}/events/stream",
            params={
                "session_id": session.session_id,
                "conversation_id": session.conversation_id,
                "since": session.last_event_check
            }
        )
        
        if resp.status_code == 200:
            data = resp.json()
            events = data.get("events", [])
            
            # Filter out already-seen events
            new_events = []
            for event in events:
                event_id = event.get("id", str(hash(json.dumps(event, sort_keys=True))))
                if event_id not in session.event_ids_seen:
                    session.event_ids_seen.add(event_id)
                    new_events.append(event)
            
            session.last_event_check = time.time()
            return new_events
            
    except Exception as e:
        logger.debug(f"Event poll failed (non-critical): {e}")
    
    return []

def format_event_for_moshi(event: dict) -> Optional[str]:
    """
    Format a MAS event into natural language for Moshi to speak.
    """
    event_type = event.get("type", "unknown")
    
    # Agent update
    if event_type == "agent_update":
        agent = event.get("agent_name", "An agent")
        status = event.get("status", "reported")
        message = event.get("message", "")
        if message:
            return f"[SYSTEM EVENT] {agent} {status}: {message}"
    
    # Tool call result
    elif event_type == "tool_result":
        tool = event.get("tool_name", "A tool")
        result = event.get("result_summary", "completed")
        return f"[SYSTEM EVENT] {tool} result: {result}"
    
    # Memory insight
    elif event_type == "memory_insight":
        insight = event.get("insight", "")
        if insight:
            return f"[MEMORY] I just recalled: {insight}"
    
    # Knowledge discovery
    elif event_type == "knowledge":
        topic = event.get("topic", "something")
        info = event.get("info", "")
        return f"[KNOWLEDGE] About {topic}: {info}"
    
    # System status
    elif event_type == "system_status":
        system = event.get("system", "System")
        status = event.get("status", "update")
        return f"[STATUS] {system}: {status}"
    
    # Notification
    elif event_type == "notification":
        message = event.get("message", "")
        priority = event.get("priority", "normal")
        if priority == "high":
            return f"[URGENT] {message}"
        return f"[NOTICE] {message}"
    
    # Generic event
    elif event.get("message"):
        return f"[EVENT] {event.get('message')}"
    
    return None

async def mas_event_loop(session: BridgeSession, moshi_ws, browser_ws):
    """
    Background task that polls MAS for events and injects them into Moshi.
    """
    logger.info(f"[{session.session_id[:8]}] MAS event loop started")
    
    while True:
        try:
            await asyncio.sleep(MAS_EVENT_POLL_INTERVAL)
            
            # Poll for new events
            events = await poll_mas_events(session)
            
            for event in events:
                formatted = format_event_for_moshi(event)
                if formatted:
                    logger.info(f"[{session.session_id[:8]}] Injecting event: {formatted[:50]}...")
                    
                    # Send to Moshi as text input (it will react naturally)
                    try:
                        await moshi_ws.send_bytes(b"\x02" + formatted.encode("utf-8"))
                    except:
                        pass
                    
                    # Also notify browser
                    try:
                        await browser_ws.send_json({
                            "type": "mas_event",
                            "event": event,
                            "formatted": formatted
                        })
                    except:
                        pass
                        
        except asyncio.CancelledError:
            logger.info(f"[{session.session_id[:8]}] MAS event loop stopped")
            break
        except Exception as e:
            logger.debug(f"Event loop error: {e}")

# ============================================================================
# MAS MEMORY CLONING (Async, Non-blocking)
# ============================================================================

async def clone_to_mas_memory(session: BridgeSession, speaker: str, text: str):
    """Clone transcript to MAS for memory building (fire-and-forget)."""
    if not text or len(text.strip()) < 2:
        return
    
    text = normalize(text)
    timestamp = datetime.now(timezone.utc).isoformat()
    
    entry = {"speaker": speaker, "text": text, "timestamp": timestamp}
    async with session.lock:
        session.transcript_history.append(entry)
        if len(session.transcript_history) > 50:
            session.transcript_history = session.transcript_history[-50:]
    
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
        
        for endpoint in [f"{MAS_ORCHESTRATOR_URL}/voice/memory/log", f"{MAS_ORCHESTRATOR_URL}/voice/feedback"]:
            try:
                resp = await client.post(endpoint, json=payload)
                if resp.status_code in (200, 201, 202):
                    return
            except:
                continue
                
    except Exception as e:
        logger.debug(f"Memory clone error (non-critical): {e}")

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
        moshi_available = "426" in str(e)

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
        "version": "5.1.0-event-stream",
        "moshi_available": moshi_available,
        "architecture": "moshi_full_duplex_with_mas_event_stream",
        "event_poll_interval": MAS_EVENT_POLL_INTERVAL
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
    
    import urllib.parse
    params = urllib.parse.urlencode({
        "text_prompt": MYCA_PERSONA,
        "voice_prompt": "NATF2.pt",
        "audio_temperature": "0.7",
        "text_temperature": "0.7"
    })
    
    event_task = None
    
    try:
        async with aiohttp.ClientSession() as aio:
            async with aio.ws_connect(f"{MOSHI_WS_URL}?{params}") as moshi:
                # Handshake
                hs = await asyncio.wait_for(moshi.receive(), 30)
                
                handshake_ok = False
                if hs.type == aiohttp.WSMsgType.BINARY and hs.data == b'\x00':
                    handshake_ok = True
                elif hs.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(hs.data)
                        if data.get("type") == "connected":
                            handshake_ok = True
                    except:
                        pass
                
                if not handshake_ok:
                    await websocket.send_json({"type": "error", "message": "Moshi handshake failed"})
                    return
                
                await websocket.send_bytes(b'\x00')
                logger.info(f"[{session_id[:8]}] Full-duplex bridge + event stream active")
                
                # Start MAS event polling loop
                event_task = asyncio.create_task(mas_event_loop(s, moshi, websocket))
                
                last_user_text = ""
                last_myca_text = ""
                
                async def moshi_to_browser():
                    nonlocal last_myca_text
                    try:
                        async for msg in moshi:
                            if msg.type == aiohttp.WSMsgType.BINARY and len(msg.data) > 0:
                                kind = msg.data[0]
                                
                                if kind == 1:  # Audio
                                    await websocket.send_bytes(msg.data)
                                
                                elif kind == 2:  # Text
                                    text = msg.data[1:].decode("utf-8", errors="ignore")
                                    await websocket.send_json({"type": "text", "text": text})
                                    
                                    normalized = normalize(text)
                                    if normalized and normalized != last_myca_text:
                                        last_myca_text = normalized
                                        await clone_to_mas_memory(s, "myca", normalized)
                                
                            elif msg.type == aiohttp.WSMsgType.TEXT:
                                await websocket.send_text(msg.data)
                                
                    except Exception as e:
                        logger.error(f"Moshi->Browser error: {e}")
                
                async def browser_to_moshi():
                    nonlocal last_user_text
                    try:
                        while True:
                            data = await websocket.receive()
                            
                            if "bytes" in data:
                                await moshi.send_bytes(data["bytes"])
                            
                            elif "text" in data:
                                try:
                                    payload = json.loads(data["text"])
                                    text = normalize(payload.get("text", ""))
                                    
                                    if text and text != last_user_text:
                                        last_user_text = text
                                        await clone_to_mas_memory(s, "user", text)
                                    
                                    if payload.get("forward_to_moshi", False) and text:
                                        await moshi.send_bytes(b"\x02" + text.encode("utf-8"))
                                        
                                except json.JSONDecodeError:
                                    pass
                                    
                    except WebSocketDisconnect:
                        logger.info(f"[{session_id[:8]}] Browser disconnected")
                    except Exception as e:
                        logger.error(f"Browser->Moshi error: {e}")
                
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
    finally:
        if event_task:
            event_task.cancel()

@app.get("/session/{session_id}/history")
async def get_session_history(session_id: str):
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

