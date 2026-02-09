"""
Search Memory System - February 5, 2026

Provides specialized memory management for search sessions:
- Search session tracking with queries, results, and interactions
- Widget focus and topic exploration tracking
- AI conversation context within search
- MINDEX integration for user interest enrichment
- Memory consolidation to appropriate layers
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

logger = logging.getLogger("SearchMemory")


class SearchTopic(str, Enum):
    """Topics that can be explored during search."""
    SPECIES = "species"
    CHEMISTRY = "chemistry"
    GENETICS = "genetics"
    RESEARCH = "research"
    TAXONOMY = "taxonomy"
    GALLERY = "gallery"
    AI_CHAT = "ai_chat"


@dataclass
class SearchQuery:
    """A single search query within a session."""
    id: UUID
    query: str
    timestamp: datetime
    result_count: int
    result_types: Dict[str, int]
    clicked_results: List[str]
    duration_ms: Optional[int] = None
    source: str = "text"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "query": self.query,
            "timestamp": self.timestamp.isoformat(),
            "result_count": self.result_count,
            "result_types": self.result_types,
            "clicked_results": self.clicked_results,
            "duration_ms": self.duration_ms,
            "source": self.source
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SearchQuery":
        return cls(
            id=UUID(data["id"]),
            query=data["query"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            result_count=data.get("result_count", 0),
            result_types=data.get("result_types", {}),
            clicked_results=data.get("clicked_results", []),
            duration_ms=data.get("duration_ms"),
            source=data.get("source", "text")
        )


@dataclass
class WidgetInteraction:
    """Tracks user interaction with a search widget."""
    widget: SearchTopic
    species_id: Optional[str]
    started_at: datetime
    ended_at: Optional[datetime] = None
    interactions: int = 0
    
    @property
    def duration_seconds(self) -> float:
        end = self.ended_at or datetime.now(timezone.utc)
        return (end - self.started_at).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "widget": self.widget.value,
            "species_id": self.species_id,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "interactions": self.interactions,
            "duration_seconds": self.duration_seconds
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WidgetInteraction":
        return cls(
            widget=SearchTopic(data["widget"]),
            species_id=data.get("species_id"),
            started_at=datetime.fromisoformat(data["started_at"]),
            ended_at=datetime.fromisoformat(data["ended_at"]) if data.get("ended_at") else None,
            interactions=data.get("interactions", 0)
        )


@dataclass
class AIMessage:
    """A message in the AI conversation within search."""
    id: UUID
    role: str
    content: str
    timestamp: datetime
    context_species: Optional[str] = None
    context_topic: Optional[SearchTopic] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "context_species": self.context_species,
            "context_topic": self.context_topic.value if self.context_topic else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AIMessage":
        return cls(
            id=UUID(data["id"]),
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            context_species=data.get("context_species"),
            context_topic=SearchTopic(data["context_topic"]) if data.get("context_topic") else None
        )


@dataclass
class SearchSession:
    """A complete search session with all context."""
    id: UUID
    user_id: str
    queries: List[SearchQuery] = field(default_factory=list)
    focused_species: List[str] = field(default_factory=list)
    explored_topics: List[SearchTopic] = field(default_factory=list)
    ai_conversation: List[AIMessage] = field(default_factory=list)
    widget_interactions: List[WidgetInteraction] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: Optional[datetime] = None
    voice_session_id: Optional[UUID] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> timedelta:
        end = self.ended_at or datetime.now(timezone.utc)
        return end - self.started_at
    
    @property
    def query_count(self) -> int:
        return len(self.queries)
    
    @property
    def current_species(self) -> Optional[str]:
        return self.focused_species[-1] if self.focused_species else None
    
    @property
    def current_topic(self) -> Optional[SearchTopic]:
        return self.explored_topics[-1] if self.explored_topics else None
    
    def add_query(self, query: str, result_count: int = 0, result_types: Optional[Dict[str, int]] = None, source: str = "text") -> SearchQuery:
        sq = SearchQuery(id=uuid4(), query=query, timestamp=datetime.now(timezone.utc), result_count=result_count, result_types=result_types or {}, clicked_results=[], source=source)
        self.queries.append(sq)
        self.last_activity = datetime.now(timezone.utc)
        return sq
    
    def record_click(self, result_id: str) -> None:
        if self.queries:
            self.queries[-1].clicked_results.append(result_id)
            self.last_activity = datetime.now(timezone.utc)
    
    def focus_species(self, species_id: str) -> None:
        if species_id not in self.focused_species:
            self.focused_species.append(species_id)
        self.last_activity = datetime.now(timezone.utc)
    
    def explore_topic(self, topic: SearchTopic, species_id: Optional[str] = None) -> WidgetInteraction:
        for interaction in self.widget_interactions:
            if interaction.widget == topic and interaction.ended_at is None:
                interaction.ended_at = datetime.now(timezone.utc)
        interaction = WidgetInteraction(widget=topic, species_id=species_id or self.current_species, started_at=datetime.now(timezone.utc))
        self.widget_interactions.append(interaction)
        if topic not in self.explored_topics:
            self.explored_topics.append(topic)
        self.last_activity = datetime.now(timezone.utc)
        return interaction
    
    def add_ai_message(self, role: str, content: str, context_topic: Optional[SearchTopic] = None) -> AIMessage:
        msg = AIMessage(id=uuid4(), role=role, content=content, timestamp=datetime.now(timezone.utc), context_species=self.current_species, context_topic=context_topic or self.current_topic)
        self.ai_conversation.append(msg)
        self.last_activity = datetime.now(timezone.utc)
        return msg
    
    def get_focus_duration(self, species_id: str) -> float:
        total = 0.0
        for interaction in self.widget_interactions:
            if interaction.species_id == species_id:
                total += interaction.duration_seconds
        return total
    
    def has_ai_breakthrough(self) -> bool:
        return len(self.ai_conversation) >= 4 and any(len(m.content) > 200 for m in self.ai_conversation if m.role == "assistant")
    
    def get_ai_summary(self) -> Dict[str, Any]:
        return {
            "message_count": len(self.ai_conversation),
            "topics_discussed": list(set(m.context_topic.value for m in self.ai_conversation if m.context_topic)),
            "species_discussed": list(set(m.context_species for m in self.ai_conversation if m.context_species)),
            "last_exchange": {
                "user": next((m.content for m in reversed(self.ai_conversation) if m.role == "user"), None),
                "assistant": next((m.content for m in reversed(self.ai_conversation) if m.role == "assistant"), None)
            }
        }
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "queries": [q.to_dict() for q in self.queries],
            "focused_species": self.focused_species,
            "explored_topics": [t.value for t in self.explored_topics],
            "ai_conversation": [m.to_dict() for m in self.ai_conversation],
            "widget_interactions": [w.to_dict() for w in self.widget_interactions],
            "started_at": self.started_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "voice_session_id": str(self.voice_session_id) if self.voice_session_id else None,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SearchSession":
        return cls(
            id=UUID(data["id"]),
            user_id=data["user_id"],
            queries=[SearchQuery.from_dict(q) for q in data.get("queries", [])],
            focused_species=data.get("focused_species", []),
            explored_topics=[SearchTopic(t) for t in data.get("explored_topics", [])],
            ai_conversation=[AIMessage.from_dict(m) for m in data.get("ai_conversation", [])],
            widget_interactions=[WidgetInteraction.from_dict(w) for w in data.get("widget_interactions", [])],
            started_at=datetime.fromisoformat(data["started_at"]),
            last_activity=datetime.fromisoformat(data["last_activity"]),
            ended_at=datetime.fromisoformat(data["ended_at"]) if data.get("ended_at") else None,
            voice_session_id=UUID(data["voice_session_id"]) if data.get("voice_session_id") else None,
            metadata=data.get("metadata", {})
        )


@dataclass
class SearchSessionSummary:
    """Summary of a completed search session."""
    session_id: UUID
    user_id: str
    duration_seconds: float
    query_count: int
    unique_species_explored: int
    topics_explored: List[str]
    ai_message_count: int
    top_interests: List[Tuple[str, float]]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": str(self.session_id),
            "user_id": self.user_id,
            "duration_seconds": self.duration_seconds,
            "query_count": self.query_count,
            "unique_species_explored": self.unique_species_explored,
            "topics_explored": self.topics_explored,
            "ai_message_count": self.ai_message_count,
            "top_interests": [{"species_id": s, "score": score} for s, score in self.top_interests]
        }


class SearchMemoryManager:
    """Manages search memory with MINDEX integration."""
    
    SESSION_TIMEOUT = timedelta(minutes=30)
    
    def __init__(self, database_url: Optional[str] = None):
        self._database_url = database_url or os.getenv("MINDEX_DATABASE_URL", "postgresql://mycosoft:Mushroom1!Mushroom1!@192.168.0.189:5432/mindex")
        self._pool = None
        self._active_sessions: Dict[UUID, SearchSession] = {}
        self._user_sessions: Dict[str, UUID] = {}
        self._initialized = False
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> None:
        if self._initialized:
            return
        try:
            import asyncpg
            self._pool = await asyncpg.create_pool(self._database_url, min_size=1, max_size=5)
            logger.info("Search memory connected to database")
        except Exception as e:
            logger.warning(f"Database connection failed: {e}")
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._initialized = True
        logger.info("Search memory manager initialized")
    
    async def start_session(self, user_id: str, voice_session_id: Optional[UUID] = None, metadata: Optional[Dict[str, Any]] = None) -> SearchSession:
        if user_id in self._user_sessions:
            existing_id = self._user_sessions[user_id]
            if existing_id in self._active_sessions:
                existing = self._active_sessions[existing_id]
                if datetime.now(timezone.utc) - existing.last_activity < self.SESSION_TIMEOUT:
                    return existing
                await self.end_session(existing_id)
        session = SearchSession(id=uuid4(), user_id=user_id, voice_session_id=voice_session_id, metadata=metadata or {})
        history = await self.get_user_search_history(user_id, limit=3)
        if history:
            session.metadata["previous_searches"] = [{"query": h.queries[0].query if h.queries else "", "species": h.focused_species[:3]} for h in history]
        self._active_sessions[session.id] = session
        self._user_sessions[user_id] = session.id
        logger.info(f"Started search session {session.id} for user {user_id}")
        return session
    
    async def add_query(self, session_id: UUID, query: str, result_count: int = 0, result_types: Optional[Dict[str, int]] = None, source: str = "text") -> Optional[SearchQuery]:
        session = self._active_sessions.get(session_id)
        if not session:
            return None
        sq = session.add_query(query, result_count, result_types, source)
        await self._record_search_analytics(session, sq)
        return sq
    
    async def record_focus(self, session_id: UUID, species_id: str, topic: Optional[str] = None) -> bool:
        session = self._active_sessions.get(session_id)
        if not session:
            return False
        session.focus_species(species_id)
        if topic:
            try:
                session.explore_topic(SearchTopic(topic), species_id)
            except ValueError:
                pass
        await self._record_user_interest(session.user_id, species_id, "focus", {"topic": topic, "session_id": str(session_id)})
        return True
    
    async def add_ai_turn(self, session_id: UUID, role: str, content: str, topic: Optional[str] = None) -> Optional[AIMessage]:
        session = self._active_sessions.get(session_id)
        if not session:
            return None
        search_topic = SearchTopic(topic) if topic else None
        msg = session.add_ai_message(role, content, search_topic)
        if session.current_species:
            await self._record_user_interest(session.user_id, session.current_species, "ai_question", {"question": content[:200] if role == "user" else None})
        return msg
    
    async def get_session_context(self, session_id: UUID) -> Dict[str, Any]:
        session = self._active_sessions.get(session_id) or await self._load_session(session_id)
        if not session:
            return {"error": "Session not found"}
        return {
            "session_id": str(session.id),
            "user_id": session.user_id,
            "duration_seconds": session.duration.total_seconds(),
            "queries": [q.query for q in session.queries[-5:]],
            "current_species": session.current_species,
            "focused_species": session.focused_species,
            "explored_topics": [t.value for t in session.explored_topics],
            "ai_message_count": len(session.ai_conversation),
            "recent_ai": [{"role": m.role, "content": m.content[:100]} for m in session.ai_conversation[-4:]],
            "voice_linked": session.voice_session_id is not None
        }
    
    async def end_session(self, session_id: UUID) -> Optional[SearchSessionSummary]:
        session = self._active_sessions.pop(session_id, None)
        if not session:
            return None
        if session.user_id in self._user_sessions and self._user_sessions[session.user_id] == session_id:
            del self._user_sessions[session.user_id]
        for interaction in session.widget_interactions:
            if interaction.ended_at is None:
                interaction.ended_at = datetime.now(timezone.utc)
        session.ended_at = datetime.now(timezone.utc)
        interests = self._calculate_interests(session)
        summary = SearchSessionSummary(session_id=session.id, user_id=session.user_id, duration_seconds=session.duration.total_seconds(), query_count=session.query_count, unique_species_explored=len(session.focused_species), topics_explored=[t.value for t in session.explored_topics], ai_message_count=len(session.ai_conversation), top_interests=interests[:5])
        await self._persist_session(session)
        await self._consolidate_session(session)
        logger.info(f"Ended search session {session_id}")
        return summary
    
    async def enrich_to_mindex(self, query: str, user_id: str, taxon_ids: Optional[List[int]] = None) -> bool:
        if not self._pool or not taxon_ids:
            return False
        try:
            async with self._pool.acquire() as conn:
                for taxon_id in taxon_ids:
                    await conn.execute("""
                        INSERT INTO mindex.user_interests (user_id, taxon_id, interest_type, metadata)
                        VALUES ($1, $2, 'search', $3::jsonb)
                        ON CONFLICT (user_id, taxon_id, interest_type) DO UPDATE SET
                            interaction_count = mindex.user_interests.interaction_count + 1,
                            last_seen_at = NOW()
                    """, user_id, taxon_id, json.dumps({"query": query}))
            return True
        except Exception as e:
            logger.error(f"Failed to enrich MINDEX: {e}")
            return False
    
    async def get_user_search_history(self, user_id: str, limit: int = 10) -> List[SearchSession]:
        if not self._pool:
            return []
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM mindex.search_sessions WHERE user_id = $1 ORDER BY started_at DESC LIMIT $2", user_id, limit)
                sessions = []
                for row in rows:
                    data = json.loads(row["session_data"]) if row["session_data"] else {}
                    data["id"] = row["id"]
                    data["user_id"] = row["user_id"]
                    data["started_at"] = row["started_at"].isoformat()
                    data["ended_at"] = row["ended_at"].isoformat() if row["ended_at"] else None
                    data["last_activity"] = row["started_at"].isoformat()
                    sessions.append(SearchSession.from_dict(data))
                return sessions
        except Exception as e:
            logger.error(f"Failed to get search history: {e}")
            return []
    
    async def get_stats(self) -> Dict[str, Any]:
        return {"active_sessions": len(self._active_sessions), "active_users": len(self._user_sessions), "database_connected": self._pool is not None, "initialized": self._initialized}
    
    def _calculate_interests(self, session: SearchSession) -> List[Tuple[str, float]]:
        interests: Dict[str, float] = {}
        for species_id in session.focused_species:
            score = 0.5 + min(0.3, session.get_focus_duration(species_id) / 300)
            score += min(0.2, sum(1 for i in session.widget_interactions if i.species_id == species_id) * 0.05)
            score += min(0.2, sum(1 for m in session.ai_conversation if m.context_species == species_id) * 0.1)
            interests[species_id] = min(1.0, score)
        return sorted(interests.items(), key=lambda x: x[1], reverse=True)
    
    async def _record_user_interest(self, user_id: str, species_id: str, interest_type: str, metadata: Dict[str, Any]) -> None:
        if not self._pool or not species_id.isdigit():
            return
        try:
            async with self._pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO mindex.user_interests (user_id, taxon_id, interest_type, metadata)
                    VALUES ($1, $2, $3, $4::jsonb)
                    ON CONFLICT (user_id, taxon_id, interest_type) DO UPDATE SET
                        interaction_count = mindex.user_interests.interaction_count + 1,
                        last_seen_at = NOW(),
                        interest_score = LEAST(1.0, mindex.user_interests.interest_score + 0.1)
                """, user_id, int(species_id), interest_type, json.dumps(metadata))
        except Exception as e:
            logger.debug(f"Failed to record interest: {e}")
    
    async def _record_search_analytics(self, session: SearchSession, query: SearchQuery) -> None:
        if not self._pool:
            return
        try:
            async with self._pool.acquire() as conn:
                await conn.execute("INSERT INTO mindex.search_analytics (query, user_id, session_id, result_count, clicked_results) VALUES ($1, $2, $3, $4, $5::jsonb)", query.query, session.user_id, str(session.id), query.result_count, json.dumps(query.clicked_results))
        except Exception as e:
            logger.debug(f"Failed to record analytics: {e}")
    
    async def _persist_session(self, session: SearchSession) -> bool:
        if not self._pool:
            return False
        try:
            async with self._pool.acquire() as conn:
                await conn.execute("INSERT INTO mindex.search_sessions (id, user_id, started_at, ended_at, session_data) VALUES ($1, $2, $3, $4, $5::jsonb) ON CONFLICT (id) DO UPDATE SET ended_at = EXCLUDED.ended_at, session_data = EXCLUDED.session_data", str(session.id), session.user_id, session.started_at, session.ended_at, json.dumps(session.to_dict()))
            return True
        except Exception as e:
            logger.error(f"Failed to persist session: {e}")
            return False
    
    async def _load_session(self, session_id: UUID) -> Optional[SearchSession]:
        if not self._pool:
            return None
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM mindex.search_sessions WHERE id = $1", str(session_id))
                if row and row["session_data"]:
                    return SearchSession.from_dict(json.loads(row["session_data"]))
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
        return None
    
    async def _consolidate_session(self, session: SearchSession) -> None:
        try:
            from mycosoft_mas.memory.myca_memory import get_myca_memory, MemoryLayer
            myca_memory = await get_myca_memory()
            for species_id, score in self._calculate_interests(session):
                if score >= 0.7:
                    await myca_memory.remember(content={"type": "user_search_interest", "user_id": session.user_id, "species_id": species_id, "interest_score": score}, layer=MemoryLayer.SEMANTIC, importance=score, tags=["search", "user_interest", session.user_id])
            if session.has_ai_breakthrough():
                await myca_memory.remember(content={"type": "search_ai_discovery", "user_id": session.user_id, "session_id": str(session.id), "summary": session.get_ai_summary()}, layer=MemoryLayer.EPISODIC, importance=0.8, tags=["search", "ai_discovery", session.user_id])
        except Exception as e:
            logger.error(f"Failed to consolidate session: {e}")
    
    async def _cleanup_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(300)
                now = datetime.now(timezone.utc)
                expired = [sid for sid, s in self._active_sessions.items() if now - s.last_activity > self.SESSION_TIMEOUT]
                for sid in expired:
                    await self.end_session(sid)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    async def shutdown(self) -> None:
        if self._cleanup_task:
            self._cleanup_task.cancel()
        for session_id in list(self._active_sessions.keys()):
            await self.end_session(session_id)
        if self._pool:
            await self._pool.close()
        logger.info("Search memory manager shutdown")


_search_memory: Optional[SearchMemoryManager] = None

async def get_search_memory() -> SearchMemoryManager:
    global _search_memory
    if _search_memory is None:
        _search_memory = SearchMemoryManager()
        await _search_memory.initialize()
    return _search_memory