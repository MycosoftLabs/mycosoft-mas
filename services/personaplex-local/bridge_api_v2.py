#!/usr/bin/env python3
"""
PersonaPlex Bridge API v2 - January 29, 2026
FastAPI service connecting Native Moshi TTS to website and MAS orchestrator

This bridge:
1. Checks PersonaPlex/Moshi server availability
2. Proxies WebSocket connections to the native moshi server
3. Provides REST endpoints for session management
4. Forwards both text AND audio to the browser
"""
import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4
import httpx
import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

app = FastAPI(title="PersonaPlex Bridge v2", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
PERSONAPLEX_URL = os.getenv("PERSONAPLEX_URL", "ws://localhost:8998")
MAS_ORCHESTRATOR_URL = os.getenv("MAS_ORCHESTRATOR_URL", "http://192.168.0.188:8001")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://192.168.0.188:5678/webhook")

class SessionCreate(BaseModel):
    conversation_id: Optional[str] = None
    mode: str = "personaplex"
    persona: str = "myca"

class TextMessage(BaseModel):
    session_id: str
    text: str

# Session storage
sessions = {}
pp_available = False
last_check = None


async def check_personaplex():
    """Check if PersonaPlex/Moshi server is available"""
    global pp_available, last_check
    try:
        async with websockets.connect(PERSONAPLEX_URL, close_timeout=3) as ws:
            # Wait for connection message
            msg = await asyncio.wait_for(ws.recv(), timeout=2)
            data = json.loads(msg)
            if data.get("type") == "connected":
                pp_available = True
                last_check = datetime.now(timezone.utc).isoformat()
                return True
    except Exception as e:
        pp_available = False
        last_check = datetime.now(timezone.utc).isoformat()
    return False


@app.on_event("startup")
async def startup():
    await check_personaplex()
    asyncio.create_task(periodic_check())


async def periodic_check():
    """Periodically check PersonaPlex availability"""
    while True:
        await asyncio.sleep(10)
        await check_personaplex()


@app.get("/health")
async def health():
    """Health check endpoint - returns PersonaPlex status"""
    return {
        "status": "healthy",
        "service": "personaplex-bridge",
        "personaplex": pp_available,
        "personaplex_url": PERSONAPLEX_URL,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.post("/session")
async def create_session(req: SessionCreate):
    """Create a new voice session"""
    sid = str(uuid4())
    cid = req.conversation_id or str(uuid4())
    sessions[sid] = {
        "conversation_id": cid,
        "mode": req.mode,
        "persona": req.persona,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    return {
        "session_id": sid,
        "conversation_id": cid,
        "mode": req.mode if pp_available else "elevenlabs",
        "personaplex_url": PERSONAPLEX_URL,
        "personaplex_available": pp_available,
        "created_at": sessions[sid]["created_at"]
    }


@app.get("/sessions")
async def list_sessions():
    """List active sessions"""
    return {
        "sessions": [{"session_id": k, **v} for k, v in sessions.items()],
        "count": len(sessions)
    }


@app.delete("/session/{session_id}")
async def end_session(session_id: str):
    """End a session"""
    if session_id in sessions:
        del sessions[session_id]
    return {"ended": True, "session_id": session_id}


@app.post("/chat")
async def chat(msg: TextMessage):
    """Send a chat message and get response with audio"""
    try:
        async with websockets.connect(PERSONAPLEX_URL, close_timeout=10) as ws:
            # Wait for connection
            conn_msg = await asyncio.wait_for(ws.recv(), timeout=3)
            
            # Send text input
            await ws.send(json.dumps({"type": "text_input", "text": msg.text}))
            
            response_text = ""
            audio_bytes = None
            
            # Receive responses
            while True:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=30)
                    
                    if isinstance(raw, str):
                        data = json.loads(raw)
                        if data.get("type") == "agent_text":
                            response_text = data.get("text", "")
                        elif data.get("type") == "audio_complete":
                            break
                        elif data.get("type") == "error":
                            break
                    elif isinstance(raw, bytes):
                        # Audio data (WAV format)
                        audio_bytes = raw
                        
                except asyncio.TimeoutError:
                    break
            
            # Return response with audio
            result = {
                "response_text": response_text,
                "session_id": msg.session_id,
                "has_audio": audio_bytes is not None
            }
            
            # If audio available, encode as base64
            if audio_bytes:
                import base64
                result["audio_base64"] = base64.b64encode(audio_bytes).decode("utf-8")
                result["audio_mime"] = "audio/wav"
            
            return result
            
    except Exception as e:
        return {
            "response_text": f"Error: {e}",
            "session_id": msg.session_id,
            "error": True
        }


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket proxy to PersonaPlex server"""
    await websocket.accept()
    
    try:
        async with websockets.connect(PERSONAPLEX_URL) as pp_ws:
            # Forward connection event
            await websocket.send_json({
                "type": "bridge_connected",
                "session_id": session_id,
                "backend": "moshi-native-v2"
            })
            
            async def forward_to_client():
                """Forward messages from PersonaPlex to browser"""
                try:
                    async for msg in pp_ws:
                        if isinstance(msg, str):
                            await websocket.send_text(msg)
                        elif isinstance(msg, bytes):
                            # Forward binary audio data
                            await websocket.send_bytes(msg)
                except Exception as e:
                    print(f"Forward to client error: {e}")
            
            async def forward_to_personaplex():
                """Forward messages from browser to PersonaPlex"""
                try:
                    while True:
                        data = await websocket.receive()
                        if "text" in data:
                            await pp_ws.send(data["text"])
                        elif "bytes" in data:
                            await pp_ws.send(data["bytes"])
                except Exception as e:
                    print(f"Forward to PersonaPlex error: {e}")
            
            # Run both forwarding tasks
            await asyncio.gather(
                forward_to_client(),
                forward_to_personaplex(),
                return_exceptions=True
            )
            
    except WebSocketDisconnect:
        print(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        print(f"WebSocket error: {e}")


@app.get("/voices")
async def list_voices():
    """List available voices"""
    return {
        "voices": [
            {"id": "alba-mackenna/casual.wav", "name": "Alba (Casual)", "gender": "female", "language": "en"},
            {"id": "alba-mackenna/announcer.wav", "name": "Alba (Announcer)", "gender": "female", "language": "en"},
            {"id": "alba-mackenna/merchant.wav", "name": "Alba (Merchant)", "gender": "female", "language": "en"},
        ],
        "default": "alba-mackenna/casual.wav"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8999)
