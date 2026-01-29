import asyncio
import io
import json
import logging
import os
import sys
import wave
import tempfile
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

os.environ['NO_TORCH_COMPILE'] = '1'

import numpy as np
import websockets
from websockets.server import serve
import httpx

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

HOST = '0.0.0.0'
PORT = 8997  # Different port to not conflict
MAS_URL = os.getenv('MAS_ORCHESTRATOR_URL', 'http://192.168.0.188:8001')
MODEL_PATH = 'models/personaplex-7b-v1'
VOICE_PROMPT = 'NATF2.pt'
SAMPLE_RATE = 24000
HF_TOKEN = os.getenv('HF_TOKEN', '$env:HF_TOKEN')

class PersonaPlexNATF2Server:
    def __init__(self):
        self.sessions = {}
        
    async def generate_audio_natf2(self, text: str) -> bytes:
        '''Generate audio using PersonaPlex with NATF2 voice via offline script'''
        try:
            # Create temp input wav with silence (we just want text-to-speech)
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                input_wav = f.name
                # 1 second of silence as input
                samples = np.zeros(SAMPLE_RATE, dtype=np.int16)
                with wave.open(f, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(SAMPLE_RATE)
                    wf.writeframes(samples.tobytes())
            
            output_wav = tempfile.mktemp(suffix='.wav')
            output_json = tempfile.mktemp(suffix='.json')
            
            # Run PersonaPlex offline
            cmd = [
                sys.executable, '-m', 'moshi.offline',
                '--voice-prompt', f'{MODEL_PATH}/voices/{VOICE_PROMPT}',
                '--text-prompt', f'You are MYCA. Respond: {text}',
                '--input-wav', input_wav,
                '--output-wav', output_wav,
                '--output-text', output_json,
                '--seed', '42424242'
            ]
            
            env = os.environ.copy()
            env['NO_TORCH_COMPILE'] = '1'
            env['HF_TOKEN'] = HF_TOKEN
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=env)
            
            if os.path.exists(output_wav):
                with open(output_wav, 'rb') as f:
                    audio_data = f.read()
                os.unlink(output_wav)
                if os.path.exists(output_json):
                    os.unlink(output_json)
                os.unlink(input_wav)
                return audio_data
            else:
                logger.error(f'PersonaPlex output not found: {result.stderr}')
                return b''
                
        except Exception as e:
            logger.error(f'PersonaPlex error: {e}')
            return b''
    
    async def handle_client(self, websocket):
        session_id = str(uuid4())
        self.sessions[session_id] = {'ws': websocket, 'turns': 0}
        
        await websocket.send(json.dumps({
            'type': 'connected',
            'session_id': session_id,
            'voice': 'NATF2 (PersonaPlex)',
            'model': 'personaplex-7b-v1'
        }))
        
        logger.info(f'Session started: {session_id}')
        
        try:
            async for message in websocket:
                if isinstance(message, str):
                    data = json.loads(message)
                    if data.get('type') == 'text_input':
                        text = data.get('text', '')
                        if text.strip():
                            # Get response from MAS
                            response_text = await self.get_mas_response(text)
                            
                            # Send text response
                            await websocket.send(json.dumps({
                                'type': 'agent_text',
                                'text': response_text
                            }))
                            
                            # Generate audio with NATF2
                            audio = await self.generate_audio_natf2(response_text)
                            if audio:
                                await websocket.send(audio)
                                await websocket.send(json.dumps({'type': 'audio_complete'}))
        except Exception as e:
            logger.error(f'Session error: {e}')
        finally:
            del self.sessions[session_id]
            logger.info(f'Session ended: {session_id}')
    
    async def get_mas_response(self, text: str) -> str:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(f'{MAS_URL}/voice/orchestrator/chat',
                    json={'message': text, 'want_audio': False, 'source': 'personaplex'})
                if resp.status_code == 200:
                    return resp.json().get('response_text', 'How can I help?')
        except Exception as e:
            logger.error(f'MAS error: {e}')
        return 'I am MYCA. How can I help you?'
    
    async def start(self):
        logger.info(f'PersonaPlex NATF2 Server starting on ws://{HOST}:{PORT}')
        async with serve(self.handle_client, HOST, PORT):
            await asyncio.Future()

if __name__ == '__main__':
    asyncio.run(PersonaPlexNATF2Server().start())
