#!/usr/bin/env python3
"""
Real Moshi Full-Duplex Server with Native Voice - January 29, 2026
Uses HuggingFace Transformers MoshiForConditionalGeneration for native speech synthesis
"""
import asyncio
import json
import logging
import os
import sys
from uuid import uuid4
import numpy as np
import io

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

HOST = os.getenv("PERSONAPLEX_HOST", "0.0.0.0")
PORT = int(os.getenv("PERSONAPLEX_PORT", "8998"))
MAS_URL = os.getenv("MAS_ORCHESTRATOR_URL", "http://192.168.0.188:8001")
SAMPLE_RATE = 24000

# Use the correct HF model path
MODEL_ID = "kmhf/hf-moshiko"

try:
    import torch
    import websockets
    from websockets.server import serve
    import httpx
    from transformers import MoshiForConditionalGeneration, AutoFeatureExtractor, AutoTokenizer
    import scipy.io.wavfile as wavfile
except ImportError as e:
    logger.error(f"Missing dependency: {e}")
    logger.error("Install with: pip install transformers accelerate scipy sentencepiece protobuf")
    sys.exit(1)

# Check GPU
if torch.cuda.is_available():
    DEVICE = "cuda"
    logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
    logger.info(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB")
else:
    DEVICE = "cpu"
    logger.warning("No GPU - running on CPU (slow)")

class MoshiNativeModel:
    def __init__(self):
        self.model = None
        self.feature_extractor = None
        self.tokenizer = None
        self.loaded = False
        
    async def load(self):
        if self.loaded:
            return True
            
        logger.info(f"Loading Moshi model from {MODEL_ID}...")
        try:
            # Load tokenizer
            logger.info("Loading tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
            
            # Load feature extractor
            logger.info("Loading feature extractor...")
            self.feature_extractor = AutoFeatureExtractor.from_pretrained(MODEL_ID)
            
            # Load model
            logger.info("Loading MoshiForConditionalGeneration (this takes time)...")
            self.model = MoshiForConditionalGeneration.from_pretrained(
                MODEL_ID,
                torch_dtype=torch.bfloat16 if DEVICE == "cuda" else torch.float32,
                device_map=DEVICE
            )
            self.model.eval()
            
            logger.info("Moshi model loaded successfully with native voice!")
            self.loaded = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to load Moshi model: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def generate_response(self, text_prompt):
        """Generate text and audio response using Moshi's native voice"""
        if not self.loaded:
            return None, None
            
        try:
            with torch.no_grad():
                # Get unconditional inputs
                unconditional = self.model.get_unconditional_inputs(num_samples=1)
                
                # Prepare text input
                input_ids = self.tokenizer(text_prompt, return_tensors="pt").input_ids.to(DEVICE)
                
                # Match length to audio tokens
                num_tokens = unconditional["moshi_audio_codes"].shape[-1]
                pad_token = self.tokenizer.pad_token_id or 0
                
                if input_ids.shape[-1] < num_tokens:
                    pad_length = num_tokens - input_ids.shape[-1]
                    padding = torch.full((1, pad_length), pad_token, dtype=input_ids.dtype, device=DEVICE)
                    input_ids = torch.cat([input_ids, padding], dim=-1)
                else:
                    input_ids = input_ids[:, :num_tokens]
                
                # Generate with audio output
                logger.info("Generating response with native Moshi voice...")
                output = self.model.generate(
                    input_ids=input_ids,
                    moshi_audio_codes=unconditional["moshi_audio_codes"].to(DEVICE),
                    user_audio_codes=unconditional["user_audio_codes"].to(DEVICE),
                    max_new_tokens=150,
                    return_audio_waveforms=True
                )
                
                # Extract text
                text_tokens = output.sequences
                response_text = self.tokenizer.decode(text_tokens[0], skip_special_tokens=True)
                logger.info(f"Generated text: {response_text[:100]}...")
                
                # Extract audio waveform
                audio_waveform = output.audio_sequences
                if audio_waveform is not None and audio_waveform.numel() > 0:
                    audio_np = audio_waveform[0, 0].cpu().float().numpy()
                    logger.info(f"Generated audio: {len(audio_np)} samples at {SAMPLE_RATE}Hz")
                    return response_text, audio_np
                    
                return response_text, None
                
        except Exception as e:
            logger.error(f"Generation error: {e}")
            import traceback
            traceback.print_exc()
            return None, None

class FullDuplexServer:
    def __init__(self):
        self.model = MoshiNativeModel()
        self.sessions = {}
        self.http = None
        
    async def get_http(self):
        if self.http is None:
            self.http = httpx.AsyncClient(timeout=30.0)
        return self.http
        
    async def start(self):
        loaded = await self.model.load()
        if not loaded:
            logger.error("Failed to load model - exiting")
            sys.exit(1)
            
        logger.info(f"Moshi Full-Duplex Server on ws://{HOST}:{PORT}")
        logger.info(f"Native voice synthesis: ENABLED")
        logger.info(f"Sample rate: {SAMPLE_RATE}Hz")
        
        async with serve(self.handle_ws, HOST, PORT):
            await asyncio.Future()
    
    async def handle_ws(self, ws):
        sid = str(uuid4())
        self.sessions[sid] = {"ws": ws, "turns": 0, "cid": str(uuid4())}
        logger.info(f"Session started: {sid}")
        
        await ws.send(json.dumps({
            "type": "connected",
            "session_id": sid,
            "sample_rate": SAMPLE_RATE,
            "native_voice": True,
            "device": DEVICE
        }))
        
        try:
            async for msg in ws:
                await self.handle_message(sid, msg)
        except Exception as e:
            logger.error(f"Session error: {e}")
        finally:
            logger.info(f"Session ended: {sid}")
            if sid in self.sessions:
                del self.sessions[sid]
    
    async def handle_message(self, sid, msg):
        session = self.sessions[sid]
        ws = session["ws"]
        
        if isinstance(msg, bytes):
            await ws.send(json.dumps({"type": "audio_received", "bytes": len(msg)}))
        else:
            data = json.loads(msg)
            if data.get("type") == "text_input":
                await self.process_text(sid, data.get("text", ""))
            elif data.get("type") == "ping":
                await ws.send(json.dumps({"type": "pong"}))
    
    async def process_text(self, sid, user_text):
        session = self.sessions[sid]
        ws = session["ws"]
        session["turns"] += 1
        
        await ws.send(json.dumps({"type": "user_text", "text": user_text}))
        
        # Generate with native Moshi
        response_text, audio_waveform = self.model.generate_response(user_text)
        
        if response_text:
            await ws.send(json.dumps({
                "type": "agent_text", 
                "text": response_text,
                "backend": "moshi-native"
            }))
            
            if audio_waveform is not None:
                # Convert to WAV
                audio_int16 = (np.clip(audio_waveform, -1, 1) * 32767).astype(np.int16)
                wav_buffer = io.BytesIO()
                wavfile.write(wav_buffer, SAMPLE_RATE, audio_int16)
                wav_bytes = wav_buffer.getvalue()
                await ws.send(wav_bytes)
                logger.info(f"Sent WAV audio: {len(wav_bytes)} bytes")
        else:
            # Fallback
            response = await self.call_mas(session, user_text)
            await ws.send(json.dumps({"type": "agent_text", "text": response, "backend": "mas-fallback"}))
        
        await ws.send(json.dumps({"type": "speaking_done", "turn": session["turns"]}))
    
    async def call_mas(self, session, text):
        try:
            http = await self.get_http()
            r = await http.post(f"{MAS_URL}/voice/orchestrator/chat", json={
                "message": text, "conversation_id": session["cid"], "source": "personaplex"
            })
            if r.status_code == 200:
                return r.json().get("response_text", "I heard you.")
        except Exception as e:
            logger.error(f"MAS error: {e}")
        return f"I heard: {text}"

if __name__ == "__main__":
    asyncio.run(FullDuplexServer().start())
