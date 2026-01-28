#!/usr/bin/env python3
"""PersonaPlex Test Server (No PyTorch) - January 28, 2026"""
import asyncio
import json
import logging
import os
import time
import math
from datetime import datetime
from uuid import uuid4
import numpy as np
import websockets
from websockets.server import serve

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HOST = os.getenv("PERSONAPLEX_HOST", "0.0.0.0")
PORT = int(os.getenv("PERSONAPLEX_PORT", "8998"))

class Session:
    def __init__(self, sid, ws):
        self.session_id = sid
        self.websocket = ws
        self.turn_count = 0

class PersonaPlexServer:
    def __init__(self):
        self.sessions = {}
        self.sample_rate = 24000
        
    async def handle_connection(self, ws):
        sid = str(uuid4())
        session = Session(sid, ws)
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
            await session.websocket.send(json.dumps({"type": "processing", "samples": len(audio)}))
    
    async def generate_response(self, session, user_text):
        session.turn_count += 1
        start = time.time()
        await session.websocket.send(json.dumps({"type": "user_text", "text": user_text}))
        
        # Generate response
        response = self._gen_text(user_text)
        latency = (time.time() - start) * 1000
        
        await session.websocket.send(json.dumps({"type": "agent_text", "text": response, "latency_ms": latency}))
        
        # Generate audio
        audio = self._gen_audio(response)
        await session.websocket.send(audio.tobytes())
        await session.websocket.send(json.dumps({"type": "speaking_done", "turn": session.turn_count}))
    
    def _gen_text(self, text):
        t = text.lower()
        if any(g in t for g in ["hello", "hi", "hey"]):
            return "Hello! I'm MYCA, your Mycosoft Autonomous Cognitive Agent. How can I help you today?"
        elif "status" in t:
            return "All systems operational. MAS orchestrator is running, n8n workflows are active, and I'm ready to assist."
        elif "agent" in t:
            return "I can manage agents for you. Would you like me to list active agents, spawn a new one, or check their status?"
        elif any(c in t for c in ["light", "turn on", "turn off"]):
            return "I'll handle that control for you. Command sent to the smart home system."
        elif "help" in t:
            return "I can help with system status, agent management, smart device control, database queries, and workflow execution."
        elif "test" in t:
            return "This is a test response from MYCA. The PersonaPlex voice system is working correctly on your local RTX 5090!"
        return f"I heard: {text}. Processing your request."
    
    def _gen_audio(self, text):
        duration_s = min(len(text) * 0.05, 5.0)
        samples = int(self.sample_rate * duration_s)
        t = np.linspace(0, duration_s, samples, dtype=np.float32)
        # Generate a pleasant tone sweep
        freq = 220 + 220 * np.sin(2 * np.pi * 0.5 * t)
        audio = 0.15 * np.sin(2 * np.pi * freq * t / self.sample_rate * 100)
        return audio
    
    async def run(self):
        logger.info(f"PersonaPlex Test Server on ws://{HOST}:{PORT}")
        async with serve(self.handle_connection, HOST, PORT):
            await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(PersonaPlexServer().run())
