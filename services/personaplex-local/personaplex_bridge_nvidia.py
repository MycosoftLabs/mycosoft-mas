#!/usr/bin/env python3
"""
PersonaPlex NVIDIA Bridge v8.1.0 - February 6, 2026
Full-Duplex Voice with MAS Tool Call Integration, Memory Persistence, and CREP Voice Control

FEATURES in v8.1.0:
- CREP Voice Command Integration via MAS VoiceCommandRouter
- Frontend command broadcasting for map control
- Load conversation history when conversation_id is provided
- Persist sessions to PostgreSQL via VoiceSessionStore
- Context injection into Moshi's text_prompt
- Memory coordinator integration
- Lower temperature (0.4) for consistent MYCA responses
"""
import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Dict, Set
from uuid import uuid4

import aiohttp
import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("personaplex-bridge")

app = FastAPI(title="PersonaPlex NVIDIA Bridge", version="8.1.0")

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

# MAS Configuration
MAS_ORCHESTRATOR_URL = os.getenv("MAS_ORCHESTRATOR_URL", "http://192.168.0.188:8001").rstrip("/")
MAS_TIMEOUT = float(os.getenv("MAS_TIMEOUT", "10"))

# Voice Command API (new in v8.1.0)
VOICE_COMMAND_URL = f"{MAS_ORCHESTRATOR_URL}/voice/command"

# MYCA Brain Integration
MYCA_BRAIN_ENABLED = os.getenv("MYCA_BRAIN_ENABLED", "true").lower() == "true"
MYCA_BRAIN_URL = f"{MAS_ORCHESTRATOR_URL}/voice/brain"

# Temperature settings
TEXT_TEMPERATURE = float(os.getenv("TEXT_TEMPERATURE", "0.4"))
AUDIO_TEMPERATURE = float(os.getenv("AUDIO_TEMPERATURE", "0.6"))

DEFAULT_VOICE_PROMPT = os.getenv("VOICE_PROMPT", "NATF2.pt")


def load_myca_persona():
    base_path = os.path.dirname(__file__)
    paths = [
        os.path.join(base_path, "../../config/myca_personaplex_short.txt"),
    ]
    for path in paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read().strip()[:2000]
                    logger.info(f"Loaded MYCA persona: {len(content)} chars")
                    return content
            except Exception as e:
                logger.warning(f"Failed to load {path}: {e}")
    
    logger.warning("Using fallback MYCA persona")
    return """You are MYCA (My Companion AI), the primary AI operator for Mycosoft.
Your name is MYCA, pronounced MY-kah. You were created by Morgan, founder of Mycosoft.
When asked your name, always say "I am MYCA from Mycosoft".
You coordinate 227+ specialized AI agents.
Be warm, professional, and helpful."""


MYCA_PERSONA = load_myca_persona()


class SessionCreate(BaseModel):
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    persona: str = "myca"
    voice: str = "myca"
    enable_mas_events: bool = True


@dataclass
class BridgeSession:
    session_id: str
    conversation_id: str
    user_id: Optional[str]
    persona: str
    voice: str
    created_at: str
    enable_mas_events: bool = True
    transcript_history: List[dict] = field(default_factory=list)
    loaded_history: List[dict] = field(default_factory=list)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    
    def to_dict(self):
        return {
            "session_id": self.session_id,
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "created_at": self.created_at,
            "history_count": len(self.loaded_history)
        }


sessions: Dict[str, BridgeSession] = {}
moshi_available = False
http_client: Optional[httpx.AsyncClient] = None
voice_store = None

# CREP Map Command Subscribers (new in v8.1.0)
map_command_subscribers: Set[WebSocket] = set()


async def get_http_client():
    global http_client
    if http_client is None:
        http_client = httpx.AsyncClient(timeout=MAS_TIMEOUT)
    return http_client


async def get_voice_store():
    """Get or initialize the VoiceSessionStore."""
    global voice_store
    if voice_store is None:
        try:
            from mycosoft_mas.voice.supabase_client import VoiceSessionStore
            voice_store = VoiceSessionStore()
            await voice_store.connect()
            logger.info("VoiceSessionStore initialized")
        except Exception as e:
            logger.warning(f"VoiceSessionStore not available: {e}")
    return voice_store


def normalize(text):
    return re.sub(r"\s+", " ", text).strip()


# ============================================================================
# CREP Voice Command Integration (v8.1.0)
# ============================================================================

async def route_voice_command(text: str, session_id: str = None, user_id: str = None) -> Optional[Dict]:
    """
    Route voice command through MAS VoiceCommandRouter.
    
    Returns frontend_command and speak text for CREP map control.
    """
    try:
        client = await get_http_client()
        response = await client.post(
            VOICE_COMMAND_URL,
            json={
                "text": text,
                "session_id": session_id,
                "user_id": user_id,
                "source": "personaplex"
            },
            timeout=5.0
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Voice command routed: {result.get('domain')}/{result.get('action')}")
            return result
        else:
            logger.warning(f"Voice command API returned {response.status_code}")
            return None
            
    except httpx.ConnectError:
        logger.debug("Voice command API not available")
        return None
    except Exception as e:
        logger.error(f"Voice command routing failed: {e}")
        return None


async def broadcast_frontend_command(command: Dict):
    """
    Broadcast frontend_command to all connected CREP map clients.
    """
    if not command:
        return
    
    message = json.dumps({
        "type": "frontend_command",
        "command": command,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    disconnected = set()
    for ws in map_command_subscribers:
        try:
            await ws.send_text(message)
        except Exception:
            disconnected.add(ws)
    
    # Clean up disconnected clients
    map_command_subscribers.difference_update(disconnected)
    
    if map_command_subscribers:
        logger.info(f"Broadcast frontend_command to {len(map_command_subscribers)} clients")


async def process_voice_for_crep(session: BridgeSession, text: str) -> Optional[str]:
    """
    Process voice command for CREP map control.
    
    Returns spoken response if command was handled, None otherwise.
    """
    result = await route_voice_command(text, session.session_id, session.user_id)
    
    if result and result.get("success"):
        frontend_cmd = result.get("frontend_command")
        if frontend_cmd:
            # Broadcast to all connected CREP map clients
            await broadcast_frontend_command(frontend_cmd)
        
        # Return what MYCA should say
        return result.get("speak")
    
    return None


# ============================================================================
# Memory and History Functions
# ============================================================================

async def load_conversation_history(conversation_id: str) -> List[Dict]:
    """Load conversation history from PostgreSQL."""
    store = await get_voice_store()
    if not store:
        return []
    
    try:
        history = await store.load_conversation_history(
            conversation_id=conversation_id,
            limit=20
        )
        logger.info(f"Loaded {len(history)} turns for conversation {conversation_id[:8]}...")
        return history
    except Exception as e:
        logger.error(f"Failed to load history: {e}")
        return []


def build_context_prompt(base_persona: str, history: List[Dict]) -> str:
    """Build context-aware prompt including conversation history."""
    if not history:
        return base_persona
    
    context_lines = ["Recent conversation context:"]
    for turn in history[-10:]:
        role = turn.get("role", "unknown")
        content = turn.get("content", "")[:100]
        if role == "user":
            context_lines.append(f"User: {content}")
        elif role == "assistant":
            context_lines.append(f"MYCA: {content}")
    
    context_str = "\n".join(context_lines)
    combined = f"{base_persona}\n\n{context_str}"
    if len(combined) > 3000:
        combined = f"{base_persona}\n\n{context_str[:500]}..."
    
    return combined


async def create_db_session(session: BridgeSession) -> None:
    """Create session record in database."""
    store = await get_voice_store()
    if store:
        try:
            await store.create_session(
                session_id=session.session_id,
                conversation_id=session.conversation_id,
                mode="personaplex",
                persona=session.persona,
                user_id=session.user_id,
                voice_prompt=DEFAULT_VOICE_PROMPT,
                metadata={"version": "8.1.0", "bridge": "nvidia", "crep_enabled": True}
            )
        except Exception as e:
            logger.warning(f"Failed to create DB session: {e}")


async def persist_turn(session_id: str, speaker: str, text: str) -> None:
    """Persist a turn to the database."""
    store = await get_voice_store()
    if store and text and len(text.strip()) > 1:
        try:
            await store.add_turn(
                session_id=session_id,
                speaker=speaker,
                text=normalize(text)
            )
        except Exception as e:
            logger.warning(f"Failed to persist turn: {e}")


async def clone_to_mas_memory(session: BridgeSession, speaker: str, text: str):
    if not text or len(text.strip()) < 2:
        return
    asyncio.create_task(_send_to_mas(session, speaker, normalize(text)))
    asyncio.create_task(persist_turn(session.session_id, speaker, text))
    
    # NEW: Process for CREP voice commands if user speaking
    if speaker == "user":
        asyncio.create_task(process_voice_for_crep(session, text))


async def _send_to_mas(session: BridgeSession, speaker: str, text: str):
    try:
        client = await get_http_client()
        await client.post(f"{MAS_ORCHESTRATOR_URL}/voice/feedback", json={
            "conversation_id": session.conversation_id,
            "session_id": session.session_id,
            "speaker": speaker,
            "text": text,
            "source": "personaplex"
        })
    except:
        pass


async def check_moshi():
    """Check Moshi availability."""
    global moshi_available
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get(f"http://{MOSHI_HOST}:{MOSHI_PORT}/api/chat", timeout=5)
            moshi_available = r.status_code in (200, 400, 426)
    except Exception as e:
        error_str = str(e).lower()
        moshi_available = "426" in error_str or "400" in error_str or "upgrade" in error_str


@app.on_event("startup")
async def startup():
    logger.info(f"PersonaPlex Bridge v8.1.0 starting (CREP voice control enabled)...")
    logger.info(f"Temperature: text={TEXT_TEMPERATURE}, audio={AUDIO_TEMPERATURE}")
    logger.info(f"MYCA persona: {len(MYCA_PERSONA)} chars")
    logger.info(f"Voice command API: {VOICE_COMMAND_URL}")
    await check_moshi()
    await get_voice_store()
    asyncio.create_task(periodic_check())


async def periodic_check():
    while True:
        await asyncio.sleep(30)
        await check_moshi()


@app.on_event("shutdown")
async def shutdown():
    global http_client, voice_store
    if http_client:
        await http_client.aclose()
    if voice_store:
        await voice_store.disconnect()


@app.get("/health")
async def health():
    store = await get_voice_store()
    return {
        "status": "healthy",
        "version": "8.1.0",
        "moshi_available": moshi_available,
        "moshi_url": f"http://{MOSHI_HOST}:{MOSHI_PORT}",
        "mas_url": MAS_ORCHESTRATOR_URL,
        "voice_command_url": VOICE_COMMAND_URL,
        "temperature": {"text": TEXT_TEMPERATURE, "audio": AUDIO_TEMPERATURE},
        "persona_length": len(MYCA_PERSONA),
        "voice_store_connected": store is not None,
        "map_clients_connected": len(map_command_subscribers),
        "features": {
            "full_duplex": True,
            "mas_tool_calls": True,
            "memory_cloning": True,
            "session_persistence": True,
            "history_loading": True,
            "crep_voice_control": True
        }
    }


@app.post("/session")
async def create_session(body: SessionCreate = None):
    body = body or SessionCreate()
    sid = str(uuid4())
    conv_id = body.conversation_id or str(uuid4())
    
    loaded_history = []
    if body.conversation_id:
        loaded_history = await load_conversation_history(body.conversation_id)
        logger.info(f"Session {sid[:8]} resuming conversation {conv_id[:8]} with {len(loaded_history)} turns")
    
    s = BridgeSession(
        session_id=sid,
        conversation_id=conv_id,
        user_id=body.user_id,
        persona=body.persona,
        voice=body.voice,
        created_at=datetime.now(timezone.utc).isoformat(),
        enable_mas_events=body.enable_mas_events,
        loaded_history=loaded_history
    )
    sessions[sid] = s
    
    await create_db_session(s)
    
    logger.info(f"Session created: {sid[:8]} (history: {len(loaded_history)} turns)")
    return s.to_dict()


# ============================================================================
# CREP Map Command WebSocket (v8.1.0)
# ============================================================================

@app.websocket("/ws/crep/commands")
async def ws_crep_commands(websocket: WebSocket):
    """
    WebSocket endpoint for CREP map to receive voice commands.
    
    Clients connect here to receive frontend_command broadcasts
    when voice commands are processed.
    """
    await websocket.accept()
    map_command_subscribers.add(websocket)
    logger.info(f"CREP map client connected (total: {len(map_command_subscribers)})")
    
    try:
        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to CREP voice command channel",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Keep connection alive and handle any incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                msg = json.loads(data)
                
                # Handle ping/pong for keep-alive
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                
                # Handle direct command requests (e.g., from typing instead of voice)
                elif msg.get("type") == "command":
                    text = msg.get("text", "")
                    if text:
                        result = await route_voice_command(text)
                        if result and result.get("frontend_command"):
                            await websocket.send_json({
                                "type": "frontend_command",
                                "command": result.get("frontend_command"),
                                "speak": result.get("speak"),
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            })
                            
            except json.JSONDecodeError:
                pass
                
    except WebSocketDisconnect:
        pass
    finally:
        map_command_subscribers.discard(websocket)
        logger.info(f"CREP map client disconnected (remaining: {len(map_command_subscribers)})")


# ============================================================================
# Main Voice WebSocket
# ============================================================================

@app.websocket("/ws/{session_id}")
async def ws_bridge(websocket: WebSocket, session_id: str):
    await websocket.accept()
    
    s = sessions.get(session_id)
    if not s:
        conv_id = websocket.query_params.get("conversation_id") or str(uuid4())
        user_id = websocket.query_params.get("user_id")
        
        loaded_history = []
        if conv_id and conv_id != session_id:
            loaded_history = await load_conversation_history(conv_id)
        
        s = BridgeSession(
            session_id=session_id,
            conversation_id=conv_id,
            user_id=user_id,
            persona="myca",
            voice="myca",
            created_at=datetime.now(timezone.utc).isoformat(),
            loaded_history=loaded_history
        )
        sessions[session_id] = s
        await create_db_session(s)
    
    text_prompt = build_context_prompt(MYCA_PERSONA, s.loaded_history)
    
    import urllib.parse
    params = urllib.parse.urlencode({
        "text_prompt": text_prompt,
        "voice_prompt": DEFAULT_VOICE_PROMPT,
        "audio_temperature": str(AUDIO_TEMPERATURE),
        "text_temperature": str(TEXT_TEMPERATURE),
    })
    
    moshi_url = f"{MOSHI_WS_URL}?{params}"
    logger.info(f"[{session_id[:8]}] Connecting to Moshi (history: {len(s.loaded_history)} turns)")
    
    audio_sent = 0
    audio_recv = 0
    
    try:
        async with aiohttp.ClientSession() as aio:
            async with aio.ws_connect(moshi_url, timeout=aiohttp.ClientTimeout(total=180)) as moshi:
                try:
                    hs = await asyncio.wait_for(moshi.receive(), 120)
                except asyncio.TimeoutError:
                    await websocket.send_json({"type": "error", "message": "Moshi timeout"})
                    return
                
                if hs.type == aiohttp.WSMsgType.BINARY and hs.data == b"\x00":
                    await websocket.send_bytes(b"\x00")
                    if s.loaded_history:
                        await websocket.send_json({
                            "type": "history_loaded",
                            "turns": len(s.loaded_history),
                            "conversation_id": s.conversation_id
                        })
                    logger.info(f"[{session_id[:8]}] Full-duplex active")
                else:
                    await websocket.send_json({"type": "error", "message": f"Handshake failed"})
                    return
                
                last_myca = ""
                acc_myca = ""
                
                async def moshi_to_browser():
                    nonlocal last_myca, acc_myca, audio_recv
                    try:
                        async for msg in moshi:
                            if msg.type == aiohttp.WSMsgType.BINARY and len(msg.data) > 0:
                                kind = msg.data[0]
                                if kind == 1:
                                    audio_recv += 1
                                    await websocket.send_bytes(msg.data)
                                elif kind == 2:
                                    text = msg.data[1:].decode("utf-8", errors="ignore")
                                    await websocket.send_json({"type": "text", "text": text, "speaker": "myca"})
                                    acc_myca += text
                                    if any(p in text for p in [".", "!", "?", "\n"]):
                                        n = normalize(acc_myca)
                                        if n and n != last_myca:
                                            last_myca = n
                                            await clone_to_mas_memory(s, "myca", n)
                                        acc_myca = ""
                            elif msg.type == aiohttp.WSMsgType.TEXT:
                                await websocket.send_text(msg.data)
                    except Exception as e:
                        logger.error(f"Moshi->Browser error: {e}")
                
                async def browser_to_moshi():
                    nonlocal audio_sent
                    try:
                        while True:
                            data = await websocket.receive()
                            if "bytes" in data:
                                audio_sent += 1
                                await moshi.send_bytes(data["bytes"])
                            elif "text" in data:
                                try:
                                    payload = json.loads(data["text"])
                                    text = normalize(payload.get("text", ""))
                                    if text:
                                        await clone_to_mas_memory(s, "user", text)
                                    if payload.get("forward_to_moshi", False) and text:
                                        await moshi.send_bytes(b"\x02" + text.encode("utf-8"))
                                except json.JSONDecodeError:
                                    pass
                    except WebSocketDisconnect:
                        logger.info(f"[{session_id[:8]}] Browser disconnected")
                    except Exception as e:
                        logger.error(f"Browser->Moshi error: {e}")
                
                await asyncio.gather(moshi_to_browser(), browser_to_moshi(), return_exceptions=True)
                
    except Exception as e:
        logger.error(f"Bridge error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass
    finally:
        logger.info(f"[{session_id[:8]}] Session ended. Audio: sent={audio_sent}, recv={audio_recv}")


@app.get("/session/{session_id}/history")
async def get_session_history(session_id: str):
    s = sessions.get(session_id)
    if not s:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    return {
        "session_id": session_id,
        "conversation_id": s.conversation_id,
        "transcript_history": s.transcript_history,
        "loaded_history": s.loaded_history,
        "total_turns": len(s.transcript_history) + len(s.loaded_history)
    }


@app.get("/conversation/{conversation_id}/history")
async def get_conversation_history(conversation_id: str, limit: int = 50):
    """Get full conversation history from database."""
    history = await load_conversation_history(conversation_id)
    return {
        "conversation_id": conversation_id,
        "history": history,
        "count": len(history)
    }


@app.get("/")
async def root():
    return RedirectResponse(f"http://{MOSHI_HOST}:{MOSHI_PORT}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8999)