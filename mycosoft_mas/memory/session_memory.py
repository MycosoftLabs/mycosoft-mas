"""
Session Memory - February 6, 2026

Per-session context and conversation state.
"""

import json
import logging
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import asyncpg
except ImportError:
    asyncpg = None


@dataclass
class ConversationMessage:
    """A message in conversation history."""
    role: str  # user, assistant, system
    content: str
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PendingAction:
    """An action awaiting confirmation."""
    id: str
    action_type: str
    description: str
    parameters: Dict[str, Any]
    created_at: str
    expires_at: str


@dataclass
class WorkingMemoryItem:
    """A fact in working memory."""
    id: str
    content: str
    source: str
    relevance: float
    added_at: str


@dataclass
class SessionMemory:
    """Session-specific memory and state."""
    session_id: str
    user_id: Optional[str] = None
    current_entities: List[Dict] = field(default_factory=list)
    current_region: Optional[Dict] = None
    current_time_range: Optional[Dict] = None
    current_layers: List[str] = field(default_factory=list)
    conversation_history: List[Dict] = field(default_factory=list)
    pending_actions: List[Dict] = field(default_factory=list)
    working_memory: List[Dict] = field(default_factory=list)
    started_at: Optional[str] = None
    updated_at: Optional[str] = None
    last_interaction_at: Optional[str] = None
    is_active: bool = True


class SessionMemoryManager:
    """Manages session memory persistence."""
    
    MAX_CONVERSATION_HISTORY = 100
    MAX_WORKING_MEMORY = 50
    SESSION_TIMEOUT_HOURS = 24
    
    def __init__(self, connection_string: Optional[str] = None):
        self.connection_string = connection_string or os.getenv(
            "DATABASE_URL",
            "postgresql://mycosoft:mycosoft@localhost:5432/mindex"
        )
        self.pool: Optional[asyncpg.Pool] = None
    
    async def initialize(self) -> None:
        if asyncpg is None:
            raise ImportError("asyncpg required")
        self.pool = await asyncpg.create_pool(self.connection_string, min_size=2, max_size=10)
    
    async def close(self) -> None:
        if self.pool:
            await self.pool.close()
    
    async def get_session(self, session_id: str) -> Optional[SessionMemory]:
        """Get session memory."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM mindex.session_memory WHERE session_id = $1",
                session_id
            )
            
            if not row:
                return None
            
            focus = row["current_focus"] or {}
            
            return SessionMemory(
                session_id=str(row["session_id"]),
                user_id=row["user_id"],
                current_entities=focus.get("entities", []),
                current_region=focus.get("region"),
                current_time_range=focus.get("time_range"),
                current_layers=focus.get("layers", []),
                conversation_history=row["conversation_history"] or [],
                pending_actions=row["pending_actions"] or [],
                working_memory=row["working_memory"] or [],
                started_at=row["started_at"].isoformat() if row["started_at"] else None,
                updated_at=row["updated_at"].isoformat() if row["updated_at"] else None,
                last_interaction_at=row["last_interaction_at"].isoformat() if row["last_interaction_at"] else None,
                is_active=row["is_active"],
            )
    
    async def create_session(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> SessionMemory:
        """Create new session."""
        sid = session_id or str(uuid.uuid4())
        
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO mindex.session_memory (session_id, user_id)
                VALUES ($1, $2)
                """,
                sid,
                user_id,
            )
        
        return await self.get_session(sid)
    
    async def update_session(self, session: SessionMemory) -> SessionMemory:
        """Update session memory."""
        focus = {
            "entities": session.current_entities,
            "region": session.current_region,
            "time_range": session.current_time_range,
            "layers": session.current_layers,
        }
        
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE mindex.session_memory
                SET user_id = $2,
                    current_focus = $3,
                    conversation_history = $4,
                    pending_actions = $5,
                    working_memory = $6,
                    last_interaction_at = NOW(),
                    is_active = $7
                WHERE session_id = $1
                """,
                session.session_id,
                session.user_id,
                json.dumps(focus),
                json.dumps(session.conversation_history[-self.MAX_CONVERSATION_HISTORY:]),
                json.dumps(session.pending_actions),
                json.dumps(session.working_memory[-self.MAX_WORKING_MEMORY:]),
                session.is_active,
            )
        
        return await self.get_session(session.session_id)
    
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None,
    ) -> None:
        """Add message to conversation history."""
        session = await self.get_session(session_id)
        if not session:
            session = await self.create_session(session_id)
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }
        
        session.conversation_history.append(message)
        await self.update_session(session)
    
    async def add_to_working_memory(
        self,
        session_id: str,
        content: str,
        source: str = "inferred",
        relevance: float = 0.8,
    ) -> None:
        """Add fact to working memory."""
        session = await self.get_session(session_id)
        if not session:
            session = await self.create_session(session_id)
        
        item = {
            "id": str(uuid.uuid4()),
            "content": content,
            "source": source,
            "relevance": relevance,
            "added_at": datetime.utcnow().isoformat(),
        }
        
        session.working_memory.append(item)
        await self.update_session(session)
    
    async def add_pending_action(
        self,
        session_id: str,
        action_type: str,
        description: str,
        parameters: Dict,
        expires_in_seconds: int = 300,
    ) -> str:
        """Add action requiring confirmation."""
        session = await self.get_session(session_id)
        if not session:
            session = await self.create_session(session_id)
        
        action_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        action = {
            "id": action_id,
            "action_type": action_type,
            "description": description,
            "parameters": parameters,
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=expires_in_seconds)).isoformat(),
        }
        
        session.pending_actions.append(action)
        await self.update_session(session)
        
        return action_id
    
    async def confirm_action(self, session_id: str, action_id: str) -> Optional[Dict]:
        """Confirm and remove a pending action."""
        session = await self.get_session(session_id)
        if not session:
            return None
        
        action = None
        for i, a in enumerate(session.pending_actions):
            if a["id"] == action_id:
                action = session.pending_actions.pop(i)
                break
        
        if action:
            await self.update_session(session)
        
        return action
    
    async def get_conversation_context(
        self,
        session_id: str,
        max_messages: int = 10,
    ) -> str:
        """Get conversation history as context string."""
        session = await self.get_session(session_id)
        if not session or not session.conversation_history:
            return ""
        
        messages = session.conversation_history[-max_messages:]
        return "\n".join(
            f"{m['role']}: {m['content']}"
            for m in messages
        )
    
    async def get_working_memory_context(self, session_id: str) -> str:
        """Get working memory as context string."""
        session = await self.get_session(session_id)
        if not session or not session.working_memory:
            return ""
        
        # Sort by relevance
        items = sorted(session.working_memory, key=lambda x: x["relevance"], reverse=True)
        return "\n".join(f"- {item['content']}" for item in items[:10])
    
    async def cleanup_inactive_sessions(self) -> int:
        """Mark old sessions as inactive."""
        cutoff = datetime.utcnow() - timedelta(hours=self.SESSION_TIMEOUT_HOURS)
        
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE mindex.session_memory
                SET is_active = FALSE
                WHERE is_active = TRUE
                AND last_interaction_at < $1
                """,
                cutoff
            )
            
            count = int(result.split()[-1]) if result else 0
            logger.info(f"Cleaned up {count} inactive sessions")
            return count


# Global instance
_session_manager: Optional[SessionMemoryManager] = None


async def get_session_manager() -> SessionMemoryManager:
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionMemoryManager()
        await _session_manager.initialize()
    return _session_manager