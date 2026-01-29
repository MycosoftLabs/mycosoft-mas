#!/usr/bin/env python3
"""
PersonaPlex Voice Server - January 28, 2026
Full integration with MAS orchestrator, n8n, MINDEX, and LLM backends
"""
import asyncio
import json
import logging
import os
from datetime import datetime
from uuid import uuid4
import numpy as np
import websockets
from websockets.server import serve
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HOST = os.getenv("PERSONAPLEX_HOST", "0.0.0.0")
PORT = int(os.getenv("PERSONAPLEX_PORT", "8998"))

# Backend URLs
MAS_ORCHESTRATOR_URL = os.getenv("MAS_ORCHESTRATOR_URL", "http://192.168.0.188:8001")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://192.168.0.188:5678/webhook/myca-voice")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "aEO01A4wXwd1O8GPgGlF")

class Session:
    def __init__(self, sid, ws):
        self.session_id = sid
        self.websocket = ws
        self.turn_count = 0
        self.conversation_id = str(uuid4())

class PersonaPlexServer:
    def __init__(self):
        self.sessions = {}
        self.sample_rate = 24000
        self.http_client = None
        
    async def get_http(self):
        if self.http_client is None:
            self.http_client = httpx.AsyncClient(timeout=30.0)
        return self.http_client
        
    async def handle_connection(self, ws):
        sid = str(uuid4())
        session = Session(sid, ws)
        self.sessions[sid] = session
        logger.info(f"Session started: {sid}")
        await ws.send(json.dumps({
            "type": "connected", 
            "session_id": sid,
            "conversation_id": session.conversation_id,
            "sample_rate": self.sample_rate,
            "backend": "mas-orchestrator"
        }))
        try:
            async for msg in ws:
                await self.handle_message(session, msg)
        except websockets.ConnectionClosed:
            pass
        finally:
            logger.info(f"Session ended: {sid}")
            del self.sessions[sid]
    
    async def handle_message(self, session, msg):
        if isinstance(msg, bytes):
            # Audio input - would be processed by real PersonaPlex
            await session.websocket.send(json.dumps({"type": "processing"}))
        else:
            data = json.loads(msg)
            if data.get("type") == "text_input":
                await self.process_text(session, data.get("text", ""))
            elif data.get("type") == "ping":
                await session.websocket.send(json.dumps({"type": "pong"}))
    
    async def process_text(self, session, user_text):
        session.turn_count += 1
        start = datetime.utcnow()
        
        # Send user text back
        await session.websocket.send(json.dumps({"type": "user_text", "text": user_text}))
        
        # Call MAS orchestrator for real AI response
        response_text = await self.call_mas_orchestrator(session, user_text)
        
        latency_ms = (datetime.utcnow() - start).total_seconds() * 1000
        
        # Send agent response
        await session.websocket.send(json.dumps({
            "type": "agent_text", 
            "text": response_text,
            "latency_ms": latency_ms,
            "backend": "mas-orchestrator"
        }))
        
        # Generate and send audio
        audio_data = await self.generate_speech(response_text)
        if audio_data:
            await session.websocket.send(audio_data)
        
        await session.websocket.send(json.dumps({
            "type": "speaking_done", 
            "turn": session.turn_count
        }))
    
    async def call_mas_orchestrator(self, session, user_text):
        """Call MAS orchestrator which handles LLM routing, n8n, MINDEX, tools"""
        try:
            http = await self.get_http()
            
            # MAS orchestrator endpoint handles:
            # - LLM selection (OpenAI, Anthropic, Groq, Gemini)
            # - Tool calling
            # - MINDEX knowledge retrieval
            # - n8n workflow triggers
            payload = {
                "message": user_text,
                "conversation_id": session.conversation_id,
                "source": "personaplex",
                "want_audio": False,
                "context": {
                    "session_id": session.session_id,
                    "turn": session.turn_count
                }
            }
            
            response = await http.post(
                f"{MAS_ORCHESTRATOR_URL}/voice/orchestrator/chat",
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"MAS response: {data.get('agent', 'unknown')} - {len(data.get('response_text', ''))} chars")
                return data.get("response_text", "I received your message but couldn't process it.")
            else:
                logger.error(f"MAS error: {response.status_code}")
                # Fallback to n8n webhook
                return await self.call_n8n_fallback(session, user_text)
                
        except Exception as e:
            logger.error(f"Orchestrator error: {e}")
            return await self.call_n8n_fallback(session, user_text)
    
    async def call_n8n_fallback(self, session, user_text):
        """Fallback to n8n webhook if MAS is unavailable"""
        try:
            http = await self.get_http()
            payload = {
                "message": user_text,
                "conversation_id": session.conversation_id,
                "source": "personaplex-fallback"
            }
            
            response = await http.post(N8N_WEBHOOK_URL, json=payload)
            if response.status_code == 200:
                data = response.json()
                return data.get("response", data.get("message", "Processing via n8n workflow."))
        except Exception as e:
            logger.error(f"n8n fallback error: {e}")
        
        return "I'm having trouble connecting to the backend. Please try again."
    
    async def generate_speech(self, text):
        """Generate speech audio using ElevenLabs TTS"""
        if not ELEVENLABS_API_KEY:
            logger.warning("No ElevenLabs API key - generating beep")
            return self._gen_beep()
        
        try:
            http = await self.get_http()
            response = await http.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}",
                headers={
                    "xi-api-key": ELEVENLABS_API_KEY,
                    "Content-Type": "application/json",
                    "Accept": "audio/mpeg"
                },
                json={
                    "text": text,
                    "model_id": "eleven_turbo_v2_5",
                    "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
                }
            )
            
            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"ElevenLabs error: {response.status_code}")
                return self._gen_beep()
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return self._gen_beep()
    
    def _gen_beep(self):
        """Generate audible beep as fallback"""
        duration = 0.3
        samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, samples, dtype=np.float32)
        audio = 0.8 * np.sin(2 * np.pi * 880 * t)  # 880Hz beep
        return audio.tobytes()
    
    async def run(self):
        logger.info(f"PersonaPlex Server on ws://{HOST}:{PORT}")
        logger.info(f"MAS Orchestrator: {MAS_ORCHESTRATOR_URL}")
        logger.info(f"n8n Webhook: {N8N_WEBHOOK_URL}")
        logger.info(f"ElevenLabs TTS: {'ENABLED' if ELEVENLABS_API_KEY else 'DISABLED'}")
        async with serve(self.handle_connection, HOST, PORT):
            await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(PersonaPlexServer().run())
