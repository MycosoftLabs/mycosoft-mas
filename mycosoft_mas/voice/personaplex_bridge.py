"""
PersonaPlex Duplex Bridge - January 27, 2026
Connects PersonaPlex full-duplex voice to MAS orchestrator
"""
import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4
import aiohttp

logger = logging.getLogger(__name__)

class Intent(Enum):
    CHITCHAT = "chitchat"
    ACTION_NEEDED = "action_needed"
    CONFIRMATION_REQUIRED = "confirmation_required"
    UNKNOWN = "unknown"

@dataclass
class DuplexSession:
    session_id: str
    conversation_id: str
    persona: str = "myca"
    voice_prompt: str = "NATF2.pt"
    mode: str = "personaplex"
    started_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    turns: list = field(default_factory=list)
    tool_invocations: list = field(default_factory=list)
    barge_in_events: list = field(default_factory=list)
    is_active: bool = True
    
    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "conversation_id": self.conversation_id,
            "persona": self.persona,
            "voice_prompt": self.voice_prompt,
            "mode": self.mode,
            "started_at": self.started_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "turn_count": len(self.turns),
            "tool_count": len(self.tool_invocations),
            "is_active": self.is_active,
        }

class PersonaPlexBridge:
    def __init__(self, personaplex_url=None, mas_url=None, n8n_url=None):
        self.personaplex_url = personaplex_url or os.getenv("PERSONAPLEX_URL", "wss://localhost:8998")
        self.mas_url = mas_url or os.getenv("MAS_ORCHESTRATOR_URL", "http://192.168.0.188:8001")
        self.n8n_url = n8n_url or os.getenv("N8N_WEBHOOK_URL", "http://192.168.0.188:5678/webhook")
        self.sessions: dict[str, DuplexSession] = {}
        self._http: Optional[aiohttp.ClientSession] = None
        self.action_keywords = ["turn on", "turn off", "set", "create", "delete", "start", "stop", "run", "check", "status"]
        self.confirm_keywords = ["delete", "remove", "destroy", "shutdown", "restart all", "clear", "reset"]
    
    async def get_http(self):
        if not self._http or self._http.closed:
            self._http = aiohttp.ClientSession()
        return self._http
    
    async def close(self):
        if self._http and not self._http.closed:
            await self._http.close()
    
    def create_session(self, conversation_id=None, persona="myca", voice_prompt="NATF2.pt"):
        session = DuplexSession(
            session_id=str(uuid4()),
            conversation_id=conversation_id or str(uuid4()),
            persona=persona,
            voice_prompt=voice_prompt,
        )
        self.sessions[session.session_id] = session
        return session
    
    def get_session(self, session_id: str):
        return self.sessions.get(session_id)
    
    def end_session(self, session_id: str):
        if session_id in self.sessions:
            self.sessions[session_id].is_active = False
    
    def classify_intent(self, text: str) -> Intent:
        text_lower = text.lower()
        for kw in self.confirm_keywords:
            if kw in text_lower:
                return Intent.CONFIRMATION_REQUIRED
        for kw in self.action_keywords:
            if kw in text_lower:
                return Intent.ACTION_NEEDED
        return Intent.CHITCHAT
    
    async def handle_agent_text(self, session_id: str, agent_text: str, user_text=None):
        session = self.get_session(session_id)
        if not session:
            return None
        session.last_activity = datetime.utcnow()
        session.turns.append({"timestamp": datetime.utcnow().isoformat(), "user": user_text, "agent": agent_text})
        intent = self.classify_intent(agent_text)
        if intent == Intent.CHITCHAT:
            return None
        if intent == Intent.CONFIRMATION_REQUIRED:
            return "This action requires confirmation. Should I proceed?"
        if intent == Intent.ACTION_NEEDED:
            return await self._execute_tool(session, agent_text, user_text)
        return None
    
    async def _execute_tool(self, session, agent_text, user_text):
        start = time.time()
        try:
            http = await self.get_http()
            payload = {"message": user_text or agent_text, "conversation_id": session.conversation_id, "want_audio": False, "source": "personaplex"}
            async with http.post(f"{self.mas_url}/voice/orchestrator/chat", json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    latency = (time.time() - start) * 1000
                    session.tool_invocations.append({"timestamp": datetime.utcnow().isoformat(), "agent": result.get("agent"), "latency_ms": latency, "status": "success"})
                    return result.get("response_text", "Action completed.")
                return "I encountered an issue executing that action."
        except Exception as e:
            logger.error(f"Tool error: {e}")
            return "I had trouble executing that action."
    
    def get_active_sessions(self):
        return [s.to_dict() for s in self.sessions.values() if s.is_active]
    
    def get_stats(self):
        active = [s for s in self.sessions.values() if s.is_active]
        return {"active_sessions": len(active), "total_sessions": len(self.sessions)}

_bridge = None
def get_bridge():
    global _bridge
    if not _bridge:
        _bridge = PersonaPlexBridge()
    return _bridge
