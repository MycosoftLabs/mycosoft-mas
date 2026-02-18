#!/usr/bin/env python3
"""
PersonaPlex NVIDIA Bridge v8.2.0 - February 13, 2026
Full-Duplex Voice: 100% Moshi STT + TTS (no edge-tts or other TTS fallback).

Voice path: User mic -> Moshi STT -> MAS Brain -> response text -> Moshi TTS -> speaker.
Bridge connects to Moshi at MOSHI_HOST:MOSHI_PORT (e.g. GPU node 192.168.0.190:8998).

FEATURES:
- Full PersonaPlex: speech-to-speech via Moshi only (NATF2 / Moshika female voice when using moshika model).
- CREP Voice Command Integration via MAS VoiceCommandRouter
- Load conversation history, persist sessions to PostgreSQL via VoiceSessionStore
- Context injection into Moshi text_prompt, memory coordinator integration
- Lower temperature (0.4) for consistent MYCA responses
"""
import sys
from pathlib import Path

# Add MAS repo to Python path for mycosoft_mas imports
MAS_REPO_PATH = Path(__file__).resolve().parent.parent.parent
if str(MAS_REPO_PATH) not in sys.path:
    sys.path.insert(0, str(MAS_REPO_PATH))

import asyncio
import json
import logging
import os
import re
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional, List, Dict, Set
from uuid import uuid4

import aiohttp
import httpx
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

# Import duplex session for full-duplex voice support
try:
    from mycosoft_mas.consciousness.duplex_session import create_duplex_session
    DUPLEX_AVAILABLE = True
except ImportError as e:
    logging.getLogger("personaplex-bridge").warning(f"Duplex session not available: {e}")
    DUPLEX_AVAILABLE = False
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel

# Suppress FastAPI on_event deprecation warning (lifespan refactor pending)
warnings.filterwarnings("ignore", message=".*on_event is deprecated.*")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("personaplex-bridge")

# Reduce httpx noise (health check polling)
logging.getLogger("httpx").setLevel(logging.WARNING)

app = FastAPI(title="PersonaPlex NVIDIA Bridge", version="8.2.0")

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

# Database configuration for VoiceSessionStore (MINDEX VM)
# Force DATABASE_URL to connect to memory schema on MINDEX
MINDEX_DATABASE_URL = "postgresql://mycosoft:REDACTED_DB_PASSWORD@192.168.0.189:5432/mindex"
os.environ["DATABASE_URL"] = MINDEX_DATABASE_URL
logger.info(f"Set DATABASE_URL for voice store: postgresql://mycosoft:****@192.168.0.189:5432/mindex")


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
    
    # Full-duplex support (Phase 1)
    duplex_session: Optional[Any] = None  # DuplexSession when available
    is_tts_playing: bool = False
    moshi_ws: Optional[Any] = None  # Reference to Moshi WebSocket for stop signal
    
    def to_dict(self):
        return {
            "session_id": self.session_id,
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "created_at": self.created_at,
            "history_count": len(self.loaded_history),
            "duplex_enabled": self.duplex_session is not None,
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
            logger.info("Initializing VoiceSessionStore...")
            from mycosoft_mas.voice.supabase_client import VoiceSessionStore
            voice_store = VoiceSessionStore()
            logger.info(f"VoiceSessionStore created, connecting to: {voice_store._url[:50]}...")
            connected = await voice_store.connect()
            if connected:
                logger.info("VoiceSessionStore connected successfully!")
            else:
                logger.error("VoiceSessionStore connect() returned False")
                voice_store = None
        except Exception as e:
            logger.error(f"VoiceSessionStore initialization failed: {type(e).__name__}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            voice_store = None
    return voice_store


def normalize(text):
    return re.sub(r"\s+", " ", text).strip()


# ============================================================================
# Full-Duplex Voice Support (Phase 1)
# ============================================================================

# VAD Configuration
VAD_ENERGY_THRESHOLD = float(os.getenv("VAD_ENERGY_THRESHOLD", "0.02"))
VAD_MIN_SPEECH_FRAMES = int(os.getenv("VAD_MIN_SPEECH_FRAMES", "3"))
VAD_COOLDOWN_FRAMES = int(os.getenv("VAD_COOLDOWN_FRAMES", "10"))

# Track VAD state per session
vad_states: Dict[str, Dict] = {}


def detect_speech_vad(audio_chunk: bytes, session_id: str) -> bool:
    """
    Detect voice activity in audio chunk with debounce.
    
    Uses energy-based detection with:
    - 3 consecutive frames above threshold (debounce)
    - Cooldown after barge-in to avoid repeated triggers
    
    Args:
        audio_chunk: Raw PCM audio bytes (16-bit signed, mono)
        session_id: Session ID for state tracking
    
    Returns:
        True if sustained speech detected (triggers barge-in)
    """
    # Initialize state for session
    if session_id not in vad_states:
        vad_states[session_id] = {
            "speech_frames": 0,
            "cooldown": 0,
        }
    
    state = vad_states[session_id]
    
    # Handle cooldown
    if state["cooldown"] > 0:
        state["cooldown"] -= 1
        return False
    
    # Calculate RMS energy
    try:
        samples = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32)
        samples = samples / 32768.0  # Normalize to [-1, 1]
        energy = np.sqrt(np.mean(samples ** 2))
    except Exception:
        return False
    
    # Check threshold with debounce
    if energy > VAD_ENERGY_THRESHOLD:
        state["speech_frames"] += 1
        if state["speech_frames"] >= VAD_MIN_SPEECH_FRAMES:
            logger.debug(f"[{session_id[:8]}] VAD: Speech detected (energy={energy:.4f})")
            state["cooldown"] = VAD_COOLDOWN_FRAMES  # Start cooldown
            state["speech_frames"] = 0
            return True
    else:
        state["speech_frames"] = 0
    
    return False


async def stop_moshi_tts(moshi_ws, session: BridgeSession):
    """
    Stop Moshi TTS playback immediately.
    
    This is called on barge-in to halt the current audio output.
    
    Protocol: Send a special "stop" signal to Moshi.
    For now, we close and reopen the connection or send an interrupt byte.
    
    Args:
        moshi_ws: The aiohttp WebSocket connection to Moshi
        session: The BridgeSession
    """
    session.is_tts_playing = False
    
    try:
        # Option 1: Send interrupt signal byte (if Moshi supports it)
        # The Moshi protocol uses byte 0x03 for stop/interrupt
        await moshi_ws.send_bytes(b"\x03")
        logger.info(f"[{session.session_id[:8]}] Sent TTS stop signal to Moshi")
    except Exception as e:
        logger.warning(f"[{session.session_id[:8]}] Failed to send TTS stop: {e}")


def start_tts_cooldown(session_id: str):
    """Start VAD cooldown after TTS to avoid self-detection."""
    if session_id in vad_states:
        vad_states[session_id]["cooldown"] = VAD_COOLDOWN_FRAMES
        vad_states[session_id]["speech_frames"] = 0


def cleanup_vad_state(session_id: str):
    """Clean up VAD state when session ends."""
    vad_states.pop(session_id, None)


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
                metadata={"version": "8.2.0", "bridge": "nvidia", "crep_enabled": True}
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
    
    # Process user speech: CREP commands + MAS Brain query
    if speaker == "user":
        asyncio.create_task(process_voice_for_crep(session, text))
        # Query MAS Brain for intelligent context and send events to frontend
        asyncio.create_task(process_with_mas_brain(session, text))


async def process_with_mas_brain(session: BridgeSession, user_text: str):
    """
    Query MAS Brain and send events to frontend for dashboard display.
    This runs in parallel with Moshi's response generation.
    """
    try:
        # Send "processing" event to frontend
        await send_mas_event_to_frontend(session.session_id, "tool_call", {
            "id": f"brain_{session.session_id[:8]}",
            "tool": "mas_brain_query",
            "query": user_text[:50],
            "status": "running"
        })
        
        # Query MAS Brain
        brain_response = await query_mas_brain(session, user_text)
        
        if brain_response:
            # Send tool call results
            for tc in brain_response.get("tool_calls", []):
                await send_mas_event_to_frontend(session.session_id, "tool_call", {
                    "id": tc.get("id", "unknown"),
                    "tool": tc.get("tool", "unknown"),
                    "query": tc.get("query", ""),
                    "result": tc.get("result"),
                    "status": "success"
                })
            
            # Send memory stats
            memory_stats = brain_response.get("memory_stats", {})
            if memory_stats:
                await send_mas_event_to_frontend(session.session_id, "memory", {
                    "reads": memory_stats.get("reads", 0),
                    "writes": memory_stats.get("writes", 0),
                    "context_size": memory_stats.get("context_size", 0)
                })
            
            # Send agent activity
            for agent in brain_response.get("agents_invoked", []):
                await send_mas_event_to_frontend(session.session_id, "agent_invoke", {
                    "agentId": agent.get("id", "unknown"),
                    "agentName": agent.get("name", "unknown"),
                    "action": agent.get("action", "invoked"),
                    "status": "completed"
                })
            
            # Send injection data (MAS Brain response text)
            response_text = brain_response.get("response", "")
            if response_text:
                await send_mas_event_to_frontend(session.session_id, "injection", {
                    "type": "brain_response",
                    "content": response_text[:200],
                    "status": "available"
                })
                
                # Full PersonaPlex: Send MAS response to frontend (text) and to Moshi for TTS only.
                # No edge-tts or other fallback — voice is 100% Moshi (STT + TTS).
                if session.session_id in voice_websockets:
                    frontend_ws = voice_websockets[session.session_id]
                    try:
                        # Send response as text to frontend for display (same format Moshi uses)
                        words = response_text.split()
                        for word in words:
                            await frontend_ws.send_json({
                                "type": "text",
                                "text": word + " ",
                                "speaker": "myca"
                            })
                        # Send response text to Moshi for TTS; Moshi streams audio (kind=1) back
                        # and moshi_to_browser() forwards it to the frontend.
                        if session.moshi_ws:
                            await session.moshi_ws.send_bytes(b"\x02" + response_text.encode("utf-8"))
                            logger.info(f"[{session.session_id[:8]}] Sent MAS response to Moshi for TTS: {len(response_text)} chars")
                        else:
                            logger.warning(f"[{session.session_id[:8]}] Moshi WebSocket not set; TTS skipped (full PersonaPlex requires Moshi)")
                        logger.info(f"[{session.session_id[:8]}] Sent MAS response to frontend: {response_text[:50]}...")
                    except Exception as e:
                        logger.error(f"Failed to send MAS response to frontend/Moshi: {e}")
            
            # Complete the brain query event
            await send_mas_event_to_frontend(session.session_id, "tool_call", {
                "id": f"brain_{session.session_id[:8]}",
                "tool": "mas_brain_query",
                "status": "success",
                "duration": brain_response.get("latency_ms", 0)
            })
        else:
            await send_mas_event_to_frontend(session.session_id, "tool_call", {
                "id": f"brain_{session.session_id[:8]}",
                "tool": "mas_brain_query",
                "status": "timeout"
            })
    except Exception as e:
        logger.warning(f"MAS Brain processing error: {e}")


async def _send_to_mas(session: BridgeSession, speaker: str, text: str):
    """Send feedback to MAS for logging."""
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


async def query_mas_brain(session: BridgeSession, user_text: str) -> Optional[dict]:
    """
    Query MAS Brain API for intelligent response, memory context, and tool calls.
    Returns structured response including tool_calls, memory_stats, etc.
    This enables the frontend to display MAS activity even in full-duplex mode.
    """
    if not MYCA_BRAIN_ENABLED:
        return None
    
    try:
        client = await get_http_client()
        response = await client.post(
            f"{MYCA_BRAIN_URL}/chat",
            json={
                "message": user_text,
                "user_id": session.user_id or "voice_user",
                "conversation_id": session.conversation_id,
                "session_id": session.session_id,
                "context": {
                    "source": "personaplex_voice",
                    "mode": "full_duplex",
                    "return_metadata": True
                }
            },
            timeout=30.0  # Allow time for MAS to process (increased for slower MAS responses)
        )
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"MAS Brain response: {len(data.get('response', ''))} chars, tool_calls: {len(data.get('tool_calls', []))}")
            return data
        else:
            logger.warning(f"MAS Brain returned {response.status_code}")
            return None
    except httpx.TimeoutException:
        logger.warning("MAS Brain query timed out")
        return None
    except Exception as e:
        logger.warning(f"MAS Brain query failed: {e}")
        return None


# Track WebSocket connections for sending MAS events
voice_websockets: Dict[str, WebSocket] = {}


async def send_mas_event_to_frontend(session_id: str, event_type: str, data: dict):
    """Send MAS event to frontend via WebSocket.
    
    The frontend expects:
    - msg.type === "mas_event"
    - msg.event is a MASEvent object with: id, type, source, message, timestamp, data
    """
    ws = voice_websockets.get(session_id)
    if ws:
        try:
            await ws.send_json({
                "type": "mas_event",
                "event": {
                    "id": data.get("id", f"evt_{datetime.now().timestamp()}"),
                    "type": event_type,  # tool_call, memory_write, memory_read, agent_invoke, system, feedback
                    "source": "personaplex_bridge",
                    "message": data.get("tool", data.get("agentName", event_type)),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "data": data
                }
            })
        except Exception:
            pass


async def check_moshi():
    """Check Moshi availability.

    Moshi (moshi.server) accepts WebSocket only. An HTTP GET may:
    - Return 200 or 426  (server fully up)
    - Close immediately / empty reply  (server starting or WS-only mode)
    - Refuse connection  (not started)

    Strategy: try HTTP first; if it raises a connection error but TCP connects,
    treat as available (server is up, just WS-only or still warming up).
    """
    global moshi_available
    prev = moshi_available
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get(f"http://{MOSHI_HOST}:{MOSHI_PORT}/", timeout=5)
            moshi_available = r.status_code in (200, 426)
    except (httpx.RemoteProtocolError, httpx.ReadError):
        # Server closed connection without an HTTP response — WebSocket-only mode.
        # Fall back to a raw TCP connect to confirm the port is open.
        try:
            import socket
            sock = socket.create_connection((MOSHI_HOST, MOSHI_PORT), timeout=3)
            sock.close()
            moshi_available = True   # TCP ok → Moshi is up
        except OSError:
            moshi_available = False
    except Exception:
        moshi_available = False
    # Only log state changes
    if prev != moshi_available:
        logger.info(f"Moshi server {'available' if moshi_available else 'unavailable'}")


@app.on_event("startup")
async def startup():
    logger.info(f"PersonaPlex Bridge v8.2.0 starting (full PersonaPlex, Moshi STT+TTS only)...")
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
        "version": "8.2.0",
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
    
    # Initialize DuplexSession for full-duplex voice support
    if DUPLEX_AVAILABLE:
        try:
            s.duplex_session = create_duplex_session(
                session_id=sid,
                conversation_id=conv_id,
                user_id=body.user_id,
                on_barge_in=lambda: logger.info(f"[{sid[:8]}] DuplexSession barge-in callback"),
                on_state_change=lambda state: logger.debug(f"[{sid[:8]}] DuplexSession state: {state}"),
            )
            logger.info(f"[{sid[:8]}] DuplexSession initialized")
        except Exception as e:
            logger.error(f"[{sid[:8]}] Failed to create DuplexSession: {e}")
            s.duplex_session = None
    
    sessions[sid] = s
    
    await create_db_session(s)
    
    logger.info(f"Session created: {sid[:8]} (history: {len(loaded_history)} turns, duplex: {s.duplex_session is not None})")
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
    
    # Register WebSocket for MAS events
    voice_websockets[session_id] = websocket
    
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
        
        # Initialize DuplexSession for full-duplex voice support
        if DUPLEX_AVAILABLE:
            try:
                s.duplex_session = create_duplex_session(
                    session_id=session_id,
                    conversation_id=conv_id,
                    user_id=user_id,
                    on_barge_in=lambda: logger.info(f"[{session_id[:8]}] DuplexSession barge-in callback"),
                    on_state_change=lambda state: logger.debug(f"[{session_id[:8]}] DuplexSession state: {state}"),
                )
                logger.info(f"[{session_id[:8]}] DuplexSession initialized")
            except Exception as e:
                logger.error(f"[{session_id[:8]}] Failed to create DuplexSession: {e}")
        
        sessions[session_id] = s
        await create_db_session(s)
    
    # Connect to Moshi's /api/chat with NO URL parameters.
    # Passing text_prompt as a URL param produces a 6000+ char URL which causes
    # Moshi's aiohttp server to silently hang after the WS upgrade (never sends handshake).
    # The MYCA persona and memory context are injected by MAS through the conversation
    # system — no need to pass them to Moshi's URL.
    moshi_url = MOSHI_WS_URL
    logger.info(f"[{session_id[:8]}] Connecting to Moshi (history: {len(s.loaded_history)} turns)")
    
    audio_sent = 0
    audio_recv = 0
    
    try:
        async with aiohttp.ClientSession() as aio:
            logger.info(f"[{session_id[:8]}] Opening WebSocket to Moshi: {moshi_url[:100]}...")
            # Explicitly set WebSocket headers to ensure proper upgrade
            headers = {
                'Connection': 'Upgrade',
                'Upgrade': 'websocket'
            }
            # No heartbeat — Moshi's WebSocket server doesn't respond to WS ping frames.
            try:
                async with aio.ws_connect(
                    moshi_url,
                    timeout=aiohttp.ClientTimeout(total=None, sock_connect=15, sock_read=300),
                    headers=headers,
                ) as moshi:
                    logger.info(f"[{session_id[:8]}] WebSocket opened, waiting for handshake...")
                    try:
                        hs = await asyncio.wait_for(moshi.receive(), 120)
                    # hs.data may be bytes, str, or an exception object — always use str() for logging
                        hs_data_repr = str(hs.data)[:100] if hasattr(hs, "data") else "N/A"
                        logger.info(f"[{session_id[:8]}] Handshake received: type={hs.type}, data={hs_data_repr}")
                    except (asyncio.TimeoutError, Exception) as timeout_err:
                        logger.error(f"[{session_id[:8]}] Handshake wait failed: {type(timeout_err).__name__}: {timeout_err}")
                        await websocket.send_json({"type": "error", "message": "Moshi handshake timeout — try again in a few seconds"})
                        return

                        # Accept either binary b"\x00" OR JSON {"type": "connected"} handshake from Moshi
                    handshake_ok = False
                    if hs.type == aiohttp.WSMsgType.BINARY and hs.data == b"\x00":
                        await websocket.send_bytes(b"\x00")
                        handshake_ok = True
                        logger.info(f"[{session_id[:8]}] Binary handshake accepted")
                    elif hs.type == aiohttp.WSMsgType.TEXT:
                        try:
                            import json
                            hs_data = json.loads(hs.data)
                            if hs_data.get("type") == "connected":
                                await websocket.send_bytes(b"\x00")
                                handshake_ok = True
                                logger.info(f"[{session_id[:8]}] JSON handshake accepted: {hs_data}")
                        except (json.JSONDecodeError, TypeError):
                            logger.error(f"[{session_id[:8]}] Invalid JSON handshake: {str(hs.data)[:100]}")
                    elif hs.type == aiohttp.WSMsgType.ERROR:
                        logger.error(f"[{session_id[:8]}] Moshi error frame: {type(hs.data).__name__}: {hs.data}")
                        await websocket.send_json({"type": "error", "message": f"Moshi error: {type(hs.data).__name__} — try again"})
                        return

                    if not handshake_ok:
                        data_repr = str(hs.data)[:80] if hasattr(hs, "data") else "N/A"
                        logger.error(f"[{session_id[:8]}] Handshake failed: type={hs.type}, data={data_repr}")
                        await websocket.send_json({"type": "error", "message": "Moshi handshake failed — try again"})
                        return

                    if s.loaded_history:
                        await websocket.send_json({
                            "type": "history_loaded",
                            "turns": len(s.loaded_history),
                            "conversation_id": s.conversation_id
                        })

                    logger.info(f"[{session_id[:8]}] Full-duplex active")

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
                                        s.is_tts_playing = True
                                        await websocket.send_bytes(msg.data)
                                    elif kind == 2:
                                        text = msg.data[1:].decode("utf-8", errors="ignore")
                                        await websocket.send_json({"type": "text", "text": text, "speaker": "myca"})
                                        if acc_myca and not acc_myca.endswith(' ') and not text.startswith((' ', '.', ',', '!', '?', ';', ':', "'", '"', ')')):
                                            acc_myca += ' '
                                        acc_myca += text
                                        if any(p in text for p in [".", "!", "?", "\n"]):
                                            n = normalize(acc_myca)
                                            if n and n != last_myca:
                                                last_myca = n
                                                await clone_to_mas_memory(s, "myca", n)
                                            acc_myca = ""
                                    elif kind == 0:
                                        s.is_tts_playing = False
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
                                    audio_bytes = data["bytes"]

                                    if s.is_tts_playing:
                                        if detect_speech_vad(audio_bytes, session_id):
                                            logger.info(f"[{session_id[:8]}] Barge-in detected via VAD")
                                            if s.duplex_session:
                                                s.duplex_session.barge_in()
                                            else:
                                                await stop_moshi_tts(moshi, s)
                                            try:
                                                await websocket.send_json({
                                                    "type": "barge_in",
                                                    "message": "User interrupted",
                                                    "timestamp": datetime.now(timezone.utc).isoformat()
                                                })
                                            except Exception:
                                                pass

                                    # MYCA Brain mode: do NOT send user audio to Moshi.
                                    # User transcript comes via user_transcript JSON; MAS Brain
                                    # responds and we send 0x02+text to Moshi for TTS only.
                                    # Otherwise Moshi generates its own "I'm Moshi" response.
                                    if not MYCA_BRAIN_ENABLED:
                                        await moshi.send_bytes(audio_bytes)
                                elif "text" in data:
                                    try:
                                        payload = json.loads(data["text"])
                                        text = normalize(payload.get("text", ""))
                                        if text:
                                            await clone_to_mas_memory(s, "user", text)
                                            if s.duplex_session:
                                                s.duplex_session.record_user_turn(text)
                                        if payload.get("forward_to_moshi", False) and text:
                                            await moshi.send_bytes(b"\x02" + text.encode("utf-8"))
                                        if payload.get("type") == "barge_in" or payload.get("interrupt"):
                                            logger.info(f"[{session_id[:8]}] Explicit barge-in from frontend")
                                            if s.duplex_session:
                                                s.duplex_session.barge_in(text)
                                            else:
                                                await stop_moshi_tts(moshi, s)
                                    except json.JSONDecodeError:
                                        pass
                        except WebSocketDisconnect:
                            logger.info(f"[{session_id[:8]}] Browser disconnected")
                        except RuntimeError as e:
                            if "disconnect" in str(e).lower() or "receive" in str(e).lower():
                                logger.info(f"[{session_id[:8]}] Browser WS already closed")
                            else:
                                logger.error(f"Browser->Moshi error: {type(e).__name__}: {e}")
                        except Exception as e:
                            logger.error(f"Browser->Moshi error: {type(e).__name__}: {e}")

                    s.moshi_ws = moshi
                    if s.duplex_session:
                        s.duplex_session.set_stop_tts_callback(lambda: stop_moshi_tts(moshi, s))
                    await asyncio.gather(moshi_to_browser(), browser_to_moshi(), return_exceptions=True)
            except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as conn_err:
                logger.error(f"[{session_id[:8]}] Moshi connection failed: {type(conn_err).__name__}: {conn_err}")
                await websocket.send_json({
                    "type": "error",
                    "message": f"Moshi unreachable at {MOSHI_HOST}:{MOSHI_PORT}. Ensure Moshi is running; run _start_voice_system.py to warm up.",
                })
                return
    except Exception as e:
        logger.error(f"Bridge error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass
    finally:
        # Clean up WebSocket registration and VAD state
        voice_websockets.pop(session_id, None)
        cleanup_vad_state(session_id)
        
        # Reset duplex session if available
        if s and s.duplex_session:
            s.duplex_session.reset()
        
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