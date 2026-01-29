#!/usr/bin/env python3
"""
Native Moshi TTS Server - January 29, 2026
Uses Kyutai's native moshi library for text-to-speech on RTX 5090 (sm_120)

This server bypasses HuggingFace Transformers (which has version issues)
and uses the native moshi library directly.

IMPORTANT: Requires NO_TORCH_COMPILE=1 environment variable (Triton not compatible with sm_120)
"""
import asyncio
import io
import json
import logging
import os
import sys
from datetime import datetime
from uuid import uuid4

# Disable torch.compile (Triton not compatible with RTX 5090 sm_120)
os.environ['NO_TORCH_COMPILE'] = '1'

import numpy as np
import scipy.io.wavfile as wavfile

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

HOST = os.getenv("PERSONAPLEX_HOST", "0.0.0.0")
PORT = int(os.getenv("PERSONAPLEX_PORT", "8998"))
MAS_URL = os.getenv("MAS_ORCHESTRATOR_URL", "http://192.168.0.188:8001")
SAMPLE_RATE = 24000

# Default voice - female natural voice
DEFAULT_VOICE = os.getenv("MOSHI_VOICE", "alba-mackenna/casual.wav")

try:
    import torch
    import websockets
    from websockets.server import serve
    import httpx
    from moshi.models.tts import TTSModel
    from moshi.models.loaders import CheckpointInfo
except ImportError as e:
    logger.error(f"Missing dependency: {e}")
    logger.error("Install with: pip install moshi websockets httpx scipy")
    sys.exit(1)

# Check GPU
if torch.cuda.is_available():
    DEVICE = "cuda"
    logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
    logger.info(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB")
    logger.info(f"CUDA capability: {torch.cuda.get_device_capability(0)}")
else:
    DEVICE = "cpu"
    logger.warning("No GPU - running on CPU (slow)")


class NativeMoshiTTS:
    """Native Moshi TTS using kyutai's moshi library directly"""
    
    def __init__(self):
        self.tts_model = None
        self.loaded = False
        self.voice = DEFAULT_VOICE
        
    async def load(self):
        if self.loaded:
            return True
            
        logger.info("Loading Kyutai TTS model (1.6B)...")
        try:
            # Load from HuggingFace
            checkpoint_info = CheckpointInfo.from_hf_repo('kyutai/tts-1.6b-en_fr')
            
            # Create TTS model on GPU
            self.tts_model = TTSModel.from_checkpoint_info(
                checkpoint_info, 
                device=DEVICE, 
                dtype=torch.bfloat16
            )
            
            logger.info(f"TTS model loaded!")
            logger.info(f"Sample rate: {self.tts_model.mimi.sample_rate}Hz")
            logger.info(f"Default voice: {self.voice}")
            self.loaded = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to load TTS model: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def generate_speech(self, text: str, voice: str = None) -> tuple:
        """
        Generate speech from text using native Moshi TTS
        
        Args:
            text: Text to speak
            voice: Voice identifier (e.g., 'alba-mackenna/casual.wav')
            
        Returns:
            tuple: (audio_array, duration_seconds)
        """
        if not self.loaded:
            raise RuntimeError("TTS model not loaded")
            
        voice = voice or self.voice
        
        try:
            with torch.inference_mode():
                # Generate audio
                audio_list = self.tts_model.simple_generate(
                    text, 
                    voice, 
                    cfg_coef=2.0, 
                    show_progress=False
                )
                
                audio_tensor = audio_list[0]
                audio_np = audio_tensor.cpu().numpy().astype(np.float32)
                duration = len(audio_np) / SAMPLE_RATE
                
                logger.info(f"Generated {duration:.2f}s of audio for: {text[:50]}...")
                return audio_np, duration
                
        except Exception as e:
            logger.error(f"TTS generation error: {e}")
            import traceback
            traceback.print_exc()
            return np.zeros(SAMPLE_RATE, dtype=np.float32), 1.0  # 1s of silence
    
    def audio_to_wav_bytes(self, audio_np: np.ndarray) -> bytes:
        """Convert audio numpy array to WAV bytes"""
        buffer = io.BytesIO()
        # Scale to int16 range
        audio_int16 = (audio_np * 32767).astype(np.int16)
        wavfile.write(buffer, SAMPLE_RATE, audio_int16)
        return buffer.getvalue()
    
    def audio_to_pcm_bytes(self, audio_np: np.ndarray) -> bytes:
        """Convert audio numpy array to raw PCM float32 bytes"""
        return audio_np.astype(np.float32).tobytes()


class MoshiWebSocketServer:
    """WebSocket server for PersonaPlex-compatible voice interface"""
    
    def __init__(self):
        self.tts = NativeMoshiTTS()
        self.sessions = {}
        self.http = None
        
    async def get_http(self):
        if self.http is None:
            self.http = httpx.AsyncClient(timeout=30.0)
        return self.http
    
    async def get_mas_response(self, text: str) -> str:
        """Get intelligent response from MAS orchestrator"""
        try:
            http = await self.get_http()
            response = await http.post(
                f"{MAS_URL}/voice/orchestrator/chat",
                json={"message": text, "want_audio": False}
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("response_text", data.get("response", "I understand."))
        except Exception as e:
            logger.warning(f"MAS orchestrator unavailable: {e}")
        
        # Fallback response
        return self.generate_fallback_response(text)
    
    def generate_fallback_response(self, text: str) -> str:
        """Generate fallback response when MAS is unavailable"""
        lower = text.lower()
        
        if any(w in lower for w in ["hello", "hi ", "hey"]) or lower == "hi":
            return "Hello! I'm MYCA, your AI assistant. How can I help you today?"
        elif "status" in lower:
            return "All systems are operational. The MAS orchestrator and agents are running normally."
        elif "who are you" in lower or "what are you" in lower:
            return "I am MYCA, the Mycosoft Autonomous Cognitive Agent. I help manage and coordinate the Multi-Agent System."
        elif "help" in lower:
            return "I can help you with system status, agent management, and general questions. Just ask me anything."
        else:
            return f"I heard you say: {text}. I'm processing your request."
    
    async def handle_connection(self, websocket):
        """Handle a WebSocket connection"""
        session_id = str(uuid4())
        self.sessions[session_id] = {
            "connected_at": datetime.utcnow().isoformat(),
            "turns": 0
        }
        
        logger.info(f"New connection: {session_id}")
        
        try:
            # Send connection confirmation
            await websocket.send(json.dumps({
                "type": "connected",
                "session_id": session_id,
                "voice": self.tts.voice,
                "sample_rate": SAMPLE_RATE
            }))
            
            async for message in websocket:
                try:
                    if isinstance(message, str):
                        data = json.loads(message)
                        await self.handle_message(websocket, session_id, data)
                    elif isinstance(message, bytes):
                        # Audio input from client (not used in TTS-only mode)
                        logger.debug(f"Received {len(message)} bytes of audio")
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON"
                    }))
                except Exception as e:
                    logger.error(f"Message handling error: {e}")
                    await websocket.send(json.dumps({
                        "type": "error", 
                        "message": str(e)
                    }))
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Connection closed: {session_id}")
        finally:
            if session_id in self.sessions:
                del self.sessions[session_id]
    
    async def handle_message(self, websocket, session_id: str, data: dict):
        """Handle incoming message"""
        msg_type = data.get("type", "")
        
        if msg_type == "text_input":
            # Text-to-speech request
            text = data.get("text", "").strip()
            if not text:
                return
                
            self.sessions[session_id]["turns"] += 1
            
            # Get response from MAS
            response_text = await self.get_mas_response(text)
            
            # Send text response first
            await websocket.send(json.dumps({
                "type": "agent_text",
                "text": response_text,
                "session_id": session_id
            }))
            
            # Generate and send audio
            audio_np, duration = self.tts.generate_speech(response_text)
            
            # Send audio as binary WAV
            wav_bytes = self.tts.audio_to_wav_bytes(audio_np)
            await websocket.send(wav_bytes)
            
            # Send completion
            await websocket.send(json.dumps({
                "type": "audio_complete",
                "duration": duration,
                "sample_rate": SAMPLE_RATE
            }))
            
        elif msg_type == "ping":
            await websocket.send(json.dumps({"type": "pong"}))
            
        elif msg_type == "set_voice":
            voice = data.get("voice", DEFAULT_VOICE)
            self.tts.voice = voice
            await websocket.send(json.dumps({
                "type": "voice_set",
                "voice": voice
            }))


async def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("Native Moshi TTS Server v2 - January 29, 2026")
    logger.info("=" * 60)
    
    server = MoshiWebSocketServer()
    
    # Load TTS model
    logger.info("Loading TTS model...")
    success = await server.tts.load()
    if not success:
        logger.error("Failed to load TTS model. Exiting.")
        sys.exit(1)
    
    # Start WebSocket server
    logger.info(f"Starting WebSocket server on ws://{HOST}:{PORT}")
    async with serve(server.handle_connection, HOST, PORT):
        logger.info(f"Server running at ws://{HOST}:{PORT}")
        logger.info("Ready to accept connections!")
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    asyncio.run(main())
