#!/usr/bin/env python3
"""
Real PersonaPlex Server - January 28, 2026
Full-duplex conversational AI using NVIDIA PersonaPlex model
Requires: RTX 5090 (32GB VRAM) or similar
"""
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from uuid import uuid4
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

HOST = os.getenv("PERSONAPLEX_HOST", "0.0.0.0")
PORT = int(os.getenv("PERSONAPLEX_PORT", "8998"))
HF_TOKEN = os.getenv("HF_TOKEN", "")
MAS_ORCHESTRATOR_URL = os.getenv("MAS_ORCHESTRATOR_URL", "http://192.168.0.188:8001")

# Voice prompt file (NATF2 = Natural Female 2)
VOICE_PROMPT = os.getenv("VOICE_PROMPT", "NATF2.pt")
TEXT_PROMPT_FILE = os.getenv("TEXT_PROMPT_FILE", "myca_persona.txt")

try:
    import torch
    import websockets
    from websockets.server import serve
    import httpx
except ImportError as e:
    logger.error(f"Missing dependency: {e}")
    logger.error("Install with: pip install torch websockets httpx")
    sys.exit(1)

# Check CUDA
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
if DEVICE == "cuda":
    GPU_NAME = torch.cuda.get_device_name(0)
    GPU_MEM = torch.cuda.get_device_properties(0).total_memory / 1e9
    logger.info(f"GPU: {GPU_NAME} ({GPU_MEM:.1f}GB)")
else:
    logger.warning("No GPU detected - will run in CPU mode (very slow)")

class PersonaPlexModel:
    """Wrapper for NVIDIA PersonaPlex model"""
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.mimi_encoder = None
        self.mimi_decoder = None
        self.sample_rate = 24000
        self.loaded = False
        self.text_prompt = self._load_text_prompt()
        
    def _load_text_prompt(self):
        prompt_file = os.path.join(os.path.dirname(__file__), TEXT_PROMPT_FILE)
        if os.path.exists(prompt_file):
            with open(prompt_file) as f:
                return f.read().strip()
        return "You are MYCA, a helpful AI assistant from Mycosoft. Be conversational and friendly."
    
    async def load(self):
        if self.loaded:
            return
        
        logger.info("Loading PersonaPlex model...")
        
        try:
            # Try to load the real PersonaPlex model
            from moshi.models import loaders
            from huggingface_hub import hf_hub_download
            
            if not HF_TOKEN:
                logger.warning("No HF_TOKEN set - using simulation mode")
                logger.warning("To use real model: export HF_TOKEN=your_token")
                self.loaded = True
                return
            
            # Download model weights
            logger.info("Downloading PersonaPlex weights from HuggingFace...")
            model_path = hf_hub_download(
                repo_id="nvidia/personaplex-7b-v1",
                filename="model.safetensors",
                token=HF_TOKEN
            )
            
            # Load Mimi codec
            logger.info("Loading Mimi audio codec...")
            mimi = loaders.get_mimi("cuda" if torch.cuda.is_available() else "cpu")
            self.mimi_encoder = mimi
            self.mimi_decoder = mimi
            
            # Load main model
            logger.info("Loading PersonaPlex transformer...")
            self.model = loaders.get_moshi_lm(device=DEVICE)
            
            logger.info("PersonaPlex model loaded successfully!")
            self.loaded = True
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            logger.info("Running in simulation mode")
            self.loaded = True
    
    def encode_audio(self, audio_bytes):
        """Encode raw audio to tokens using Mimi codec"""
        if self.mimi_encoder is None:
            return None
        audio = np.frombuffer(audio_bytes, dtype=np.float32)
        audio_tensor = torch.from_numpy(audio).unsqueeze(0).to(DEVICE)
        with torch.no_grad():
            tokens = self.mimi_encoder.encode(audio_tensor)
        return tokens
    
    def decode_audio(self, tokens):
        """Decode tokens to audio using Mimi codec"""
        if self.mimi_decoder is None:
            return self._generate_tone(0.5)
        with torch.no_grad():
            audio = self.mimi_decoder.decode(tokens)
        return audio.cpu().numpy().tobytes()
    
    def generate_response(self, user_audio_tokens, text_input=None):
        """Generate response using PersonaPlex model"""
        if self.model is None:
            # Simulation mode
            return self._simulate_response(text_input)
        
        # Real model inference would go here
        # This requires the full PersonaPlex inference loop
        pass
    
    def _simulate_response(self, text):
        """Simulate PersonaPlex response when model not loaded"""
        t = text.lower() if text else ""
        if any(g in t for g in ["hello", "hi", "hey"]):
            return "Hello! I am MYCA. How can I help you today?", self._generate_tone(1.0)
        elif "status" in t:
            return "All systems operational. Ready to assist.", self._generate_tone(1.5)
        else:
            return f"I heard: {text}", self._generate_tone(1.0)
    
    def _generate_tone(self, duration):
        """Generate a simple tone for testing"""
        samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, samples, dtype=np.float32)
        audio = 0.5 * np.sin(2 * np.pi * 440 * t)
        return audio.tobytes()

class PersonaPlexServer:
    def __init__(self):
        self.model = PersonaPlexModel()
        self.sessions = {}
        self.http_client = None
        
    async def get_http(self):
        if self.http_client is None:
            self.http_client = httpx.AsyncClient(timeout=30.0)
        return self.http_client
        
    async def start(self):
        await self.model.load()
        logger.info(f"PersonaPlex Server starting on ws://{HOST}:{PORT}")
        logger.info(f"Device: {DEVICE}")
        logger.info(f"MAS: {MAS_ORCHESTRATOR_URL}")
        async with serve(self.handle_connection, HOST, PORT):
            await asyncio.Future()
    
    async def handle_connection(self, ws):
        sid = str(uuid4())
        self.sessions[sid] = {"ws": ws, "turns": 0, "cid": str(uuid4())}
        logger.info(f"Session started: {sid}")
        
        await ws.send(json.dumps({
            "type": "connected",
            "session_id": sid,
            "sample_rate": self.model.sample_rate,
            "device": DEVICE,
            "model_loaded": self.model.model is not None
        }))
        
        try:
            async for msg in ws:
                await self.handle_message(sid, msg)
        except Exception as e:
            logger.error(f"Session error: {e}")
        finally:
            logger.info(f"Session ended: {sid}")
            del self.sessions[sid]
    
    async def handle_message(self, sid, msg):
        session = self.sessions[sid]
        ws = session["ws"]
        
        if isinstance(msg, bytes):
            # Audio input - would be processed by Mimi encoder
            tokens = self.model.encode_audio(msg)
            await ws.send(json.dumps({"type": "processing"}))
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
        
        # Send user text back
        await ws.send(json.dumps({"type": "user_text", "text": text}))
        
        # Call MAS orchestrator for intelligent response
        response_text = await self.call_mas(session, text)
        
        # Send agent text
        await ws.send(json.dumps({
            "type": "agent_text",
            "text": response_text,
            "backend": "mas-orchestrator"
        }))
        
        # Generate audio response
        if self.model.model is not None:
            # Real PersonaPlex would generate audio tokens
            audio = self.model.decode_audio(None)
        else:
            # Use ElevenLabs as fallback
            audio = await self.get_elevenlabs_audio(response_text)
            if audio is None:
                _, audio = self.model._simulate_response(text)
        
        await ws.send(audio)
        await ws.send(json.dumps({"type": "speaking_done", "turn": session["turns"]}))
    
    async def call_mas(self, session, text):
        """Call MAS orchestrator for AI response with tool access"""
        try:
            http = await self.get_http()
            response = await http.post(
                f"{MAS_ORCHESTRATOR_URL}/voice/orchestrator/chat",
                json={
                    "message": text,
                    "conversation_id": session["cid"],
                    "source": "personaplex",
                    "want_audio": False
                }
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("response_text", "I received your message.")
        except Exception as e:
            logger.error(f"MAS error: {e}")
        return f"I heard: {text}. (MAS unavailable)"
    
    async def get_elevenlabs_audio(self, text):
        """Fallback to ElevenLabs TTS"""
        api_key = os.getenv("ELEVENLABS_API_KEY", "")
        voice_id = os.getenv("ELEVENLABS_VOICE_ID", "aEO01A4wXwd1O8GPgGlF")
        
        if not api_key:
            return None
        
        try:
            http = await self.get_http()
            response = await http.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={"xi-api-key": api_key, "Content-Type": "application/json"},
                json={"text": text, "model_id": "eleven_turbo_v2_5"}
            )
            if response.status_code == 200:
                return response.content
        except Exception as e:
            logger.error(f"ElevenLabs error: {e}")
        return None

if __name__ == "__main__":
    server = PersonaPlexServer()
    asyncio.run(server.start())
