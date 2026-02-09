"""
PersonaPlex Voice Memory System.
Created: February 5, 2026

Provides specialized memory management for PersonaPlex voice sessions:
- Voice session persistence and restoration
- Conversation summarization and context
- Speaker recognition state
- Dialog history with turn tracking
- Emotional state memory
"""

import asyncio
import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

logger = logging.getLogger("PersonaPlexMemory")


class ConversationTurn:
    """A single turn in a conversation."""
    
    def __init__(
        self,
        role: str,  # "user" or "assistant"
        content: str,
        timestamp: Optional[datetime] = None,
        audio_hash: Optional[str] = None,
        duration_ms: Optional[int] = None,
        emotion: Optional[str] = None,
        confidence: float = 1.0
    ):
        self.id = uuid4()
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now(timezone.utc)
        self.audio_hash = audio_hash
        self.duration_ms = duration_ms
        self.emotion = emotion
        self.confidence = confidence
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "audio_hash": self.audio_hash,
            "duration_ms": self.duration_ms,
            "emotion": self.emotion,
            "confidence": self.confidence
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationTurn":
        turn = cls(
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            audio_hash=data.get("audio_hash"),
            duration_ms=data.get("duration_ms"),
            emotion=data.get("emotion"),
            confidence=data.get("confidence", 1.0)
        )
        turn.id = UUID(data["id"])
        return turn


@dataclass
class VoiceSession:
    """A voice conversation session."""
    id: UUID
    user_id: Optional[str] = None
    speaker_profile: Optional[str] = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: Optional[datetime] = None
    turns: List[ConversationTurn] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    summary: Optional[str] = None
    topics: List[str] = field(default_factory=list)
    emotional_arc: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> Optional[timedelta]:
        if self.ended_at:
            return self.ended_at - self.started_at
        return datetime.now(timezone.utc) - self.started_at
    
    @property
    def turn_count(self) -> int:
        return len(self.turns)
    
    def add_turn(
        self,
        role: str,
        content: str,
        audio_hash: Optional[str] = None,
        duration_ms: Optional[int] = None,
        emotion: Optional[str] = None
    ) -> ConversationTurn:
        """Add a conversation turn."""
        turn = ConversationTurn(
            role=role,
            content=content,
            audio_hash=audio_hash,
            duration_ms=duration_ms,
            emotion=emotion
        )
        self.turns.append(turn)
        
        # Track emotional arc
        if emotion:
            self.emotional_arc.append({
                "timestamp": turn.timestamp.isoformat(),
                "emotion": emotion,
                "turn_index": len(self.turns) - 1
            })
        
        return turn
    
    def get_recent_context(self, max_turns: int = 10) -> List[Dict[str, str]]:
        """Get recent conversation history for context."""
        recent = self.turns[-max_turns:] if len(self.turns) > max_turns else self.turns
        return [{"role": t.role, "content": t.content} for t in recent]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "speaker_profile": self.speaker_profile,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "turns": [t.to_dict() for t in self.turns],
            "context": self.context,
            "summary": self.summary,
            "topics": self.topics,
            "emotional_arc": self.emotional_arc,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VoiceSession":
        session = cls(
            id=UUID(data["id"]),
            user_id=data.get("user_id"),
            speaker_profile=data.get("speaker_profile"),
            started_at=datetime.fromisoformat(data["started_at"]),
            ended_at=datetime.fromisoformat(data["ended_at"]) if data.get("ended_at") else None,
            turns=[ConversationTurn.from_dict(t) for t in data.get("turns", [])],
            context=data.get("context", {}),
            summary=data.get("summary"),
            topics=data.get("topics", []),
            emotional_arc=data.get("emotional_arc", []),
            metadata=data.get("metadata", {})
        )
        return session


class ConversationSummarizer:
    """Summarizes conversations for long-term memory."""
    
    def __init__(self):
        self._llm_url = os.getenv("PERSONAPLEX_URL", "http://localhost:8999")
    
    async def summarize(self, session: VoiceSession) -> str:
        """Generate a summary of the conversation."""
        if not session.turns:
            return ""
        
        # Build conversation text
        conv_text = "\n".join([
            f"{t.role.upper()}: {t.content}"
            for t in session.turns
        ])
        
        # Try to use PersonaPlex for summarization
        try:
            import aiohttp
            async with aiohttp.ClientSession() as client:
                async with client.post(
                    f"{self._llm_url}/v1/chat/completions",
                    json={
                        "model": "moshi-7b",
                        "messages": [
                            {"role": "system", "content": "Summarize the following conversation in 2-3 sentences, capturing the key topics and outcomes."},
                            {"role": "user", "content": conv_text}
                        ],
                        "max_tokens": 150,
                        "temperature": 0.3
                    },
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"LLM summarization failed, using fallback: {e}")
        
        # Fallback: Simple extractive summary
        turn_count = len(session.turns)
        user_turns = sum(1 for t in session.turns if t.role == "user")
        
        # Get first and last user messages
        first_msg = next((t.content for t in session.turns if t.role == "user"), "")
        last_msg = next((t.content for t in reversed(session.turns) if t.role == "user"), "")
        
        return f"Conversation with {turn_count} turns ({user_turns} from user). Started with: '{first_msg[:50]}...' Ended with: '{last_msg[:50]}...'"
    
    async def extract_topics(self, session: VoiceSession) -> List[str]:
        """Extract main topics from conversation."""
        # Simple keyword extraction
        topics = set()
        
        # Common topic keywords
        topic_indicators = {
            "mushroom": ["mushroom", "fungi", "mycelium", "spore", "fruiting"],
            "grow": ["grow", "growth", "substrate", "harvest", "cultivation"],
            "environment": ["temperature", "humidity", "co2", "light", "environment"],
            "device": ["sensor", "camera", "controller", "device", "sporebase"],
            "help": ["help", "assist", "how", "what", "explain"],
            "status": ["status", "check", "monitor", "report"]
        }
        
        all_text = " ".join(t.content.lower() for t in session.turns)
        
        for topic, keywords in topic_indicators.items():
            if any(kw in all_text for kw in keywords):
                topics.add(topic)
        
        return list(topics)


class PersonaPlexMemory:
    """
    Memory system for PersonaPlex voice interactions.
    
    Provides:
    - Voice session management
    - Conversation history persistence
    - Context summarization
    - Speaker profile tracking
    - Cross-session memory
    """
    
    def __init__(self, database_url: Optional[str] = None):
        self._database_url = database_url or os.getenv(
            "MINDEX_DATABASE_URL",
            "postgresql://mycosoft:REDACTED_VM_SSH_PASSWORD@192.168.0.189:5432/mindex"
        )
        self._pool = None
        self._active_sessions: Dict[UUID, VoiceSession] = {}
        self._summarizer = ConversationSummarizer()
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the memory system."""
        if self._initialized:
            return
        
        try:
            import asyncpg
            self._pool = await asyncpg.create_pool(
                self._database_url,
                min_size=1,
                max_size=5
            )
            logger.info("PersonaPlex memory connected to database")
        except Exception as e:
            logger.warning(f"Database connection failed, using in-memory only: {e}")
        
        self._initialized = True
    
    async def start_session(
        self,
        user_id: Optional[str] = None,
        speaker_profile: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> VoiceSession:
        """Start a new voice session."""
        session = VoiceSession(
            id=uuid4(),
            user_id=user_id,
            speaker_profile=speaker_profile,
            context=context or {}
        )
        
        # Load previous session context if user identified
        if user_id:
            previous = await self.get_recent_sessions(user_id, limit=1)
            if previous:
                session.context["previous_session"] = {
                    "id": str(previous[0].id),
                    "summary": previous[0].summary,
                    "topics": previous[0].topics
                }
        
        self._active_sessions[session.id] = session
        logger.info(f"Started voice session {session.id}")
        return session
    
    async def add_turn(
        self,
        session_id: UUID,
        role: str,
        content: str,
        audio_hash: Optional[str] = None,
        duration_ms: Optional[int] = None,
        emotion: Optional[str] = None
    ) -> Optional[ConversationTurn]:
        """Add a turn to an active session."""
        session = self._active_sessions.get(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found")
            return None
        
        turn = session.add_turn(role, content, audio_hash, duration_ms, emotion)
        return turn
    
    async def end_session(self, session_id: UUID) -> Optional[VoiceSession]:
        """End a voice session and persist to storage."""
        session = self._active_sessions.pop(session_id, None)
        if not session:
            return None
        
        session.ended_at = datetime.now(timezone.utc)
        
        # Generate summary and extract topics
        session.summary = await self._summarizer.summarize(session)
        session.topics = await self._summarizer.extract_topics(session)
        
        # Persist to database
        await self._persist_session(session)
        
        logger.info(f"Ended voice session {session_id} ({session.turn_count} turns)")
        return session
    
    async def _persist_session(self, session: VoiceSession) -> bool:
        """Persist session to database."""
        if not self._pool:
            return False
        
        try:
            async with self._pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO voice.sessions (id, user_id, speaker_profile, started_at, 
                        ended_at, turns, context, summary, topics, emotional_arc, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7::jsonb, $8, $9, $10::jsonb, $11::jsonb)
                    ON CONFLICT (id) DO UPDATE SET
                        ended_at = EXCLUDED.ended_at,
                        turns = EXCLUDED.turns,
                        summary = EXCLUDED.summary,
                        topics = EXCLUDED.topics,
                        emotional_arc = EXCLUDED.emotional_arc
                """, str(session.id), session.user_id, session.speaker_profile,
                    session.started_at, session.ended_at,
                    json.dumps([t.to_dict() for t in session.turns]),
                    json.dumps(session.context), session.summary, session.topics,
                    json.dumps(session.emotional_arc), json.dumps(session.metadata))
            return True
        except Exception as e:
            logger.error(f"Failed to persist session: {e}")
            return False
    
    async def get_session(self, session_id: UUID) -> Optional[VoiceSession]:
        """Get a session by ID."""
        # Check active sessions first
        if session_id in self._active_sessions:
            return self._active_sessions[session_id]
        
        # Check database
        if not self._pool:
            return None
        
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM voice.sessions WHERE id = $1",
                    str(session_id)
                )
                if row:
                    return VoiceSession.from_dict({
                        "id": row["id"],
                        "user_id": row["user_id"],
                        "speaker_profile": row["speaker_profile"],
                        "started_at": row["started_at"].isoformat(),
                        "ended_at": row["ended_at"].isoformat() if row["ended_at"] else None,
                        "turns": json.loads(row["turns"]) if row["turns"] else [],
                        "context": json.loads(row["context"]) if row["context"] else {},
                        "summary": row["summary"],
                        "topics": row["topics"] or [],
                        "emotional_arc": json.loads(row["emotional_arc"]) if row["emotional_arc"] else [],
                        "metadata": json.loads(row["metadata"]) if row["metadata"] else {}
                    })
        except Exception as e:
            logger.error(f"Failed to get session: {e}")
        
        return None
    
    async def get_recent_sessions(
        self,
        user_id: str,
        limit: int = 10,
        since: Optional[datetime] = None
    ) -> List[VoiceSession]:
        """Get recent sessions for a user."""
        if not self._pool:
            return []
        
        try:
            async with self._pool.acquire() as conn:
                if since:
                    rows = await conn.fetch("""
                        SELECT * FROM voice.sessions 
                        WHERE user_id = $1 AND started_at >= $2
                        ORDER BY started_at DESC LIMIT $3
                    """, user_id, since, limit)
                else:
                    rows = await conn.fetch("""
                        SELECT * FROM voice.sessions 
                        WHERE user_id = $1
                        ORDER BY started_at DESC LIMIT $2
                    """, user_id, limit)
                
                sessions = []
                for row in rows:
                    sessions.append(VoiceSession.from_dict({
                        "id": row["id"],
                        "user_id": row["user_id"],
                        "speaker_profile": row["speaker_profile"],
                        "started_at": row["started_at"].isoformat(),
                        "ended_at": row["ended_at"].isoformat() if row["ended_at"] else None,
                        "turns": json.loads(row["turns"]) if row["turns"] else [],
                        "context": json.loads(row["context"]) if row["context"] else {},
                        "summary": row["summary"],
                        "topics": row["topics"] or [],
                        "emotional_arc": json.loads(row["emotional_arc"]) if row["emotional_arc"] else [],
                        "metadata": json.loads(row["metadata"]) if row["metadata"] else {}
                    }))
                return sessions
        except Exception as e:
            logger.error(f"Failed to get recent sessions: {e}")
        
        return []
    
    async def get_cross_session_context(self, user_id: str) -> Dict[str, Any]:
        """Get aggregated context across multiple sessions."""
        sessions = await self.get_recent_sessions(user_id, limit=5)
        
        if not sessions:
            return {"sessions_count": 0}
        
        # Aggregate topics
        all_topics = []
        for s in sessions:
            all_topics.extend(s.topics)
        topic_counts = {}
        for t in all_topics:
            topic_counts[t] = topic_counts.get(t, 0) + 1
        
        # Get conversation patterns
        avg_turns = sum(s.turn_count for s in sessions) / len(sessions)
        
        return {
            "sessions_count": len(sessions),
            "frequent_topics": sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            "avg_turns_per_session": round(avg_turns, 1),
            "last_session_summary": sessions[0].summary if sessions else None,
            "total_turns": sum(s.turn_count for s in sessions)
        }
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get memory system statistics."""
        active_count = len(self._active_sessions)
        total_active_turns = sum(s.turn_count for s in self._active_sessions.values())
        
        stats = {
            "active_sessions": active_count,
            "active_turns": total_active_turns,
            "database_connected": self._pool is not None,
            "initialized": self._initialized
        }
        
        if self._pool:
            try:
                async with self._pool.acquire() as conn:
                    row = await conn.fetchrow("SELECT COUNT(*) as total FROM voice.sessions")
                    stats["total_sessions"] = row["total"] if row else 0
            except:
                pass
        
        return stats


# Singleton instance
_personaplex_memory: Optional[PersonaPlexMemory] = None


async def get_personaplex_memory() -> PersonaPlexMemory:
    """Get or create the singleton PersonaPlex memory instance."""
    global _personaplex_memory
    if _personaplex_memory is None:
        _personaplex_memory = PersonaPlexMemory()
        await _personaplex_memory.initialize()
    return _personaplex_memory
