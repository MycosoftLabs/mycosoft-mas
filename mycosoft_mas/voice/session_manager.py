"""Voice Session Manager - January 27, 2026"""
import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4
import aiohttp

logger = logging.getLogger(__name__)

class VoiceMode(Enum):
    PERSONAPLEX = "personaplex"
    ELEVENLABS = "elevenlabs"
    AUTO = "auto"

@dataclass
class VoiceConfig:
    mode: VoiceMode = VoiceMode.AUTO
    voice_prompt: str = "NATF2.pt"
    voice_id: str = "aEO01A4wXwd1O8GPgGlF"
    persona: str = "myca"
    fallback_enabled: bool = True

class VoiceSessionManager:
    def __init__(self):
        self.personaplex_url = os.getenv("PERSONAPLEX_URL", "wss://localhost:8998")
        self.personaplex_available = False
        self._check_task = None
    
    async def start(self):
        self._check_task = asyncio.create_task(self._check_loop())
        await self.check_personaplex()
    
    async def stop(self):
        if self._check_task:
            self._check_task.cancel()
    
    async def _check_loop(self):
        while True:
            await asyncio.sleep(30)
            await self.check_personaplex()
    
    async def check_personaplex(self) -> bool:
        try:
            url = self.personaplex_url.replace("wss://", "https://").replace("ws://", "http://")
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5), ssl=False) as resp:
                    self.personaplex_available = resp.status == 200
        except:
            self.personaplex_available = False
        return self.personaplex_available
    
    def get_mode(self, config=None):
        if config and config.mode != VoiceMode.AUTO:
            return config.mode
        return VoiceMode.PERSONAPLEX if self.personaplex_available else VoiceMode.ELEVENLABS
    
    def get_transport(self, mode):
        if mode == VoiceMode.PERSONAPLEX:
            return {"type": "websocket", "url": self.personaplex_url, "sample_rate": 24000}
        return {"type": "http", "tts_url": "/api/mas/voice", "orchestrator_url": "/api/mas/voice/orchestrator"}
    
    def create_session(self, conversation_id, config=None):
        config = config or VoiceConfig()
        mode = self.get_mode(config)
        return {
            "conversation_id": conversation_id,
            "session_id": str(uuid4()),
            "mode": mode.value,
            "personaplex_available": self.personaplex_available,
            "transport": self.get_transport(mode),
            "fallback": self.get_transport(VoiceMode.ELEVENLABS) if config.fallback_enabled else None,
            "created_at": datetime.utcnow().isoformat(),
        }

_manager = None
def get_session_manager():
    global _manager
    if not _manager:
        _manager = VoiceSessionManager()
    return _manager
