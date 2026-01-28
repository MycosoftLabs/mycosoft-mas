#!/usr/bin/env python3
"""
PersonaPlex Bridge API - January 28, 2026
FastAPI service connecting PersonaPlex to MAS orchestrator
"""
import asyncio
import json
import os
from datetime import datetime
from typing import Optional
from uuid import uuid4
import httpx
import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="PersonaPlex Bridge", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

sessions = {}
pp_available = False

async def check_personaplex():
    global pp_available
    try:
        async with websockets.connect(PERSONAPLEX_URL, close_timeout=2) as ws:
            pp_available = True
            return True
    except:
        pp_available = False
        return False

@app.on_event("startup")
async def startup():
    await check_personaplex()
    asyncio.create_task(periodic_check())

async def periodic_check():
    while True:
        await asyncio.sleep(10)
        await check_personaplex()

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "personaplex-bridge", "personaplex": pp_available, "timestamp": datetime.utcnow().isoformat()}

@app.post("/session")
async def create_session(req: SessionCreate):
    sid = str(uuid4())
    cid = req.conversation_id or str(uuid4())
    sessions[sid] = {"conversation_id": cid, "mode": req.mode, "persona": req.persona, "created_at": datetime.utcnow().isoformat()}
    return {"session_id": sid, "conversation_id": cid, "mode": req.mode if pp_available else "elevenlabs", "personaplex_url": PERSONAPLEX_URL, "personaplex_available": pp_available, "created_at": sessions[sid]["created_at"]}

@app.get("/sessions")
async def list_sessions():
    return {"sessions": [{"session_id": k, **v} for k, v in sessions.items()], "count": len(sessions)}

@app.delete("/session/{session_id}")
async def end_session(session_id: str):
    if session_id in sessions:
        del sessions[session_id]
    return {"ended": True, "session_id": session_id}

@app.post("/chat")
async def chat(msg: TextMessage):
    try:
        async with websockets.connect(PERSONAPLEX_URL, close_timeout=5) as ws:
            await ws.recv()
            await ws.send(json.dumps({"type": "text_input", "text": msg.text}))
            response_text = ""
            async for raw in ws:
                if isinstance(raw, str):
                    data = json.loads(raw)
                    if data.get("type") == "agent_text":
                        response_text = data.get("text", "")
                        break
            return {"response_text": response_text, "session_id": msg.session_id}
    except Exception as e:
        return {"response_text": f"Error: {e}", "session_id": msg.session_id, "error": True}

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    try:
        async with websockets.connect(PERSONAPLEX_URL) as pp_ws:
            await websocket.send_json({"type": "connected", "session_id": session_id})
            async def forward_to_client():
                try:
                    async for msg in pp_ws:
                        if isinstance(msg, str):
                            await websocket.send_text(msg)
                        else:
                            await websocket.send_bytes(msg)
                except:
                    pass
            async def forward_to_personaplex():
                try:
                    while True:
                        data = await websocket.receive()
                        if "text" in data:
                            await pp_ws.send(data["text"])
                        elif "bytes" in data:
                            await pp_ws.send(data["bytes"])
                except:
                    pass
            await asyncio.gather(forward_to_client(), forward_to_personaplex())
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WS error: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8999)
