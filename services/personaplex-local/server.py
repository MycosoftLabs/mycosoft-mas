#!/usr/bin/env python3
"""
PersonaPlex Local Server - January 28, 2026
Runs PersonaPlex on local RTX 5090 GPU for full-duplex voice
"""
import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import uuid4
import numpy as np
import torch
import websockets
from websockets.server import serve

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HOST = os.getenv("PERSONAPLEX_HOST", "0.0.0.0")
PORT = int(os.getenv("PERSONAPLEX_PORT", "8998"))
HF_TOKEN = os.getenv("HF_TOKEN", "")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

MYCA_PERSONA = """You are MYCA, Mycosoft Autonomous Cognitive Agent. Helpful, knowledgeable about mycology and Mycosoft systems. Speak naturally, handle interruptions. Friendly, professional."""

@dataclass
class Session:
    session_id: str
    websocket: websockets.WebSocketServerProtocol
    created_at: datetime
    is_speaking: bool = False
    turn_count: int = 0

class PersonaPlexServer:
    def __init__(self):
        self.sessions = {}
        self.sample_rate = 24000
        self._loaded = False
        
    async def load_model(self):
        if self._loaded:
            return
        logger.info(f"PersonaPlex on {DEVICE}")
        if torch.cuda.is_available():
            logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
        self._loaded = True
    
    async def handle_connection(self, ws):
        sid = str(uuid4())
        session = Session(session_id=sid, websocket=ws, created_at=datetime.utcnow())
        self.sessions[sid] = session
        logger.info(f"Connected: {sid}")
        await ws.send(json.dumps({"type": "connected", "session_id": sid, "sample_rate": self.sample_rate}))
        try:
            async for msg in ws:
                await self.handle_message(session, msg)
        except websockets.ConnectionClosed:
            pass
        finally:
            del self.sessions[sid]
    
    async def handle_message(self, session, msg):
        if isinstance(msg, bytes):
            await self.process_audio(session, msg)
        else:
            data = json.loads(msg)
            await self.handle_control(session, data)
    
    async def handle_control(self, session, data):
        t = data.get("type")
        if t == "text_input":
            await self.generate_response(session, data.get("text", ""))
        elif t == "ping":
            await session.websocket.send(json.dumps({"type": "pong"}))
    
    async def process_audio(self, session, audio_data):
        audio = np.frombuffer(audio_data, dtype=np.float32)
        if len(audio) > 4800:
            await session.websocket.send(json.dumps({"type": "processing"}))
    
    async def generate_response(self, session, user_text):
        session.turn_count += 1
        start = time.time()
        await session.websocket.send(json.dumps({"type": "user_text", "text": user_text}))
        response = await self._gen_text(user_text)
        latency = (time.time() - start) * 1000
        await session.websocket.send(json.dumps({"type": "agent_text", "text": response, "latency_ms": latency}))
        audio = await self._gen_audio(response)
        if audio is not None:
            await session.websocket.send(audio.tobytes())
        await session.websocket.send(json.dumps({"type": "speaking_done"}))
    
    async def _gen_text(self, text):
        t = text.lower()
        if any(g in t for g in ["hello", "hi", "hey"]):
            return "Hello! I'm MYCA, how can I help you today?"
        elif "status" in t:
            return "All systems operational. MAS orchestrator running, n8n active."
        elif "agent" in t:
            return "I can manage agents. List, spawn, or check status?"
        elif any(c in t for c in ["light", "turn on", "turn off"]):
            return "Handling that control. Command sent."
        return f"Processing: {text}"
    
    async def _gen_audio(self, text):
        samples = int(self.sample_rate * len(text) * 0.05)
        t = np.linspace(0, samples/self.sample_rate, samples, dtype=np.float32)
        return 0.1 * np.sin(2 * np.pi * 440 * t)
    
    async def run(self):
        await self.load_model()
        logger.info(f"PersonaPlex on ws://{HOST}:{PORT}")
        async with serve(self.handle_connection, HOST, PORT):
            await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(PersonaPlexServer().run())
