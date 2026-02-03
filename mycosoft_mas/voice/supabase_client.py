"""Supabase Voice Session Store - February 3, 2026

Persists voice sessions to Supabase/PostgreSQL for the memory system.
Integrates with PersonaPlex bridge for session tracking.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger("VoiceSessionStore")


class VoiceSessionStore:
    """Persist voice sessions to Supabase/PostgreSQL."""
    
    def __init__(self):
        self._pool = None
        self._url = os.getenv("DATABASE_URL", os.getenv("SUPABASE_DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/mycosoft"))
    
    async def connect(self) -> bool:
        try:
            import asyncpg
            self._pool = await asyncpg.create_pool(self._url, min_size=1, max_size=5)
            logger.info("VoiceSessionStore connected to database")
            return True
        except Exception as e:
            logger.error(f"VoiceSessionStore connection failed: {e}")
            return False
    
    async def disconnect(self) -> None:
        if self._pool:
            await self._pool.close()
            self._pool = None
    
    async def create_session(
        self,
        session_id: str,
        conversation_id: str,
        mode: str = "personaplex",
        persona: str = "myca",
        user_id: Optional[str] = None,
        voice_prompt: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        if not self._pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO memory.voice_sessions 
                        (session_id, conversation_id, mode, persona, user_id, voice_prompt, metadata)
                    VALUES ($1, $2, $3, $4, $5::uuid, $6, $7)
                    ON CONFLICT (session_id) DO UPDATE SET
                        is_active = TRUE,
                        metadata = memory.voice_sessions.metadata || EXCLUDED.metadata
                ''', session_id, conversation_id, mode, persona,
                    user_id, voice_prompt, metadata or {})
            logger.info(f"Created voice session: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            return False
    
    async def add_turn(
        self,
        session_id: str,
        speaker: str,
        text: str,
        duration_ms: Optional[int] = None,
        latency_ms: Optional[int] = None,
        confidence: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        if not self._pool:
            await self.connect()
        
        turn_id = str(uuid4())
        try:
            async with self._pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO memory.voice_turns 
                        (turn_id, session_id, speaker, text, duration_ms, latency_ms, confidence, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ''', turn_id, session_id, speaker, text, duration_ms, latency_ms, confidence, metadata or {})
                
                await conn.execute('''
                    UPDATE memory.voice_sessions 
                    SET turn_count = turn_count + 1
                    WHERE session_id = $1
                ''', session_id)
            return turn_id
        except Exception as e:
            logger.error(f"Failed to add turn: {e}")
            return None
    
    async def log_tool_invocation(
        self,
        session_id: str,
        agent: str,
        action: str,
        status: str = "pending",
        turn_id: Optional[str] = None,
        input_params: Optional[Dict[str, Any]] = None,
        result: Optional[Dict[str, Any]] = None,
        latency_ms: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> Optional[str]:
        if not self._pool:
            await self.connect()
        
        invocation_id = str(uuid4())
        try:
            async with self._pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO memory.voice_tool_invocations 
                        (invocation_id, session_id, turn_id, agent, action, status, 
                         input_params, result, latency_ms, error_message,
                         completed_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                         CASE WHEN $6 IN ('success', 'error', 'cancelled') THEN NOW() ELSE NULL END)
                ''', invocation_id, session_id, turn_id, agent, action, status,
                    input_params or {}, result, latency_ms, error_message)
                
                if status in ('success', 'error'):
                    await conn.execute('''
                        UPDATE memory.voice_sessions 
                        SET tool_count = tool_count + 1
                        WHERE session_id = $1
                    ''', session_id)
            return invocation_id
        except Exception as e:
            logger.error(f"Failed to log tool invocation: {e}")
            return None
    
    async def log_barge_in(
        self,
        session_id: str,
        cancelled_text: Optional[str] = None,
        cancelled_at_position_ms: Optional[int] = None,
        user_intent: Optional[str] = None
    ) -> Optional[str]:
        if not self._pool:
            await self.connect()
        
        event_id = str(uuid4())
        try:
            async with self._pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO memory.voice_barge_in_events 
                        (event_id, session_id, cancelled_text, cancelled_at_position_ms, user_intent)
                    VALUES ($1, $2, $3, $4, $5)
                ''', event_id, session_id, cancelled_text, cancelled_at_position_ms, user_intent)
            return event_id
        except Exception as e:
            logger.error(f"Failed to log barge-in: {e}")
            return None
    
    async def end_session(
        self,
        session_id: str,
        summary: Optional[str] = None
    ) -> bool:
        if not self._pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                await conn.execute("SELECT memory.end_voice_session($1, $2)", session_id, summary)
            logger.info(f"Ended voice session: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to end session: {e}")
            return False
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        if not self._pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow('''
                    SELECT * FROM memory.voice_sessions WHERE session_id = $1
                ''', session_id)
                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error(f"Failed to get session: {e}")
            return None
    
    async def get_session_with_turns(self, session_id: str) -> Optional[Dict[str, Any]]:
        if not self._pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow('''
                    SELECT * FROM memory.get_session_with_turns($1)
                ''', session_id)
                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error(f"Failed to get session with turns: {e}")
            return None
    
    async def get_user_sessions(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        if not self._pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT session_id, conversation_id, mode, persona, 
                           turn_count, tool_count, started_at, ended_at, is_active
                    FROM memory.voice_sessions 
                    WHERE user_id = $1::uuid
                    ORDER BY started_at DESC
                    LIMIT $2
                ''', user_id, limit)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get user sessions: {e}")
            return []
    
    async def get_session_stats(self) -> Dict[str, Any]:
        if not self._pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM memory.voice_session_stats")
                if row:
                    return dict(row)
                return {}
        except Exception as e:
            logger.error(f"Failed to get session stats: {e}")
            return {}


_voice_store: Optional[VoiceSessionStore] = None


def get_voice_store() -> VoiceSessionStore:
    global _voice_store
    if _voice_store is None:
        _voice_store = VoiceSessionStore()
    return _voice_store


async def init_voice_store() -> VoiceSessionStore:
    store = get_voice_store()
    await store.connect()
    return store
