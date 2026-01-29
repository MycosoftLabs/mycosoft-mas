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
import json
import os
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4
import httpx
import aiohttp
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import logging

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
MAS_ORCHESTRATOR_URL = os.getenv("MAS_ORCHESTRATOR_URL", "http://192.168.0.188:8001")

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

sessions = {}
moshi_available = False
last_check = None

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

@app.on_event("startup")
async def startup():
    await check_moshi_health()
    asyncio.create_task(periodic_check())

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
        "timestamp": last_check or datetime.now(timezone.utc).isoformat()
    }

@app.post("/session")
async def create_session(req: SessionCreate):
    sid = str(uuid4())
    cid = req.conversation_id or str(uuid4())
    voice_prompt = VOICE_PROMPTS.get(req.voice, VOICE_PROMPTS["default"])
    text_prompt = MYCA_PERSONA if req.persona == "myca" else ""
    
    sessions[sid] = {
        "conversation_id": cid,
        "mode": req.mode,
        "persona": req.persona,
        "voice": req.voice,
        "voice_prompt": voice_prompt,
        "text_prompt": text_prompt,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    
    return {
        "session_id": sid,
        "conversation_id": cid,
        "mode": "personaplex" if moshi_available else "elevenlabs",
        "moshi_available": moshi_available,
        "voice_prompt": voice_prompt,
        "ws_url": f"ws://localhost:8999/ws/{sid}",
        "direct_moshi_url": f"http://{MOSHI_HOST}:{MOSHI_PORT}",
        "created_at": sessions[sid]["created_at"]
    }

@app.get("/sessions")
async def list_sessions():
    return {"sessions": [{"session_id": k, **v} for k, v in sessions.items()], "count": len(sessions)}

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

@app.websocket("/ws/{session_id}")
async def websocket_bridge(websocket: WebSocket, session_id: str):
    await websocket.accept()
    session = sessions.get(session_id, {"text_prompt": MYCA_PERSONA, "voice_prompt": "NATF2.pt"})
    
    import urllib.parse
    params = urllib.parse.urlencode({
        "text_prompt": session.get("text_prompt", MYCA_PERSONA),
        "voice_prompt": session.get("voice_prompt", "NATF2.pt"),
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
                                        await websocket.send_json({"type": "text", "text": text})
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
                    except WebSocketDisconnect:
                        logger.info(f"Browser disconnected: {session_id}")
                    except Exception as e:
                        logger.error(f"Forward to Moshi error: {e}")
                
                await asyncio.gather(forward_to_browser(), forward_to_moshi(), return_exceptions=True)
    except Exception as e:
        logger.error(f"WebSocket bridge error: {e}")
        await websocket.send_json({"type": "error", "message": str(e)})

@app.get("/")
async def redirect_to_moshi():
    return RedirectResponse(url=f"http://{MOSHI_HOST}:{MOSHI_PORT}")

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting PersonaPlex NVIDIA Bridge on port 8999")
    uvicorn.run(app, host="0.0.0.0", port=8999)
