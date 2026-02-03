"""
Unified Memory Service - February 3, 2026

Central coordinator for all memory operations across the Mycosoft MAS.
Integrates Redis (short-term), PostgreSQL (long-term), Qdrant (vector),
and graph memory with automatic scope routing and lifecycle management.
"""

import asyncio
import hashlib
import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger("UnifiedMemoryService")


class MemoryScope(str, Enum):
    """Memory scope determines storage backend and TTL."""
    CONVERSATION = "conversation"
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"
    EPHEMERAL = "ephemeral"
    DEVICE = "device"
    EXPERIMENT = "experiment"
    WORKFLOW = "workflow"


class MemorySource(str, Enum):
    """Source system that created the memory."""
    PERSONAPLEX = "personaplex"
    NATUREOS = "natureos"
    ORCHESTRATOR = "orchestrator"
    AGENT = "agent"
    N8N = "n8n"
    MINDEX = "mindex"
    DEVICE = "device"
    DASHBOARD = "dashboard"
    SYSTEM = "system"


class MemoryEntry(BaseModel):
    """Universal memory entry structure."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    scope: MemoryScope
    namespace: str
    key: str
    value: Any
    source: MemorySource = MemorySource.SYSTEM
    embedding: Optional[List[float]] = None
    confidence: float = 1.0
    access_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed_at: Optional[datetime] = None


class MemoryRelationship(BaseModel):
    """Relationship between memory entries."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    from_entry_id: str
    to_entry_id: str
    relationship_type: str
    weight: float = 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserProfile(BaseModel):
    """User profile for long-term personalization."""
    user_id: str
    preferences: Dict[str, Any] = Field(default_factory=dict)
    expertise_domains: List[str] = Field(default_factory=list)
    personality_traits: Dict[str, Any] = Field(default_factory=dict)
    interaction_history: Dict[str, Any] = Field(default_factory=dict)
    memory_consent: bool = True
    last_active_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MemoryBackend(ABC):
    """Abstract base class for memory storage backends."""
    
    @abstractmethod
    async def connect(self) -> bool:
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        pass
    
    @abstractmethod
    async def write(self, entry: MemoryEntry) -> bool:
        pass
    
    @abstractmethod
    async def read(self, scope: MemoryScope, namespace: str, key: Optional[str] = None) -> List[MemoryEntry]:
        pass
    
    @abstractmethod
    async def delete(self, scope: MemoryScope, namespace: str, key: str) -> bool:
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        pass


class RedisBackend(MemoryBackend):
    """Redis backend for short-term memory."""
    
    def __init__(self):
        self._client = None
        self._url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    
    async def connect(self) -> bool:
        try:
            import redis.asyncio as redis
            self._client = redis.from_url(self._url, decode_responses=True)
            await self._client.ping()
            logger.info("Redis backend connected")
            return True
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            return False
    
    async def disconnect(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None
    
    def _build_key(self, scope: MemoryScope, namespace: str, key: str) -> str:
        safe_namespace = namespace.replace(":", "_").replace("/", "_")
        safe_key = key.replace(":", "_").replace("/", "_")
        return f"mas:memory:{scope.value}:{safe_namespace}:{safe_key}"
    
    async def write(self, entry: MemoryEntry) -> bool:
        if not self._client:
            await self.connect()
        try:
            full_key = self._build_key(entry.scope, entry.namespace, entry.key)
            data = entry.model_dump(mode="json")
            ttl_map = {
                MemoryScope.CONVERSATION: 3600,
                MemoryScope.AGENT: 86400,
                MemoryScope.EPHEMERAL: 60,
                MemoryScope.WORKFLOW: 604800,
            }
            ttl = ttl_map.get(entry.scope)
            if entry.expires_at:
                delta = entry.expires_at - datetime.now(timezone.utc)
                ttl = max(int(delta.total_seconds()), 1)
            if ttl:
                await self._client.set(full_key, json.dumps(data), ex=ttl)
            else:
                await self._client.set(full_key, json.dumps(data))
            return True
        except Exception as e:
            logger.error(f"Redis write failed: {e}")
            return False
    
    async def read(self, scope: MemoryScope, namespace: str, key: Optional[str] = None) -> List[MemoryEntry]:
        if not self._client:
            await self.connect()
        try:
            entries = []
            if key:
                full_key = self._build_key(scope, namespace, key)
                data = await self._client.get(full_key)
                if data:
                    entries.append(MemoryEntry(**json.loads(data)))
            else:
                pattern = self._build_key(scope, namespace, "*")
                keys = await self._client.keys(pattern)
                for k in keys:
                    data = await self._client.get(k)
                    if data:
                        entries.append(MemoryEntry(**json.loads(data)))
            return entries
        except Exception as e:
            logger.error(f"Redis read failed: {e}")
            return []
    
    async def delete(self, scope: MemoryScope, namespace: str, key: str) -> bool:
        if not self._client:
            await self.connect()
        try:
            full_key = self._build_key(scope, namespace, key)
            result = await self._client.delete(full_key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis delete failed: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        try:
            if not self._client:
                await self.connect()
            await self._client.ping()
            info = await self._client.info("memory")
            return {"status": "healthy", "backend": "redis", "memory_used": info.get("used_memory_human", "unknown")}
        except Exception as e:
            return {"status": "unhealthy", "backend": "redis", "error": str(e)}


class PostgresBackend(MemoryBackend):
    """PostgreSQL backend for long-term memory."""
    
    def __init__(self):
        self._pool = None
        self._url = os.getenv("DATABASE_URL", os.getenv("MINDEX_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/mycosoft"))
    
    async def connect(self) -> bool:
        try:
            import asyncpg
            self._pool = await asyncpg.create_pool(self._url, min_size=2, max_size=10)
            logger.info("PostgreSQL backend connected")
            return True
        except Exception as e:
            logger.error(f"PostgreSQL connection failed: {e}")
            return False
    
    async def disconnect(self) -> None:
        if self._pool:
            await self._pool.close()
            self._pool = None
    
    async def _ensure_schema(self) -> None:
        if not self._pool:
            return
        async with self._pool.acquire() as conn:
            await conn.execute('''
                CREATE SCHEMA IF NOT EXISTS memory;
                CREATE TABLE IF NOT EXISTS memory.entries (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    scope VARCHAR(20) NOT NULL,
                    namespace VARCHAR(255) NOT NULL,
                    key VARCHAR(255) NOT NULL,
                    value JSONB NOT NULL,
                    source VARCHAR(50),
                    confidence FLOAT DEFAULT 1.0,
                    access_count INTEGER DEFAULT 0,
                    metadata JSONB DEFAULT '{}',
                    expires_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    last_accessed_at TIMESTAMPTZ,
                    UNIQUE(scope, namespace, key)
                );
                CREATE INDEX IF NOT EXISTS idx_memory_scope_namespace ON memory.entries(scope, namespace);
                CREATE INDEX IF NOT EXISTS idx_memory_expires ON memory.entries(expires_at) WHERE expires_at IS NOT NULL;
            ''')
    
    async def write(self, entry: MemoryEntry) -> bool:
        if not self._pool:
            await self.connect()
            await self._ensure_schema()
        try:
            async with self._pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO memory.entries (id, scope, namespace, key, value, source, confidence, access_count, metadata, expires_at, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    ON CONFLICT (scope, namespace, key) DO UPDATE SET value = EXCLUDED.value, source = EXCLUDED.source, confidence = EXCLUDED.confidence, metadata = EXCLUDED.metadata, expires_at = EXCLUDED.expires_at, updated_at = NOW()
                ''', entry.id, entry.scope.value, entry.namespace, entry.key, json.dumps(entry.value), entry.source.value, entry.confidence, entry.access_count, json.dumps(entry.metadata), entry.expires_at, entry.created_at, entry.updated_at)
            return True
        except Exception as e:
            logger.error(f"PostgreSQL write failed: {e}")
            return False
    
    async def read(self, scope: MemoryScope, namespace: str, key: Optional[str] = None) -> List[MemoryEntry]:
        if not self._pool:
            await self.connect()
            await self._ensure_schema()
        try:
            async with self._pool.acquire() as conn:
                if key:
                    rows = await conn.fetch('SELECT * FROM memory.entries WHERE scope = $1 AND namespace = $2 AND key = $3 AND (expires_at IS NULL OR expires_at > NOW())', scope.value, namespace, key)
                else:
                    rows = await conn.fetch('SELECT * FROM memory.entries WHERE scope = $1 AND namespace = $2 AND (expires_at IS NULL OR expires_at > NOW())', scope.value, namespace)
                if rows:
                    ids = [str(row["id"]) for row in rows]
                    await conn.execute('UPDATE memory.entries SET access_count = access_count + 1, last_accessed_at = NOW() WHERE id = ANY($1::uuid[])', ids)
                entries = []
                for row in rows:
                    entries.append(MemoryEntry(id=str(row["id"]), scope=MemoryScope(row["scope"]), namespace=row["namespace"], key=row["key"], value=json.loads(row["value"]) if isinstance(row["value"], str) else row["value"], source=MemorySource(row["source"]) if row["source"] else MemorySource.SYSTEM, confidence=row["confidence"], access_count=row["access_count"], metadata=json.loads(row["metadata"]) if isinstance(row["metadata"], str) else row["metadata"] or {}, expires_at=row["expires_at"], created_at=row["created_at"], updated_at=row["updated_at"], last_accessed_at=row["last_accessed_at"]))
                return entries
        except Exception as e:
            logger.error(f"PostgreSQL read failed: {e}")
            return []
    
    async def delete(self, scope: MemoryScope, namespace: str, key: str) -> bool:
        if not self._pool:
            await self.connect()
        try:
            async with self._pool.acquire() as conn:
                result = await conn.execute('DELETE FROM memory.entries WHERE scope = $1 AND namespace = $2 AND key = $3', scope.value, namespace, key)
            return "DELETE" in result
        except Exception as e:
            logger.error(f"PostgreSQL delete failed: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        try:
            if not self._pool:
                await self.connect()
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow("SELECT COUNT(*) as count FROM memory.entries")
                return {"status": "healthy", "backend": "postgresql", "entry_count": row["count"] if row else 0}
        except Exception as e:
            return {"status": "unhealthy", "backend": "postgresql", "error": str(e)}


class QdrantBackend(MemoryBackend):
    """Qdrant backend for vector memory."""
    
    def __init__(self):
        self._client = None
        self._url = os.getenv("QDRANT_URL", "http://qdrant:6333")
        self._collection_name = "mycosoft_memory"
        self._dimension = 1536
    
    async def connect(self) -> bool:
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams
            self._client = QdrantClient(url=self._url)
            collections = self._client.get_collections().collections
            if not any(c.name == self._collection_name for c in collections):
                self._client.create_collection(collection_name=self._collection_name, vectors_config=VectorParams(size=self._dimension, distance=Distance.COSINE))
            logger.info("Qdrant backend connected")
            return True
        except Exception as e:
            logger.error(f"Qdrant connection failed: {e}")
            return False
    
    async def disconnect(self) -> None:
        self._client = None
    
    async def write(self, entry: MemoryEntry) -> bool:
        if not self._client:
            await self.connect()
        if not entry.embedding:
            return False
        try:
            from qdrant_client.models import PointStruct
            point_id = hashlib.md5(f"{entry.scope}:{entry.namespace}:{entry.key}".encode()).hexdigest()
            self._client.upsert(collection_name=self._collection_name, points=[PointStruct(id=point_id, vector=entry.embedding, payload={"scope": entry.scope.value, "namespace": entry.namespace, "key": entry.key, "value": entry.value if isinstance(entry.value, str) else json.dumps(entry.value), "source": entry.source.value, "created_at": entry.created_at.isoformat()})])
            return True
        except Exception as e:
            logger.error(f"Qdrant write failed: {e}")
            return False
    
    async def read(self, scope: MemoryScope, namespace: str, key: Optional[str] = None) -> List[MemoryEntry]:
        return []
    
    async def search_similar(self, query_embedding: List[float], scope: Optional[MemoryScope] = None, namespace: Optional[str] = None, top_k: int = 10) -> List[Tuple[MemoryEntry, float]]:
        if not self._client:
            await self.connect()
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            filter_conditions = []
            if scope:
                filter_conditions.append(FieldCondition(key="scope", match=MatchValue(value=scope.value)))
            if namespace:
                filter_conditions.append(FieldCondition(key="namespace", match=MatchValue(value=namespace)))
            query_filter = Filter(must=filter_conditions) if filter_conditions else None
            results = self._client.search(collection_name=self._collection_name, query_vector=query_embedding, query_filter=query_filter, limit=top_k)
            entries = []
            for result in results:
                payload = result.payload
                entry = MemoryEntry(id=str(result.id), scope=MemoryScope(payload["scope"]), namespace=payload["namespace"], key=payload["key"], value=payload["value"], source=MemorySource(payload["source"]), embedding=result.vector, created_at=datetime.fromisoformat(payload["created_at"]))
                entries.append((entry, result.score))
            return entries
        except Exception as e:
            logger.error(f"Qdrant search failed: {e}")
            return []
    
    async def delete(self, scope: MemoryScope, namespace: str, key: str) -> bool:
        if not self._client:
            await self.connect()
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            self._client.delete(collection_name=self._collection_name, points_selector=Filter(must=[FieldCondition(key="scope", match=MatchValue(value=scope.value)), FieldCondition(key="namespace", match=MatchValue(value=namespace)), FieldCondition(key="key", match=MatchValue(value=key))]))
            return True
        except Exception as e:
            logger.error(f"Qdrant delete failed: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        try:
            if not self._client:
                await self.connect()
            info = self._client.get_collection(self._collection_name)
            return {"status": "healthy", "backend": "qdrant", "points_count": info.points_count, "vectors_count": info.vectors_count}
        except Exception as e:
            return {"status": "unhealthy", "backend": "qdrant", "error": str(e)}


class UnifiedMemoryService:
    """Central memory coordinator for all MAS components."""
    
    def __init__(self):
        self._redis = RedisBackend()
        self._postgres = PostgresBackend()
        self._qdrant = QdrantBackend()
        self._initialized = False
        self._audit_log: List[Dict[str, Any]] = []
        self._scope_backends = {
            MemoryScope.CONVERSATION: [self._redis],
            MemoryScope.USER: [self._postgres, self._qdrant],
            MemoryScope.AGENT: [self._redis],
            MemoryScope.SYSTEM: [self._postgres],
            MemoryScope.EPHEMERAL: [self._redis],
            MemoryScope.DEVICE: [self._postgres],
            MemoryScope.EXPERIMENT: [self._postgres, self._qdrant],
            MemoryScope.WORKFLOW: [self._redis, self._postgres],
        }
    
    async def initialize(self) -> bool:
        if self._initialized:
            return True
        try:
            await self._redis.connect()
            await self._postgres.connect()
            await self._qdrant.connect()
            self._initialized = True
            logger.info("Unified Memory Service initialized")
            return True
        except Exception as e:
            logger.error(f"Memory service initialization failed: {e}")
            return False
    
    async def shutdown(self) -> None:
        await self._redis.disconnect()
        await self._postgres.disconnect()
        await self._qdrant.disconnect()
        self._initialized = False
    
    def _log_operation(self, operation: str, scope: MemoryScope, namespace: str, key: Optional[str], success: bool, backends: List[str]):
        entry = {"timestamp": datetime.now(timezone.utc).isoformat(), "operation": operation, "scope": scope.value, "namespace": namespace, "key": key, "success": success, "backends": backends}
        self._audit_log.append(entry)
        if len(self._audit_log) > 10000:
            self._audit_log = self._audit_log[-10000:]
        level = logging.INFO if success else logging.WARNING
        logger.log(level, f"Memory {operation}: {scope.value}/{namespace}/{key or '*'} -> {backends}")
    
    async def write(self, entry: MemoryEntry) -> bool:
        if not self._initialized:
            await self.initialize()
        backends = self._scope_backends.get(entry.scope, [self._postgres])
        backend_names = []
        success = True
        for backend in backends:
            if isinstance(backend, QdrantBackend) and not entry.embedding:
                continue
            result = await backend.write(entry)
            if result:
                backend_names.append(type(backend).__name__)
            else:
                success = False
        self._log_operation("write", entry.scope, entry.namespace, entry.key, success, backend_names)
        return success
    
    async def read(self, scope: MemoryScope, namespace: str, key: Optional[str] = None) -> List[MemoryEntry]:
        if not self._initialized:
            await self.initialize()
        backends = self._scope_backends.get(scope, [self._postgres])
        all_entries = []
        backend_names = []
        for backend in backends:
            if isinstance(backend, QdrantBackend):
                continue
            entries = await backend.read(scope, namespace, key)
            all_entries.extend(entries)
            if entries:
                backend_names.append(type(backend).__name__)
        seen = set()
        unique_entries = []
        for entry in all_entries:
            entry_key = (entry.scope, entry.namespace, entry.key)
            if entry_key not in seen:
                seen.add(entry_key)
                unique_entries.append(entry)
        self._log_operation("read", scope, namespace, key, len(unique_entries) > 0, backend_names)
        return unique_entries
    
    async def delete(self, scope: MemoryScope, namespace: str, key: str) -> bool:
        if not self._initialized:
            await self.initialize()
        backends = self._scope_backends.get(scope, [self._postgres])
        backend_names = []
        any_success = False
        for backend in backends:
            result = await backend.delete(scope, namespace, key)
            if result:
                any_success = True
                backend_names.append(type(backend).__name__)
        self._log_operation("delete", scope, namespace, key, any_success, backend_names)
        return any_success
    
    async def search_similar(self, query_embedding: List[float], scope: Optional[MemoryScope] = None, namespace: Optional[str] = None, top_k: int = 10) -> List[Tuple[MemoryEntry, float]]:
        if not self._initialized:
            await self.initialize()
        return await self._qdrant.search_similar(query_embedding, scope, namespace, top_k)
    
    async def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        entries = await self.read(MemoryScope.USER, f"profile:{user_id}", "profile")
        if entries:
            data = entries[0].value
            return UserProfile(user_id=user_id, preferences=data.get("preferences", {}), expertise_domains=data.get("expertise_domains", []), personality_traits=data.get("personality_traits", {}), interaction_history=data.get("interaction_history", {}), memory_consent=data.get("memory_consent", True))
        return None
    
    async def update_user_profile(self, profile: UserProfile) -> bool:
        entry = MemoryEntry(scope=MemoryScope.USER, namespace=f"profile:{profile.user_id}", key="profile", value=profile.model_dump(mode="json"), source=MemorySource.SYSTEM)
        return await self.write(entry)
    
    async def summarize_conversation(self, conversation_id: str, archive_to_user: Optional[str] = None) -> Optional[str]:
        entries = await self.read(MemoryScope.CONVERSATION, conversation_id)
        if not entries:
            return None
        messages = []
        for entry in entries:
            if isinstance(entry.value, dict) and "content" in entry.value:
                messages.append(entry.value)
        summary = f"Conversation {conversation_id} with {len(messages)} messages. "
        if messages:
            topics = set()
            for msg in messages:
                content = str(msg.get("content", "")).lower()
                if "device" in content or "sensor" in content:
                    topics.add("devices")
                if "agent" in content:
                    topics.add("agents")
                if "workflow" in content or "n8n" in content:
                    topics.add("workflows")
            if topics:
                summary += f"Topics discussed: {', '.join(topics)}."
        if archive_to_user:
            archive_entry = MemoryEntry(scope=MemoryScope.USER, namespace=f"conversations:{archive_to_user}", key=f"summary_{conversation_id}", value={"summary": summary, "message_count": len(messages), "conversation_id": conversation_id}, source=MemorySource.ORCHESTRATOR)
            await self.write(archive_entry)
        return summary
    
    async def health_check(self) -> Dict[str, Any]:
        results = {"redis": await self._redis.health_check(), "postgresql": await self._postgres.health_check(), "qdrant": await self._qdrant.health_check()}
        all_healthy = all(r.get("status") == "healthy" for r in results.values())
        return {"status": "healthy" if all_healthy else "degraded", "backends": results, "initialized": self._initialized, "audit_log_size": len(self._audit_log)}
    
    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self._audit_log[-limit:]
    
    async def cleanup_expired(self) -> int:
        if not self._initialized:
            await self.initialize()
        cleaned = 0
        try:
            async with self._postgres._pool.acquire() as conn:
                result = await conn.execute("DELETE FROM memory.entries WHERE expires_at IS NOT NULL AND expires_at < NOW()")
                cleaned = int(result.split()[-1]) if result else 0
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
        logger.info(f"Cleaned up {cleaned} expired memory entries")
        return cleaned


_memory_service: Optional[UnifiedMemoryService] = None


def get_memory_service() -> UnifiedMemoryService:
    global _memory_service
    if _memory_service is None:
        _memory_service = UnifiedMemoryService()
    return _memory_service


async def init_memory_service() -> UnifiedMemoryService:
    service = get_memory_service()
    await service.initialize()
    return service
