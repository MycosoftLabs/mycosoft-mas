#!/usr/bin/env python3
"""Update PersonaPlex Bridge to v7.0.0 with lower temperature"""

BRIDGE_CODE = r'''#!/usr/bin/env python3
"""
PersonaPlex NVIDIA Bridge v7.0.0 - February 3, 2026
Full-Duplex Voice with MAS Tool Call Integration

FIXES in v7.0.0:
- Lower temperature (0.4) for consistent MYCA responses
- Improved health check handling for Moshi 426 responses
"""
import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Dict
from uuid import uuid4

import aiohttp
import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("personaplex-bridge")

app = FastAPI(title="PersonaPlex NVIDIA Bridge", version="7.0.0")

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

# LOWERED Temperature for consistent MYCA responses (was 0.7)
TEXT_TEMPERATURE = float(os.getenv("TEXT_TEMPERATURE", "0.4"))
AUDIO_TEMPERATURE = float(os.getenv("AUDIO_TEMPERATURE", "0.6"))

DEFAULT_VOICE_PROMPT = os.getenv("VOICE_PROMPT", "NATF2.pt")


def load_myca_persona():
    base_path = os.path.dirname(__file__)
    paths = [
        os.path.join(base_path, "../../config/myca_personaplex_prompt_1000.txt"),
        os.path.join(base_path, "../../config/myca_personaplex_prompt.txt"),
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
    persona: str = "myca"
    voice: str = "myca"
    enable_mas_events: bool = True


@dataclass
class BridgeSession:
    session_id: str
    conversation_id: str
    persona: str
    voice: str
    created_at: str
    enable_mas_events: bool = True
    transcript_history: List[dict] = field(default_factory=list)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    
    def to_dict(self):
        return {"session_id": self.session_id, "conversation_id": self.conversation_id, "created_at": self.created_at}


sessions: Dict[str, BridgeSession] = {}
moshi_available = False
http_client: Optional[httpx.AsyncClient] = None


async def get_http_client():
    global http_client
    if http_client is None:
        http_client = httpx.AsyncClient(timeout=MAS_TIMEOUT)
    return http_client


def normalize(text):
    return re.sub(r"\s+", " ", text).strip()


async def clone_to_mas_memory(session: BridgeSession, speaker: str, text: str):
    if not text or len(text.strip()) < 2:
        return
    asyncio.create_task(_send_to_mas(session, speaker, normalize(text)))


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
    """Check Moshi availability - 426 means it's running (WebSocket upgrade required)"""
    global moshi_available
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get(f"http://{MOSHI_HOST}:{MOSHI_PORT}/", timeout=5)
            moshi_available = r.status_code in (200, 426)
    except Exception as e:
        # Connection errors with "426" or "upgrade" mean server is up
        error_str = str(e).lower()
        moshi_available = "426" in error_str or "upgrade" in error_str


@app.on_event("startup")
async def startup():
    logger.info(f"PersonaPlex Bridge v7.0.0 starting...")
    logger.info(f"Temperature: text={TEXT_TEMPERATURE}, audio={AUDIO_TEMPERATURE}")
    logger.info(f"MYCA persona: {len(MYCA_PERSONA)} chars")
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


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": "7.0.0",
        "moshi_available": moshi_available,
        "moshi_url": f"http://{MOSHI_HOST}:{MOSHI_PORT}",
        "mas_url": MAS_ORCHESTRATOR_URL,
        "temperature": {"text": TEXT_TEMPERATURE, "audio": AUDIO_TEMPERATURE},
        "persona_length": len(MYCA_PERSONA),
        "features": {"full_duplex": True, "mas_tool_calls": True, "memory_cloning": True}
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
        created_at=datetime.now(timezone.utc).isoformat(),
        enable_mas_events=body.enable_mas_events
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
        "voice_prompt": DEFAULT_VOICE_PROMPT,
        "audio_temperature": str(AUDIO_TEMPERATURE),
        "text_temperature": str(TEXT_TEMPERATURE),
    })
    
    moshi_url = f"{MOSHI_WS_URL}?{params}"
    logger.info(f"[{session_id[:8]}] Connecting to Moshi (temp={TEXT_TEMPERATURE})")
    
    audio_sent = 0
    audio_recv = 0
    
    try:
        async with aiohttp.ClientSession() as aio:
            async with aio.ws_connect(moshi_url, timeout=aiohttp.ClientTimeout(total=60)) as moshi:
                try:
                    hs = await asyncio.wait_for(moshi.receive(), 30)
                except asyncio.TimeoutError:
                    await websocket.send_json({"type": "error", "message": "Moshi timeout"})
                    return
                
                if hs.type == aiohttp.WSMsgType.BINARY and hs.data == b"\x00":
                    await websocket.send_bytes(b"\x00")
                    logger.info(f"[{session_id[:8]}] Full-duplex active (temp={TEXT_TEMPERATURE})")
                else:
                    await websocket.send_json({"type": "error", "message": f"Handshake failed: {hs.type}"})
                    return
                
                last_myca = ""
                acc_myca = ""
                
                async def moshi_to_browser():
                    nonlocal last_myca, acc_myca, audio_recv
                    try:
                        async for msg in moshi:
                            if msg.type == aiohttp.WSMsgType.BINARY and len(msg.data) > 0:
                                kind = msg.data[0]
                                if kind == 1:  # Audio
                                    audio_recv += 1
                                    await websocket.send_bytes(msg.data)
                                elif kind == 2:  # Text from Moshi
                                    text = msg.data[1:].decode("utf-8", errors="ignore")
                                    await websocket.send_json({"type": "text", "text": text, "speaker": "myca"})
                                    acc_myca += text
                                    if any(p in text for p in [".", "!", "?", "\n"]):
                                        n = normalize(acc_myca)
                                        if n and n != last_myca:
                                            last_myca = n
                                            await clone_to_mas_memory(s, "myca", n)
                                        acc_myca = ""
                                elif kind == 3:  # Control
                                    pass
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
    return {"session_id": session_id, "history": s.transcript_history}


@app.get("/")
async def root():
    return RedirectResponse(f"http://{MOSHI_HOST}:{MOSHI_PORT}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8999)
'''

if __name__ == "__main__":
    path = r"c:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\services\personaplex-local\personaplex_bridge_nvidia.py"
    with open(path, "w", encoding="utf-8") as f:
        f.write(BRIDGE_CODE)
    print(f"Updated bridge to v7.0.0 with TEXT_TEMPERATURE=0.4")
    print(f"Wrote {len(BRIDGE_CODE)} bytes to {path}")
