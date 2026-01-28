#!/usr/bin/env python3
"""PersonaPlex Bridge API - January 28, 2026
Connects frontend to PersonaPlex and MAS orchestrator"""
import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Optional
from uuid import uuid4
import httpx
import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="PersonaPlex Bridge", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

PERSONAPLEX_URL = os.getenv("PERSONAPLEX_URL", "ws://localhost:8998")
MAS_API_URL = os.getenv("MAS_API_URL", "http://192.168.0.188:8001")
N8N_URL = os.getenv("N8N_URL", "http://192.168.0.188:5678")

class SessionRequest(BaseModel):
    mode: str = "auto"
    persona: str = "myca"
    check_only: bool = False

class TextMessage(BaseModel):
    text: str
    session_id: Optional[str] = None

sessions = {}

@app.get("/health")
async def health():
    pp_ok = await check_personaplex()
    return {"status": "healthy", "personaplex": pp_ok, "timestamp": datetime.utcnow().isoformat()}

@app.post("/session")
async def create_session(req: SessionRequest):
    pp_available = await check_personaplex()
    if req.check_only:
        return {"personaplex_available": pp_available, "recommended_mode": "personaplex" if pp_available else "elevenlabs"}
    
    sid = str(uuid4())
    mode = "personaplex" if (req.mode == "auto" and pp_available) or req.mode == "personaplex" else "elevenlabs"
    session = {
        "session_id": sid,
        "conversation_id": str(uuid4()),
        "mode": mode,
        "personaplex_available": pp_available,
        "transport": {"type": "websocket", "url": f"ws://localhost:8999/ws/{sid}"} if mode == "personaplex" else {"type": "http"},
        "created_at": datetime.utcnow().isoformat()
    }
    sessions[sid] = session
    return session

@app.get("/sessions")
async def list_sessions():
    return {"sessions": list(sessions.values()), "stats": {"active_sessions": len(sessions), "total_sessions": len(sessions)}}

@app.delete("/sessions/{session_id}")
async def end_session(session_id: str):
    if session_id in sessions:
        del sessions[session_id]
    return {"success": True}

@app.post("/chat")
async def chat(msg: TextMessage):
    start = datetime.utcnow()
    response = await call_mas_orchestrator(msg.text)
    latency = (datetime.utcnow() - start).total_seconds() * 1000
    return {"response_text": response, "latency_ms": latency, "agent": "myca"}

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(ws: WebSocket, session_id: str):
    await ws.accept()
    logger.info(f"WS connected: {session_id}")
    pp_ws = None
    try:
        pp_ws = await websockets.connect(PERSONAPLEX_URL)
        await ws.send_json({"type": "connected", "session_id": session_id})
        
        async def forward_from_pp():
            async for msg in pp_ws:
                if isinstance(msg, bytes):
                    await ws.send_bytes(msg)
                else:
                    data = json.loads(msg)
                    if data.get("type") == "agent_text":
                        text = data.get("text", "")
                        if needs_tool(text):
                            result = await call_mas_orchestrator(text)
                            data["tool_result"] = result
                    await ws.send_json(data)
        
        async def forward_to_pp():
            while True:
                data = await ws.receive()
                if "bytes" in data:
                    await pp_ws.send(data["bytes"])
                elif "text" in data:
                    await pp_ws.send(data["text"])
        
        await asyncio.gather(forward_from_pp(), forward_to_pp())
    except WebSocketDisconnect:
        logger.info(f"WS disconnected: {session_id}")
    finally:
        if pp_ws:
            await pp_ws.close()

async def check_personaplex():
    try:
        async with websockets.connect(PERSONAPLEX_URL, close_timeout=2) as ws:
            await ws.send(json.dumps({"type": "ping"}))
            return True
    except:
        return False

async def call_mas_orchestrator(text):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{MAS_API_URL}/voice/orchestrator/chat", json={"message": text, "want_audio": False}, timeout=10)
            if r.status_code == 200:
                return r.json().get("response_text", text)
    except Exception as e:
        logger.error(f"MAS error: {e}")
    return f"Processed: {text}"

def needs_tool(text):
    keywords = ["turn on", "turn off", "status", "check", "list", "run", "create", "delete"]
    return any(k in text.lower() for k in keywords)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8999)
