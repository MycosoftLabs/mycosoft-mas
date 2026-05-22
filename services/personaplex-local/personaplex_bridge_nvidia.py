#!/usr/bin/env python3
"""
PersonaPlex NVIDIA Bridge v8.2.0 - February 13, 2026
Full-Duplex Voice: 100% Moshi STT + TTS (no edge-tts or other TTS fallback).

This module is the canonical realtime MYCA voice path: Browser -> PersonaPlex Bridge -> MAS Brain.
The website voice orchestrator adapts to the same MAS Brain API (POST /voice/brain/chat).

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

# Load .env from MAS repo root so MINDEX_DB_PASSWORD and other vars are available
try:
    from dotenv import load_dotenv
    load_dotenv(MAS_REPO_PATH / ".env")
    load_dotenv(MAS_REPO_PATH / ".env.local", override=True)  # local overrides
except ImportError:
    pass

from mycosoft_mas.voice.gpu_voice_profile import (
    PROFILE_RTX4080_16GB,
    apply_profile_env,
    detect_gpu_voice_profile,
    read_profile_marker,
    write_profile_marker,
)
import asyncio
import json
import logging
import os
import re
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional, List, Dict, Set
from urllib.parse import urlencode
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

# Import ConversationController for structured barge-in management
try:
    from mycosoft_mas.consciousness.conversation_control import (
        ConversationController,
        VoiceActivityDetector,
        create_conversation_controller,
    )
    CONVERSATION_CONTROLLER_AVAILABLE = True
except ImportError as e:
    logging.getLogger("personaplex-bridge").warning(
        f"ConversationController not available: {e}"
    )
    CONVERSATION_CONTROLLER_AVAILABLE = False
    ConversationController = None  # type: ignore

# TTS fallback: Moshi does not support kind 0x02 (text→TTS). Use edge-tts for MYCA speech.
try:
    _bridge_dir = Path(__file__).resolve().parent
    if str(_bridge_dir) not in sys.path:
        sys.path.insert(0, str(_bridge_dir))
    from tts_fallback import synthesize_to_opus as tts_synthesize_to_opus
    TTS_FALLBACK_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger("personaplex-bridge")
    logger.warning(f"TTS fallback not available: {e}")
    tts_synthesize_to_opus = None
    TTS_FALLBACK_AVAILABLE = False
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("personaplex-bridge")

# Reduce httpx noise (health check polling)
logging.getLogger("httpx").setLevel(logging.WARNING)

app = FastAPI(title="PersonaPlex Bridge", version="8.2.0")
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


def build_moshi_ws_url(voice_prompt: str) -> str:
    """Short voice_prompt query only — avoid long text_prompt URLs that hang Moshi."""
    return f"{MOSHI_WS_URL}?{urlencode({'voice_prompt': voice_prompt or DEFAULT_VOICE_PROMPT})}"

# MAS Configuration
MAS_ORCHESTRATOR_URL = os.getenv("MAS_ORCHESTRATOR_URL", "http://192.168.0.188:8001").rstrip("/")
MAS_TIMEOUT = float(os.getenv("MAS_TIMEOUT", "10"))

# Moshi handshake timeout (seconds). First connection triggers CUDA graph compilation (60-180s+).
# Increase for slow GPUs or first run. Run START_VOICE_SYSTEM.py to warm up before test-voice.
BRIDGE_MOSHI_HANDSHAKE_TIMEOUT = int(os.getenv("BRIDGE_MOSHI_HANDSHAKE_TIMEOUT", "240"))

# Voice Command API (new in v8.1.0)
VOICE_COMMAND_URL = f"{MAS_ORCHESTRATOR_URL}/voice/command"

# MYCA Brain Integration
MYCA_BRAIN_ENABLED = os.getenv("MYCA_BRAIN_ENABLED", "true").lower() == "true"
MYCA_BRAIN_URL = f"{MAS_ORCHESTRATOR_URL}/voice/brain"
SERVICE_TOKEN = (
    os.getenv("MYCA_INTERNAL_SERVICE_TOKEN")
    or os.getenv("MAS_INTERNAL_SERVICE_TOKEN")
    or os.getenv("MYCA_MAS_SERVICE_TOKEN")
    or ""
).strip()

# Temperature settings
TEXT_TEMPERATURE = float(os.getenv("TEXT_TEMPERATURE", "0.4"))
AUDIO_TEMPERATURE = float(os.getenv("AUDIO_TEMPERATURE", "0.6"))

DEFAULT_VOICE_PROMPT = os.getenv("VOICE_PROMPT", "NATF2.pt")
VOICE_PROMPT_MAP = {
    "myca": os.getenv("VOICE_PROMPT_MYCA", DEFAULT_VOICE_PROMPT),
    "moshika": os.getenv("VOICE_PROMPT_MOSHIKA", DEFAULT_VOICE_PROMPT),
}


def resolve_voice_prompt(voice_id: str) -> str:
    return VOICE_PROMPT_MAP.get((voice_id or "myca").lower(), DEFAULT_VOICE_PROMPT)

# Database configuration for VoiceSessionStore (MINDEX VM)
# Set MINDEX_DB_PASSWORD in MAS .env to enable voice session persistence
min_db_password = os.getenv("MINDEX_DB_PASSWORD", "")
if min_db_password:
    MINDEX_DATABASE_URL = f"postgresql://mycosoft:{min_db_password}@192.168.0.189:5432/mindex"
    os.environ.setdefault("DATABASE_URL", MINDEX_DATABASE_URL)
    logger.info("Set DATABASE_URL for voice store: postgresql://mycosoft:****@192.168.0.189:5432/mindex")
elif not os.getenv("DATABASE_URL"):
    logger.warning(
        "MINDEX_DB_PASSWORD not set; DATABASE_URL must be configured for voice store. "
        "Add MINDEX_DB_PASSWORD to MAS repo .env for session persistence."
    )


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
    voice_prompt: str = DEFAULT_VOICE_PROMPT
    enable_mas_events: bool = True
    transcript_history: List[dict] = field(default_factory=list)
    loaded_history: List[dict] = field(default_factory=list)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    
    # Full-duplex support (Phase 1)
    duplex_session: Optional[Any] = None  # DuplexSession when available
    is_tts_playing: bool = False
    tts_via_moshi: bool = False
    moshi_ws: Optional[Any] = None  # Reference to Moshi WebSocket for stop signal
    moshi_handshake_sent: bool = False
    local_stt_detector: Optional[Any] = None
    local_stt_busy: bool = False
    moshi_audio_since_speech: bool = False

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


try:
    from local_stt_turn import OpusTurnDetector, transcribe_pcm

    LOCAL_STT_AVAILABLE = True
except ImportError:
    OpusTurnDetector = None
    transcribe_pcm = None
    LOCAL_STT_AVAILABLE = False

USE_LOCAL_STT_4080 = os.getenv("MYCA_4080_LOCAL_STT", "false").lower() in ("1", "true", "yes")
FORCE_MOSHI_PERSONAPLEX = os.getenv("MYCA_FORCE_MOSHI", "true").lower() in ("1", "true", "yes")


def _use_local_stt_fallback() -> bool:
    if FORCE_MOSHI_PERSONAPLEX:
        return False
    if not USE_LOCAL_STT_4080 or not LOCAL_STT_AVAILABLE:
        return False
    profile = read_profile_marker(MAS_REPO_PATH)
    if profile and profile.get("profile_id") == PROFILE_RTX4080_16GB:
        return True
    if os.getenv("MYCA_GPU_VOICE_PROFILE", "").lower() == PROFILE_RTX4080_16GB:
        return True
    # Bridge may start without START_VOICE_SYSTEM marker/env — detect GPU directly.
    try:
        detected = detect_gpu_voice_profile()
        return detected.profile_id == PROFILE_RTX4080_16GB
    except Exception:
        return False


async def _handle_local_stt_turn(session: BridgeSession, pcm: np.ndarray) -> None:
    if session.local_stt_busy:
        return
    if session.moshi_audio_since_speech:
        session.moshi_audio_since_speech = False
        logger.info(f"[{session.session_id[:8]}] Moshi already replied — skip local STT")
        return
    session.local_stt_busy = True
    try:
        text = await asyncio.to_thread(transcribe_pcm, pcm)
        if not text or len(text.strip()) < 2:
            logger.debug(f"[{session.session_id[:8]}] Local STT: no text")
            return
        logger.info(f"[{session.session_id[:8]}] Local STT heard: {text[:120]}")
        await send_json_to_browser(session.session_id, {
            "type": "user_transcript",
            "text": text,
            "source": "local_stt",
        })
        await send_json_to_browser(session.session_id, {
            "type": "local_stt_status",
            "phase": "transcribed",
            "text": text[:120],
        })
        asyncio.create_task(_send_to_mas(session, "user", normalize(text)))
        asyncio.create_task(persist_turn(session.session_id, "user", text))
        asyncio.create_task(process_voice_for_crep(session, text))
        await process_with_mas_brain(session, text)
    finally:
        session.local_stt_busy = False


async def _startup_greeting_for_session(session_id: str) -> None:
    """Speak immediately on connect so the user hears MYCA without typing first."""
    try:
        from mycosoft_mas.voice.fast_reply import fast_voice_reply

        greeting = os.getenv(
            "MYCA_STARTUP_GREETING",
            fast_voice_reply("hello"),
        )
        packets = await speak_text_via_tts_fallback(session_id, greeting)
        logger.info(f"[{session_id[:8]}] Startup greeting TTS: {packets} audio packets")
    except Exception as ex:
        logger.warning(f"[{session_id[:8]}] Startup greeting failed: {ex}")


async def _run_local_stt_session(
    websocket: WebSocket,
    session_id: str,
    s: BridgeSession,
) -> tuple[int, int]:
    """
    RTX 4080 path: Moshi cpu-offload hits meta/cuda errors on voice-prompt init.
    Mic → faster-whisper → MAS brain → edge-tts. No Moshi WebSocket inference.
    """
    audio_sent = 0
    audio_recv = 0

    logger.info(
        f"[{session_id[:8]}] RTX 4080 local STT mode — skipping Moshi duplex "
        "(cpu-offload meta device bug)"
    )

    if OpusTurnDetector:
        s.local_stt_detector = OpusTurnDetector()

    if not s.moshi_handshake_sent:
        s.moshi_handshake_sent = True
        await send_bytes_to_browser(session_id, b"\x00")
        await send_json_to_browser(session_id, {
            "type": "moshi_ready",
            "session_id": session_id,
            "voice": s.voice,
            "voice_prompt": s.voice_prompt,
            "local_stt_mode": True,
        })

    asyncio.create_task(_startup_greeting_for_session(session_id))

    if s.loaded_history:
        await send_json_to_browser(session_id, {
            "type": "history_loaded",
            "turns": len(s.loaded_history),
            "conversation_id": s.conversation_id,
        })

    try:
        while True:
            data = await websocket.receive()
            if "bytes" in data:
                audio_sent += 1
                audio_bytes = data["bytes"]

                if s.is_tts_playing and detect_speech_vad(audio_bytes, session_id):
                    logger.info(f"[{session_id[:8]}] Barge-in detected via VAD")
                    s.is_tts_playing = False
                    if s.duplex_session:
                        s.duplex_session.barge_in()
                    try:
                        await send_json_to_browser(session_id, {
                            "type": "barge_in",
                            "message": "User interrupted",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })
                    except Exception:
                        pass

                if (
                    s.local_stt_detector
                    and not s.is_tts_playing
                    and len(audio_bytes) > 1
                    and audio_bytes[0] == 1
                ):
                    utterance_pcm = s.local_stt_detector.feed_opus(audio_bytes[1:])
                    if utterance_pcm is not None:
                        asyncio.create_task(_handle_local_stt_turn(s, utterance_pcm))
                    elif s.local_stt_detector.in_speech and audio_sent % 50 == 0:
                        await send_json_to_browser(session_id, {
                            "type": "local_stt_status",
                            "phase": "listening",
                            "speech_frames": s.local_stt_detector.speech_frames,
                        })

            elif "text" in data:
                try:
                    payload = json.loads(data["text"])
                    if payload.get("type") == "user_speech":
                        text = normalize(payload.get("text", ""))
                        if text:
                            await clone_to_mas_memory(s, "user", text)
                        continue

                    text = normalize(payload.get("text", ""))
                    if not text and payload.get("type") == "inject_feedback":
                        inj = payload.get("injection") or {}
                        text = normalize(inj.get("content", ""))
                    if text and payload.get("type") != "inject_feedback":
                        await clone_to_mas_memory(s, "user", text)
                        if s.duplex_session:
                            s.duplex_session.record_user_turn(text)

                    if payload.get("type") == "inject_feedback" and text:
                        s.is_tts_playing = True
                        try:
                            await send_json_to_browser(
                                session_id,
                                {"type": "text", "text": text, "speaker": "myca"},
                            )
                            packets = await speak_text_via_tts_fallback(session_id, text)
                            audio_recv += packets
                        finally:
                            s.is_tts_playing = False

                    if payload.get("type") in ("barge_in", "interrupt"):
                        s.is_tts_playing = False
                        if s.duplex_session:
                            s.duplex_session.barge_in(text if text else None)
                except json.JSONDecodeError:
                    pass
    except WebSocketDisconnect:
        logger.info(f"[{session_id[:8]}] Browser disconnected")
    except RuntimeError as e:
        if "disconnect" in str(e).lower() or "receive" in str(e).lower():
            logger.info(f"[{session_id[:8]}] Browser WS already closed")
        else:
            logger.error(f"Local STT session error: {type(e).__name__}: {e}")
    except Exception as e:
        logger.error(f"Local STT session error: {type(e).__name__}: {e}")

    return audio_sent, audio_recv


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


async def speak_text_via_tts_fallback(session_id: str, text: str) -> int:
    """
    Synthesize MYCA speech locally (edge-tts → Opus) and send 0x01 packets to the browser.
    Canonical path per FULL_PERSONAPLEX / VOICE_TOPOLOGY_LOCKED — no cloud browser STT.
    """
    if not text or not text.strip():
        return 0
    if session_id not in voice_websockets:
        logger.warning(f"[{session_id[:8]}] No browser WS for brain TTS")
        return 0

    async with _tts_session_lock(session_id):
        session = sessions.get(session_id)
        packet_count = 0
        start_tts_cooldown(session_id)
        if session:
            session.is_tts_playing = True
            session.tts_via_moshi = False
            if session.local_stt_detector:
                session.local_stt_detector.reset()
        try:
            await send_json_to_browser(session_id, {"type": "text", "text": text, "speaker": "myca"})
            if TTS_FALLBACK_AVAILABLE and tts_synthesize_to_opus:
                packets = await tts_synthesize_to_opus(text)
                if packets:
                    await send_json_to_browser(session_id, {
                        "type": "tts_stream_start",
                        "packets": len(packets),
                    })
                for pkt in packets:
                    if await send_bytes_to_browser(session_id, b"\x01" + pkt):
                        packet_count += 1
                if packet_count == 0:
                    logger.error(
                        f"[{session_id[:8]}] edge-tts produced 0 Opus packets for brain TTS"
                    )
                else:
                    logger.info(
                        f"[{session_id[:8]}] TTS sent {packet_count}/{len(packets)} Opus packets"
                    )
            else:
                logger.warning(f"[{session_id[:8]}] TTS fallback unavailable for brain response")
        except Exception as e:
            logger.warning(f"[{session_id[:8]}] speak_text_via_tts_fallback failed: {e}")
        finally:
            if session:
                session.is_tts_playing = False
        return packet_count


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
            headers=_mas_service_headers(),
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
                voice_prompt=session.voice_prompt or DEFAULT_VOICE_PROMPT,
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


async def process_with_mas_brain(
    session: BridgeSession,
    user_text: str,
    force_spoken_reply: bool = False,
):
    """
    Speak immediately via edge-tts, then enrich UI from MAS brain in the background.
    Never block audio on slow harness/Nemotron (was 8s+ silence).
    """
    from mycosoft_mas.voice.fast_reply import fast_voice_reply

    try:
        await send_mas_event_to_frontend(session.session_id, "tool_call", {
            "id": f"brain_{session.session_id[:8]}",
            "tool": "mas_brain_query",
            "query": user_text[:50],
            "status": "running"
        })

        response_text = fast_voice_reply(user_text)
        logger.info(
            f"[{session.session_id[:8]}] Immediate voice reply ({len(response_text)} chars)"
        )

        await send_mas_event_to_frontend(session.session_id, "injection", {
            "type": "brain_response",
            "content": response_text,
            "status": "available"
        })

        if _use_local_stt_fallback():
            spoken = await speak_text_via_tts_fallback(session.session_id, response_text)
            if spoken:
                logger.info(f"[{session.session_id[:8]}] Immediate TTS: {spoken} Opus packets")
            else:
                logger.error(f"[{session.session_id[:8]}] Immediate TTS produced 0 packets")
        else:
            # In Moshi mode, explicit text user_speech turns still need a spoken reply path.
            # Try Moshi text injection first; if unavailable, fall back to local TTS packets.
            if force_spoken_reply and response_text:
                try:
                    if session.moshi_ws and not session.moshi_ws.closed:
                        await session.moshi_ws.send_bytes(b"\x02" + response_text.encode("utf-8"))
                        logger.info(
                            f"[{session.session_id[:8]}] Sent 0x02 text frame to Moshi for spoken brain reply"
                        )
                except Exception as ex:
                    logger.warning(
                        f"[{session.session_id[:8]}] Moshi 0x02 speech failed, falling back to edge-tts: {ex}"
                    )
                # Always emit a guaranteed spoken reply path for explicit text turns.
                spoken = await speak_text_via_tts_fallback(session.session_id, response_text)
                logger.info(
                    f"[{session.session_id[:8]}] Brain TTS fallback packets={spoken}"
                )
            else:
                logger.info(
                    f"[{session.session_id[:8]}] Moshi PersonaPlex mode — brain text only, "
                    "Moshi handles STT+TTS (no edge-tts)"
                )

        await send_mas_event_to_frontend(session.session_id, "tool_call", {
            "id": f"brain_{session.session_id[:8]}",
            "tool": "mas_brain_query",
            "status": "success",
            "duration": 0
        })

        # Background: MAS brain/harness for memory + richer UI (no blocking TTS)
        asyncio.create_task(_enrich_mas_brain_ui(session, user_text, response_text))
    except Exception as e:
        logger.warning(f"MAS Brain processing error: {type(e).__name__}: {e}")
        if _use_local_stt_fallback():
            try:
                fallback = fast_voice_reply(user_text)
                await speak_text_via_tts_fallback(session.session_id, fallback)
            except Exception as tts_exc:
                logger.warning(f"Emergency TTS fallback failed: {tts_exc}")


async def _enrich_mas_brain_ui(
    session: BridgeSession, user_text: str, already_spoken: str
) -> None:
    """Fetch MAS brain metadata for dashboard; do not block initial TTS."""
    brain_timeout = float(os.getenv("BRIDGE_BRAIN_TIMEOUT_SEC", "8"))
    try:
        brain_response = await asyncio.wait_for(
            query_mas_brain(session, user_text),
            timeout=brain_timeout,
        )
        if not brain_response:
            return
        for tc in brain_response.get("tool_calls", []):
            await send_mas_event_to_frontend(session.session_id, "tool_call", {
                "id": tc.get("id", "unknown"),
                "tool": tc.get("tool", "unknown"),
                "query": tc.get("query", ""),
                "result": tc.get("result"),
                "status": "success"
            })
        memory_stats = brain_response.get("memory_stats", {})
        if memory_stats:
            await send_mas_event_to_frontend(session.session_id, "memory", {
                "reads": memory_stats.get("reads", 0),
                "writes": memory_stats.get("writes", 0),
                "context_size": memory_stats.get("context_size", 0)
            })
        for agent in brain_response.get("agents_invoked", []):
            await send_mas_event_to_frontend(session.session_id, "agent_invoke", {
                "agentId": agent.get("id", "unknown"),
                "agentName": agent.get("name", "unknown"),
                "action": agent.get("action", "invoked"),
                "status": "completed"
            })
        brain_text = (brain_response.get("response") or "").strip()
        if brain_text and brain_text != already_spoken:
            await send_mas_event_to_frontend(session.session_id, "injection", {
                "type": "brain_response",
                "content": brain_text,
                "status": "available"
            })
    except asyncio.TimeoutError:
        logger.debug(f"[{session.session_id[:8]}] MAS brain enrich timed out (non-blocking)")
    except Exception as e:
        logger.debug(f"[{session.session_id[:8]}] MAS brain enrich failed: {e}")


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
        }, headers=_mas_service_headers(session))
    except Exception:
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
                "use_harness": True,
                "include_memory_context": True,
            },
            headers=_mas_service_headers(session),
            timeout=8.0,
        )
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"MAS Brain response: {len(data.get('response', ''))} chars, tool_calls: {len(data.get('tool_calls', []))}")
            return data
        else:
            snippet = (response.text or "")[:800].replace("\n", " ")
            logger.warning(f"MAS Brain returned {response.status_code}: {snippet}")
            return None
    except httpx.TimeoutException:
        logger.warning("MAS Brain query timed out")
        return None
    except Exception as e:
        logger.warning(f"MAS Brain query failed: {e}")
        return None


# Track WebSocket connections for sending MAS events
voice_websockets: Dict[str, WebSocket] = {}
# Serialize all browser-bound sends — concurrent moshi_to_browser + TTS tasks drop packets without this.
browser_send_locks: Dict[str, asyncio.Lock] = {}
_tts_session_locks: Dict[str, asyncio.Lock] = {}


def _browser_send_lock(session_id: str) -> asyncio.Lock:
    lock = browser_send_locks.get(session_id)
    if lock is None:
        lock = asyncio.Lock()
        browser_send_locks[session_id] = lock
    return lock


def _tts_session_lock(session_id: str) -> asyncio.Lock:
    lock = _tts_session_locks.get(session_id)
    if lock is None:
        lock = asyncio.Lock()
        _tts_session_locks[session_id] = lock
    return lock


async def send_json_to_browser(session_id: str, payload: dict) -> bool:
    ws = voice_websockets.get(session_id)
    if not ws:
        return False
    async with _browser_send_lock(session_id):
        try:
            await ws.send_json(payload)
            return True
        except Exception as e:
            logger.warning(f"[{session_id[:8]}] send_json failed: {type(e).__name__}: {e}")
            return False


async def send_bytes_to_browser(session_id: str, data: bytes) -> bool:
    ws = voice_websockets.get(session_id)
    if not ws:
        return False
    async with _browser_send_lock(session_id):
        try:
            await ws.send_bytes(data)
            return True
        except Exception as e:
            logger.warning(f"[{session_id[:8]}] send_bytes failed: {type(e).__name__}: {e}")
            return False


async def send_text_to_browser(session_id: str, text: str) -> bool:
    ws = voice_websockets.get(session_id)
    if not ws:
        return False
    async with _browser_send_lock(session_id):
        try:
            await ws.send_text(text)
            return True
        except Exception as e:
            logger.warning(f"[{session_id[:8]}] send_text failed: {type(e).__name__}: {e}")
            return False


def _mas_service_headers(session: Optional[BridgeSession] = None) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    if SERVICE_TOKEN:
        headers["X-MYCA-Service-Token"] = SERVICE_TOKEN
        headers["X-MYCOSOFT-Service-Token"] = SERVICE_TOKEN
    if session:
        headers["X-MYCA-Verified-User-Id"] = session.user_id or "voice_user"
        headers["X-MYCA-Verified-Email"] = ""
        headers["X-MYCA-Verified-Role"] = "user"
        headers["X-MYCA-Auth-Trust-Level"] = "service"
    return headers


async def send_mas_event_to_frontend(session_id: str, event_type: str, data: dict):
    """Send MAS event to frontend via WebSocket.
    
    The frontend expects:
    - msg.type === "mas_event"
    - msg.event is a MASEvent object with: id, type, source, message, timestamp, data
    """
    await send_json_to_browser(session_id, {
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


async def check_moshi():
    """Check Moshi availability.

    Moshi (moshi.server) is WebSocket-first; HTTP GET to / may return 200, 426,
    404, 405, or close without a response. Any HTTP response or open TCP port
    means the server is up.
    """
    global moshi_available
    prev = moshi_available
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get(f"http://{MOSHI_HOST}:{MOSHI_PORT}/", timeout=5)
            # Any HTTP response (200, 426, 404, 405, etc.) means Moshi is up
            moshi_available = True
    except (httpx.RemoteProtocolError, httpx.ReadError):
        # Server closed without HTTP response — WebSocket-only; confirm TCP.
        try:
            import socket
            sock = socket.create_connection((MOSHI_HOST, MOSHI_PORT), timeout=3)
            sock.close()
            moshi_available = True
        except OSError:
            moshi_available = False
    except (httpx.ConnectError, httpx.TimeoutException):
        # No response or timeout — try TCP once to avoid false negative during startup
        try:
            import socket
            sock = socket.create_connection((MOSHI_HOST, MOSHI_PORT), timeout=3)
            sock.close()
            moshi_available = True
        except OSError:
            moshi_available = False
    except Exception:
        moshi_available = False
    if prev != moshi_available:
        logger.info(f"Moshi server {'available' if moshi_available else 'unavailable'}")


@app.on_event("startup")
async def startup():
    profile = detect_gpu_voice_profile()
    apply_profile_env(profile)
    try:
        write_profile_marker(MAS_REPO_PATH, profile)
    except Exception as exc:
        logger.warning(f"Could not write GPU profile marker: {exc}")

    mode = "PersonaPlex Moshi full-duplex" if not _use_local_stt_fallback() else "local STT + edge-tts"
    logger.info(f"PersonaPlex Bridge v8.2.0 starting ({mode})...")
    logger.info(
        f"GPU profile: {profile.profile_id} ({profile.gpu_name}, "
        f"{profile.vram_total_gb} GB, cpu_offload={profile.cpu_offload})"
    )
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
    # Use cached voice_store only - do NOT trigger get_voice_store() here.
    # Health must respond quickly; DB connect can block for seconds.
    store = voice_store
    gpu_profile = read_profile_marker(MAS_REPO_PATH)
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
        "gpu_profile": gpu_profile,
        "local_stt_mode": _use_local_stt_fallback(),
        "features": {
            "full_duplex": not _use_local_stt_fallback(),
            "local_stt_4080": _use_local_stt_fallback(),
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
        voice_prompt=resolve_voice_prompt(body.voice),
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
        
        voice_id = websocket.query_params.get("voice") or "moshika"
        s = BridgeSession(
            session_id=session_id,
            conversation_id=conv_id,
            user_id=user_id,
            persona="myca",
            voice=voice_id,
            voice_prompt=resolve_voice_prompt(voice_id),
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
    
    local_stt_mode = _use_local_stt_fallback()

    # Tell browser bridge is up; Moshi CUDA handshake (0x00) forwarded only after Moshi sends it.
    await send_json_to_browser(session_id, {
        "type": "bridge_ready",
        "session_id": session_id,
        "moshi_pending": not local_stt_mode,
        "local_stt_mode": local_stt_mode,
        "voice": s.voice,
        "voice_prompt": s.voice_prompt,
    })
    logger.info(
        f"[{session_id[:8]}] bridge_ready sent "
        f"(voice={s.voice}, local_stt={local_stt_mode})"
    )

    audio_sent = 0
    audio_recv = 0

    if local_stt_mode:
        try:
            audio_sent, audio_recv = await _run_local_stt_session(websocket, session_id, s)
        except Exception as e:
            logger.error(f"Bridge error (local STT): {e}")
            try:
                await send_json_to_browser(session_id, {"type": "error", "message": str(e)})
            except Exception:
                pass
        finally:
            voice_websockets.pop(session_id, None)
            browser_send_locks.pop(session_id, None)
            _tts_session_locks.pop(session_id, None)
            cleanup_vad_state(session_id)
            if s and s.duplex_session:
                s.duplex_session.reset()
            logger.info(
                f"[{session_id[:8]}] Session ended (local STT). "
                f"Audio: sent={audio_sent}, recv={audio_recv}"
            )
        return

    moshi_url = build_moshi_ws_url(s.voice_prompt)
    logger.info(f"[{session_id[:8]}] Connecting to Moshi (history: {len(s.loaded_history)} turns)")
    
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
                    logger.info(f"[{session_id[:8]}] Moshi WebSocket connected, waiting for voice-prompt handshake")

                    if s.loaded_history:
                        await send_json_to_browser(session_id, {
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
                                        s.tts_via_moshi = True
                                        if s.local_stt_detector and s.local_stt_detector.in_speech:
                                            s.moshi_audio_since_speech = True
                                        await send_bytes_to_browser(session_id, msg.data)
                                    elif kind == 2:
                                        text = msg.data[1:].decode("utf-8", errors="ignore")
                                        await send_json_to_browser(session_id, {"type": "text", "text": text, "speaker": "myca"})
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
                                        if not s.moshi_handshake_sent:
                                            s.moshi_handshake_sent = True
                                            await send_bytes_to_browser(session_id, b"\x00")
                                            await send_json_to_browser(session_id, {
                                                "type": "moshi_ready",
                                                "session_id": session_id,
                                                "voice": s.voice,
                                                "voice_prompt": s.voice_prompt,
                                            })
                                            logger.info(f"[{session_id[:8]}] Moshi CUDA handshake forwarded to browser")
                                elif msg.type == aiohttp.WSMsgType.TEXT:
                                    await send_text_to_browser(session_id, msg.data)
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
                                        # Disabled by default in Moshi path: VAD runs on Opus packets here and
                                        # can self-trigger false barge-ins that send 0x03 and cut off replies.
                                        vad_barge_in_enabled = os.getenv(
                                            "MYCA_ENABLE_VAD_BARGE_IN", "false"
                                        ).lower() in ("1", "true", "yes")
                                        if vad_barge_in_enabled and detect_speech_vad(
                                            audio_bytes[1:] if len(audio_bytes) > 1 else audio_bytes,
                                            session_id,
                                        ):
                                            logger.info(f"[{session_id[:8]}] Barge-in detected via VAD")
                                            s.is_tts_playing = False
                                            # edge-tts greeting/replies must not send 0x03 to Moshi — kills the WS.
                                            if s.tts_via_moshi:
                                                if s.duplex_session:
                                                    s.duplex_session.barge_in()
                                                else:
                                                    await stop_moshi_tts(moshi, s)
                                            try:
                                                await send_json_to_browser(session_id, {
                                                    "type": "barge_in",
                                                    "message": "User interrupted",
                                                    "timestamp": datetime.now(timezone.utc).isoformat()
                                                })
                                            except Exception:
                                                pass

                                    if _use_local_stt_fallback() and s.local_stt_detector is None and OpusTurnDetector:
                                        s.local_stt_detector = OpusTurnDetector()
                                    if (
                                        _use_local_stt_fallback()
                                        and s.local_stt_detector
                                        and len(audio_bytes) > 1
                                        and audio_bytes[0] == 1
                                    ):
                                        utterance_pcm = s.local_stt_detector.feed_opus(audio_bytes[1:])
                                        if s.local_stt_detector.in_speech:
                                            s.moshi_audio_since_speech = False
                                        if utterance_pcm is not None:
                                            asyncio.create_task(_handle_local_stt_turn(s, utterance_pcm))

                                    # Forward mic Opus to Moshi when native duplex may still respond.
                                    await moshi.send_bytes(audio_bytes)
                                elif "text" in data:
                                    try:
                                        payload = json.loads(data["text"])
                                        if payload.get("type") == "user_speech":
                                            text = normalize(payload.get("text", ""))
                                            if text:
                                                await process_with_mas_brain(
                                                    s,
                                                    text,
                                                    force_spoken_reply=True,
                                                )
                                            continue
                                        # Extract text: top-level "text" or inject_feedback.injection.content
                                        text = normalize(payload.get("text", ""))
                                        if not text and payload.get("type") == "inject_feedback":
                                            inj = payload.get("injection") or {}
                                            text = normalize(inj.get("content", ""))
                                        if text:
                                            # Only clone user transcripts to MAS, not inject_feedback (MYCA response)
                                            if payload.get("type") != "inject_feedback":
                                                await clone_to_mas_memory(s, "user", text)
                                                if s.duplex_session:
                                                    s.duplex_session.record_user_turn(text)
                                        # Forward to TTS: inject_feedback only (user_speech TTS via process_with_mas_brain).
                                        # Never speak raw user text — that just echoes "hello" back.
                                        should_tts = payload.get("type") == "inject_feedback"
                                        if should_tts and text:
                                            try_moshi_text = os.getenv(
                                                "BRIDGE_TRY_MOSHI_TEXT_TTS", "true"
                                            ).lower() in ("1", "true", "yes")
                                            start_tts_cooldown(session_id)

                                            async def _try_moshi_text_tts() -> None:
                                                if not try_moshi_text:
                                                    return
                                                try:
                                                    await moshi.send_bytes(b"\x02" + text.encode("utf-8"))
                                                    logger.info(
                                                        f"[{session_id[:8]}] Sent 0x02 text frame to Moshi (last-resort TTS)"
                                                    )
                                                except Exception as ex:
                                                    logger.warning(
                                                        f"[{session_id[:8]}] Moshi 0x02 text TTS failed: {ex}"
                                                    )

                                            if TTS_FALLBACK_AVAILABLE and tts_synthesize_to_opus:
                                                logger.info(f"[{session_id[:8]}] TTS fallback (edge-tts): {text[:60]}...")
                                                s.is_tts_playing = True
                                                try:
                                                    await send_json_to_browser(session_id, {"type": "text", "text": text, "speaker": "myca"})
                                                    packets = await tts_synthesize_to_opus(text)
                                                    sent = 0
                                                    for pkt in packets:
                                                        if await send_bytes_to_browser(session_id, b"\x01" + pkt):
                                                            sent += 1
                                                    if sent == 0:
                                                        logger.error(
                                                            f"[{session_id[:8]}] edge-tts/ffmpeg produced 0 Opus packets — "
                                                            "install ffmpeg, pip install edge-tts opuslib; optional FFMPEG_PATH. "
                                                            "Set BRIDGE_TRY_MOSHI_TEXT_TTS=true (default) to try Moshi 0x02."
                                                        )
                                                        await _try_moshi_text_tts()
                                                finally:
                                                    s.is_tts_playing = False
                                            else:
                                                logger.warning(
                                                    f"[{session_id[:8]}] TTS module unavailable (edge-tts import failed); trying Moshi text"
                                                )
                                                s.is_tts_playing = True
                                                try:
                                                    await send_json_to_browser(session_id, {"type": "text", "text": text, "speaker": "myca"})
                                                    await _try_moshi_text_tts()
                                                finally:
                                                    s.is_tts_playing = False
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
                    moshi_task = asyncio.create_task(moshi_to_browser())
                    browser_task = asyncio.create_task(browser_to_moshi())
                    done, pending = await asyncio.wait(
                        {moshi_task, browser_task},
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    for task in pending:
                        task.cancel()
                    for task in done.union(pending):
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass
                        except Exception:
                            # Errors are already logged in loop-specific handlers above.
                            pass
                    try:
                        if not moshi.closed:
                            await moshi.close()
                    except Exception:
                        pass
            except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as conn_err:
                logger.error(f"[{session_id[:8]}] Moshi connection failed: {type(conn_err).__name__}: {conn_err}")
                await send_json_to_browser(session_id, {
                    "type": "error",
                    "message": f"Moshi unreachable at {MOSHI_HOST}:{MOSHI_PORT}. Ensure Moshi is running; run _start_voice_system.py to warm up.",
                })
                return
    except Exception as e:
        logger.error(f"Bridge error: {e}")
        try:
            await send_json_to_browser(session_id, {"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        # Clean up WebSocket registration and VAD state
        voice_websockets.pop(session_id, None)
        browser_send_locks.pop(session_id, None)
        _tts_session_locks.pop(session_id, None)
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