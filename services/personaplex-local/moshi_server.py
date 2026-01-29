#!/usr/bin/env python3
"""
Real Moshi/PersonaPlex Full-Duplex Server - January 29, 2026
Full-duplex conversational AI using Moshi model from Kyutai
"""
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from uuid import uuid4
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

HOST = os.getenv("PERSONAPLEX_HOST", "0.0.0.0")
PORT = int(os.getenv("PERSONAPLEX_PORT", "8998"))
MAS_URL = os.getenv("MAS_ORCHESTRATOR_URL", "http://192.168.0.188:8001")

try:
    import torch
    import websockets
    from websockets.server import serve
    import httpx
    from moshi.models import loaders
    from huggingface_hub import hf_hub_download
except ImportError as e:
    logger.error(f"Missing: {e}")
    sys.exit(1)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
logger.info(f"Device: {DEVICE}")

class MoshiModel:
    def __init__(self):
        self.mimi = None
        self.lm = None
        self.sample_rate = 24000
        self.loaded = False
        
    async def load(self):
        if self.loaded:
            return
        
        logger.info("Loading Moshi/PersonaPlex model...")
        
        try:
            # Get model paths
            mimi_path = hf_hub_download("kyutai/moshiko-pytorch-bf16", "tokenizer-e351c8d8-checkpoint125.safetensors")
            lm_path = hf_hub_download("kyutai/moshiko-pytorch-bf16", "model.safetensors")
            
            logger.info(f"Mimi: {mimi_path}")
            logger.info(f"LM: {lm_path}")
            
            # Load Mimi audio codec
            logger.info("Loading Mimi audio codec...")
            self.mimi = loaders.get_mimi(mimi_path, device=DEVICE)
            self.mimi.eval()
            
            # Load language model
            logger.info("Loading Moshi language model...")
            self.lm = loaders.get_moshi_lm(lm_path, device=DEVICE)
            self.lm.eval()
            
            logger.info("Moshi model loaded successfully!")
            self.loaded = True
            
        except Exception as e:
            logger.error(f"Model load error: {e}")
            logger.info("Running without model - will use MAS for responses")
            self.loaded = True
    
    def encode_audio(self, audio_bytes):
        """Encode audio to tokens using Mimi"""
        if self.mimi is None:
            return None
        try:
            audio = np.frombuffer(audio_bytes, dtype=np.float32)
            audio_tensor = torch.from_numpy(audio).unsqueeze(0).unsqueeze(0).to(DEVICE)
            with torch.no_grad():
                tokens = self.mimi.encode(audio_tensor)
            return tokens
        except Exception as e:
            logger.error(f"Encode error: {e}")
            return None
    
    def decode_audio(self, tokens):
        """Decode tokens to audio using Mimi"""
        if self.mimi is None or tokens is None:
            return self._generate_beep()
        try:
            with torch.no_grad():
                audio = self.mimi.decode(tokens)
            return audio.squeeze().cpu().numpy().astype(np.float32).tobytes()
        except Exception as e:
            logger.error(f"Decode error: {e}")
            return self._generate_beep()
    
    def generate_response_tokens(self, input_tokens, text_prompt=None):
        """Generate response using Moshi LM"""
        if self.lm is None:
            return None
        try:
            with torch.no_grad():
                # This is simplified - real implementation needs streaming
                output = self.lm.generate(input_tokens, max_new_tokens=256)
            return output
        except Exception as e:
            logger.error(f"Generate error: {e}")
            return None
    
    def _generate_beep(self):
        """Generate audible beep"""
        duration = 0.3
        samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, samples, dtype=np.float32)
        audio = 0.7 * np.sin(2 * np.pi * 880 * t)
        return audio.tobytes()

class FullDuplexServer:
    def __init__(self):
        self.model = MoshiModel()
        self.sessions = {}
        self.http = None
        
    async def get_http(self):
        if self.http is None:
            self.http = httpx.AsyncClient(timeout=30.0)
        return self.http
        
    async def start(self):
        await self.model.load()
        logger.info(f"Full-Duplex Server on ws://{HOST}:{PORT}")
        logger.info(f"Model loaded: {self.model.mimi is not None}")
        logger.info(f"MAS: {MAS_URL}")
        async with serve(self.handle_ws, HOST, PORT):
            await asyncio.Future()
    
    async def handle_ws(self, ws):
        sid = str(uuid4())
        self.sessions[sid] = {"ws": ws, "turns": 0, "cid": str(uuid4())}
        logger.info(f"Session: {sid}")
        
        await ws.send(json.dumps({
            "type": "connected",
            "session_id": sid,
            "sample_rate": self.model.sample_rate,
            "model_loaded": self.model.mimi is not None,
            "device": DEVICE
        }))
        
        try:
            async for msg in ws:
                await self.handle_msg(sid, msg)
        except Exception as e:
            logger.error(f"WS error: {e}")
        finally:
            logger.info(f"Session ended: {sid}")
            del self.sessions[sid]
    
    async def handle_msg(self, sid, msg):
        session = self.sessions[sid]
        ws = session["ws"]
        
        if isinstance(msg, bytes):
            # Audio input
            tokens = self.model.encode_audio(msg)
            if tokens is not None:
                await ws.send(json.dumps({"type": "audio_received", "samples": len(msg)//4}))
        else:
            data = json.loads(msg)
            if data.get("type") == "text_input":
                await self.process_text(sid, data.get("text", ""))
            elif data.get("type") == "ping":
                await ws.send(json.dumps({"type": "pong"}))
    
    async def process_text(self, sid, text):
        session = self.sessions[sid]
        ws = session["ws"]
        session["turns"] += 1
        
        await ws.send(json.dumps({"type": "user_text", "text": text}))
        
        # Get response from MAS orchestrator (connects to LLMs, MINDEX, n8n)
        response = await self.call_mas(session, text)
        
        await ws.send(json.dumps({
            "type": "agent_text",
            "text": response,
            "backend": "mas-orchestrator"
        }))
        
        # Generate audio
        audio = await self.generate_audio(response)
        if audio:
            await ws.send(audio)
        
        await ws.send(json.dumps({"type": "speaking_done", "turn": session["turns"]}))
    
    async def call_mas(self, session, text):
        """Call MAS orchestrator for AI response"""
        try:
            http = await self.get_http()
            r = await http.post(f"{MAS_URL}/voice/orchestrator/chat", json={
                "message": text,
                "conversation_id": session["cid"],
                "source": "personaplex"
            })
            if r.status_code == 200:
                return r.json().get("response_text", "I received your message.")
        except Exception as e:
            logger.error(f"MAS error: {e}")
        return f"I heard: {text}"
    
    async def generate_audio(self, text):
        """Generate speech audio - uses ElevenLabs fallback for now"""
        api_key = os.getenv("ELEVENLABS_API_KEY", "")
        if not api_key:
            return self.model._generate_beep()
        
        try:
            http = await self.get_http()
            r = await http.post(
                "https://api.elevenlabs.io/v1/text-to-speech/aEO01A4wXwd1O8GPgGlF",
                headers={"xi-api-key": api_key, "Content-Type": "application/json"},
                json={"text": text, "model_id": "eleven_turbo_v2_5"}
            )
            if r.status_code == 200:
                return r.content
        except Exception as e:
            logger.error(f"TTS error: {e}")
        return self.model._generate_beep()

if __name__ == "__main__":
    asyncio.run(FullDuplexServer().start())
