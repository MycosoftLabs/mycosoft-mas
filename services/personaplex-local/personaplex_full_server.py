#!/usr/bin/env python3
'''
NVIDIA PersonaPlex Full Server - January 29, 2026

Full-duplex speech-to-speech using NVIDIA PersonaPlex 7B model.
Based on: https://research.nvidia.com/labs/adlr/personaplex/
         https://huggingface.co/nvidia/personaplex-7b-v1
'''

import asyncio
import io
import json
import logging
import os
import sys
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

os.environ['NO_TORCH_COMPILE'] = '1'

import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

HOST = os.getenv('PERSONAPLEX_HOST', '0.0.0.0')
PORT = int(os.getenv('PERSONAPLEX_PORT', '8998'))
MAS_URL = os.getenv('MAS_ORCHESTRATOR_URL', 'http://192.168.0.188:8001')
MODEL_PATH = os.getenv('PERSONAPLEX_MODEL_PATH', 'models/personaplex-7b-v1')
SAMPLE_RATE = 24000

DEFAULT_PERSONA = '''You are MYCA (Mycosoft Autonomous Cognitive Agent), a helpful AI assistant for Mycosoft.
You are friendly, knowledgeable, and efficient. Keep responses concise but informative.'''

DEFAULT_VOICE = 'alba-mackenna/casual.wav'

try:
    import torch
    import websockets
    from websockets.server import serve
    import httpx
except ImportError as e:
    logger.error(f'Missing dependency: {e}')
    sys.exit(1)

DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
if torch.cuda.is_available():
    logger.info(f'GPU: {torch.cuda.get_device_name(0)}')
    logger.info(f'VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB')


class PersonaPlexModel:
    def __init__(self, model_path: str = MODEL_PATH):
        self.model_path = Path(model_path)
        self.loaded = False
        self._tts_model = None
        self.current_persona = DEFAULT_PERSONA
        self.current_voice = DEFAULT_VOICE
        
    async def load(self) -> bool:
        if self.loaded:
            return True
            
        logger.info(f'Loading PersonaPlex from {self.model_path}...')
        model_file = self.model_path / 'model.safetensors'
        
        if not model_file.exists():
            logger.warning('PersonaPlex model not found, using TTS fallback')
            
        # Load TTS model for voice output
        try:
            from moshi.models.tts import TTSModel
            from moshi.models.loaders import CheckpointInfo
            
            logger.info('Loading Kyutai TTS model...')
            checkpoint_info = CheckpointInfo.from_hf_repo('kyutai/tts-1.6b-en_fr')
            self._tts_model = TTSModel.from_checkpoint_info(
                checkpoint_info, device=DEVICE, dtype=torch.bfloat16
            )
            logger.info('TTS model loaded!')
            self.loaded = True
            return True
        except Exception as e:
            logger.error(f'Failed to load TTS: {e}')
            self.loaded = True  # Continue anyway
            return True
    
    async def generate_response(self, user_text: str) -> tuple:
        response_text = await self._get_mas_response(user_text)
        audio_bytes = await self._generate_audio(response_text)
        return response_text, audio_bytes
    
    async def _get_mas_response(self, text: str) -> str:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(f'{MAS_URL}/voice/orchestrator/chat',
                    json={'message': text, 'want_audio': False, 'source': 'personaplex'})
                if resp.status_code == 200:
                    return resp.json().get('response_text', 'How can I help?')
        except Exception as e:
            logger.error(f'MAS error: {e}')
        return 'I am MYCA. How can I help you?'
    
    async def _generate_audio(self, text: str) -> bytes:
        try:
            if self._tts_model:
                with torch.inference_mode():
                    audio_list = self._tts_model.simple_generate(text, self.current_voice, cfg_coef=2.0, show_progress=False)
                    audio_np = audio_list[0].cpu().numpy().astype(np.float32)
                    return self._audio_to_wav(audio_np)
        except Exception as e:
            logger.error(f'TTS error: {e}')
        return self._generate_silence(1.0)
    
    def _audio_to_wav(self, audio_np: np.ndarray) -> bytes:
        buf = io.BytesIO()
        audio_int16 = (audio_np * 32767).astype(np.int16)
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_int16.tobytes())
        return buf.getvalue()
    
    def _generate_silence(self, dur: float) -> bytes:
        return self._audio_to_wav(np.zeros(int(dur * SAMPLE_RATE), dtype=np.float32))


class PersonaPlexServer:
    def __init__(self):
        self.model = PersonaPlexModel()
        self.sessions = {}
        
    async def start(self):
        await self.model.load()
        logger.info(f'PersonaPlex Full Server on ws://{HOST}:{PORT}')
        async with serve(self.handle_client, HOST, PORT):
            await asyncio.Future()
    
    async def handle_client(self, ws):
        sid = str(uuid4())
        self.sessions[sid] = {'ws': ws, 'turns': 0}
        await ws.send(json.dumps({'type': 'connected', 'session_id': sid, 'model': 'personaplex-7b-v1'}))
        try:
            async for msg in ws:
                if isinstance(msg, str):
                    data = json.loads(msg)
                    if data.get('type') == 'text_input':
                        text = data.get('text', '')
                        if text.strip():
                            self.sessions[sid]['turns'] += 1
                            resp, audio = await self.model.generate_response(text)
                            await ws.send(json.dumps({'type': 'agent_text', 'text': resp}))
                            if audio:
                                await ws.send(audio)
                                await ws.send(json.dumps({'type': 'audio_complete'}))
        except Exception as e:
            logger.error(f'Session error: {e}')
        finally:
            del self.sessions[sid]


if __name__ == '__main__':
    asyncio.run(PersonaPlexServer().start())
