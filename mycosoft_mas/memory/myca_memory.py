"""
MYCA 6-Layer Memory Architecture.
Created: February 5, 2026
Updated: February 5, 2026 - MINDEX as sole storage backend

Implements a comprehensive memory system for MYCA with six distinct layers:
1. Ephemeral Memory - Transient working data (minutes)
2. Session Memory - Current conversation context (hours)
3. Working Memory - Active task state (hours-days)
4. Semantic Memory - Long-term knowledge facts (permanent)
5. Episodic Memory - Event-based memories (permanent)
6. System Memory - Configuration and learned behaviors (permanent)

Each layer has different retention policies, access patterns, and storage backends.
"""

import asyncio
import hashlib
import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, TypeVar, Generic
from uuid import UUID, uuid4

logger = logging.getLogger("MYCAMemory")


class MemoryLayer(str, Enum):
    """The six layers of MYCA memory."""
    EPHEMERAL = "ephemeral"    # Minutes - transient working data
    SESSION = "session"        # Hours - conversation context
    WORKING = "working"        # Hours-Days - active task state
    SEMANTIC = "semantic"      # Permanent - knowledge facts
    EPISODIC = "episodic"      # Permanent - event memories
    SYSTEM = "system"          # Permanent - config and behaviors


class MemoryStatus(str, Enum):
    """Status of a memory entry."""
    ACTIVE = "active"
    DECAYED = "decayed"
    ARCHIVED = "archived"
    DELETED = "deleted"


@dataclass
class MemoryEntry:
    """A single memory entry in the system."""
    id: UUID
    layer: MemoryLayer
    content: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    accessed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    access_count: int = 0
    importance: float = 0.5  # 0.0 to 1.0
    status: MemoryStatus = MemoryStatus.ACTIVE
    tags: List[str] = field(default_factory=list)
    embeddings: Optional[List[float]] = None
    hash: Optional[str] = None
    
    def __post_init__(self):
        """Compute hash of content for integrity."""
        if not self.hash:
            content_str = json.dumps(self.content, sort_keys=True)
            self.hash = hashlib.sha256(content_str.encode()).hexdigest()


@dataclass 
class MemoryQuery:
    """Query parameters for memory retrieval."""
    text: Optional[str] = None
    layer: Optional[MemoryLayer] = None
    tags: Optional[List[str]] = None
    min_importance: float = 0.0
    since: Optional[datetime] = None
    limit: int = 10
    include_archived: bool = False
    semantic_search: bool = False


class MemoryBackend(ABC):
    """Abstract backend for memory storage."""
    
    @abstractmethod
    async def store(self, entry: MemoryEntry) -> bool:
        """Store a memory entry."""
        pass
    
    @abstractmethod
    async def retrieve(self, entry_id: UUID) -> Optional[MemoryEntry]:
        """Retrieve a memory entry by ID."""
        pass
    
    @abstractmethod
    async def query(self, query: MemoryQuery) -> List[MemoryEntry]:
        """Query memory entries."""
        pass
    
    @abstractmethod
    async def update(self, entry_id: UUID, updates: Dict[str, Any]) -> bool:
        """Update a memory entry."""
        pass
    
    @abstractmethod
    async def delete(self, entry_id: UUID) -> bool:
        """Delete a memory entry."""
        pass


class InMemoryBackend(MemoryBackend):
    """In-memory storage backend for fast ephemeral/session memory."""
    
    def __init__(self, max_entries: int = 10000):
        self._storage: Dict[UUID, MemoryEntry] = {}
        self._max_entries = max_entries
    
    async def store(self, entry: MemoryEntry) -> bool:
        if len(self._storage) >= self._max_entries:
            # Evict oldest entries
            sorted_entries = sorted(self._storage.values(), key=lambda e: e.accessed_at)
            to_remove = len(self._storage) - self._max_entries + 100
            for e in sorted_entries[:to_remove]:
                del self._storage[e.id]
        
        self._storage[entry.id] = entry
        return True
    
    async def retrieve(self, entry_id: UUID) -> Optional[MemoryEntry]:
        entry = self._storage.get(entry_id)
        if entry:
            entry.accessed_at = datetime.now(timezone.utc)
            entry.access_count += 1
        return entry
    
    async def query(self, query: MemoryQuery) -> List[MemoryEntry]:
        results = []
        for entry in self._storage.values():
            if query.layer and entry.layer != query.layer:
                continue
            if entry.importance < query.min_importance:
                continue
            if query.since and entry.created_at < query.since:
                continue
            if not query.include_archived and entry.status == MemoryStatus.ARCHIVED:
                continue
            if query.tags and not any(t in entry.tags for t in query.tags):
                continue
            results.append(entry)
        
        # Sort by importance and recency
        results.sort(key=lambda e: (e.importance, e.accessed_at), reverse=True)
        return results[:query.limit]
    
    async def update(self, entry_id: UUID, updates: Dict[str, Any]) -> bool:
        if entry_id not in self._storage:
            return False
        
        entry = self._storage[entry_id]
        for key, value in updates.items():
            if hasattr(entry, key):
                setattr(entry, key, value)
        return True
    
    async def delete(self, entry_id: UUID) -> bool:
        if entry_id in self._storage:
            del self._storage[entry_id]
            return True
        return False


class PostgresBackend(MemoryBackend):
    """PostgreSQL storage backend for persistent memory layers."""
    
    def __init__(self, database_url: Optional[str] = None):
        self._database_url = database_url or os.getenv(
        if not self._database_url:
            raise ValueError(
                "MINDEX_DATABASE_URL environment variable is required. "
                "Please set it to your PostgreSQL connection string."
            )
            "MINDEX_DATABASE_URL",
            os.getenv("MINDEX_DATABASE_URL")
        )
        self._pool = None
    
    async def initialize(self) -> None:
        """Initialize the database connection pool."""
        try:
            import asyncpg
            self._pool = await asyncpg.create_pool(
                self._database_url,
                min_size=2,
                max_size=10
            )
            logger.info("PostgreSQL memory backend initialized")
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL backend: {e}")
    
    async def store(self, entry: MemoryEntry) -> bool:
        if not self._pool:
            await self.initialize()
        
        try:
            async with self._pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO mindex.memory_entries (id, layer, content, metadata, created_at, 
                        accessed_at, access_count, importance, status, tags, hash)
                    VALUES ($1, $2, $3::jsonb, $4::jsonb, $5, $6, $7, $8, $9, $10, $11)
                    ON CONFLICT (id) DO UPDATE SET
                        content = EXCLUDED.content,
                        metadata = EXCLUDED.metadata,
                        accessed_at = EXCLUDED.accessed_at,
                        access_count = EXCLUDED.access_count,
                        importance = EXCLUDED.importance,
                        status = EXCLUDED.status
                """, str(entry.id), entry.layer.value, json.dumps(entry.content),
                    json.dumps(entry.metadata), entry.created_at, entry.accessed_at,
                    entry.access_count, entry.importance, entry.status.value,
                    entry.tags, entry.hash)
            return True
        except Exception as e:
            logger.error(f"Failed to store memory: {e}")
            return False
    
    async def retrieve(self, entry_id: UUID) -> Optional[MemoryEntry]:
        if not self._pool:
            await self.initialize()
        
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow("""
                    UPDATE mindex.memory_entries SET accessed_at = NOW(), access_count = access_count + 1
                    WHERE id = $1 RETURNING *
                """, str(entry_id))
                
                if row:
                    return MemoryEntry(
                        id=UUID(row["id"]),
                        layer=MemoryLayer(row["layer"]),
                        content=json.loads(row["content"]) if isinstance(row["content"], str) else row["content"],
                        metadata=json.loads(row["metadata"]) if isinstance(row["metadata"], str) else row["metadata"],
                        created_at=row["created_at"],
                        accessed_at=row["accessed_at"],
                        access_count=row["access_count"],
                        importance=row["importance"],
                        status=MemoryStatus(row["status"]),
                        tags=row["tags"] or [],
                        hash=row["hash"]
                    )
        except Exception as e:
            logger.error(f"Failed to retrieve memory: {e}")
        return None
    
    async def query(self, query: MemoryQuery) -> List[MemoryEntry]:
        if not self._pool:
            await self.initialize()
        
        results = []
        try:
            async with self._pool.acquire() as conn:
                sql = "SELECT * FROM mindex.memory_entries WHERE importance >= $1"
                params = [query.min_importance]
                param_idx = 2
                
                if query.layer:
                    sql += f" AND layer = ${param_idx}"
                    params.append(query.layer.value)
                    param_idx += 1
                
                if not query.include_archived:
                    sql += f" AND status != ${param_idx}"
                    params.append(MemoryStatus.ARCHIVED.value)
                    param_idx += 1
                
                if query.since:
                    sql += f" AND created_at >= ${param_idx}"
                    params.append(query.since)
                    param_idx += 1
                
                sql += f" ORDER BY importance DESC, accessed_at DESC LIMIT ${param_idx}"
                params.append(query.limit)
                
                rows = await conn.fetch(sql, *params)
                for row in rows:
                    results.append(MemoryEntry(
                        id=UUID(row["id"]),
                        layer=MemoryLayer(row["layer"]),
                        content=json.loads(row["content"]) if isinstance(row["content"], str) else row["content"],
                        metadata=json.loads(row["metadata"]) if isinstance(row["metadata"], str) else row["metadata"],
                        created_at=row["created_at"],
                        accessed_at=row["accessed_at"],
                        access_count=row["access_count"],
                        importance=row["importance"],
                        status=MemoryStatus(row["status"]),
                        tags=row["tags"] or [],
                        hash=row["hash"]
                    ))
        except Exception as e:
            logger.error(f"Failed to query memory: {e}")
        return results
    
    async def update(self, entry_id: UUID, updates: Dict[str, Any]) -> bool:
        if not self._pool:
            await self.initialize()
        
        try:
            async with self._pool.acquire() as conn:
                set_clauses = []
                params = []
                for i, (key, value) in enumerate(updates.items(), 1):
                    set_clauses.append(f"{key} = ${i}")
                    if key in ("content", "metadata"):
                        params.append(json.dumps(value))
                    else:
                        params.append(value)
                
                params.append(str(entry_id))
                sql = f"UPDATE mindex.memory_entries SET {', '.join(set_clauses)} WHERE id = ${len(params)}"
                await conn.execute(sql, *params)
            return True
        except Exception as e:
            logger.error(f"Failed to update memory: {e}")
            return False
    
    async def delete(self, entry_id: UUID) -> bool:
        if not self._pool:
            await self.initialize()
        
        try:
            async with self._pool.acquire() as conn:
                await conn.execute("DELETE FROM mindex.memory_entries WHERE id = $1", str(entry_id))
            return True
        except Exception as e:
            logger.error(f"Failed to delete memory: {e}")
            return False


class MYCAMemory:
    """
    MYCA 6-Layer Memory System.
    
    Provides unified access to all memory layers with automatic
    routing, decay management, and cross-layer consolidation.
    """
    
    # Retention policies for each layer
    RETENTION = {
        MemoryLayer.EPHEMERAL: timedelta(minutes=30),
        MemoryLayer.SESSION: timedelta(hours=24),
        MemoryLayer.WORKING: timedelta(days=7),
        MemoryLayer.SEMANTIC: None,  # Permanent
        MemoryLayer.EPISODIC: None,  # Permanent
        MemoryLayer.SYSTEM: None,    # Permanent
    }
    
    def __init__(self):
        # Fast in-memory backends for ephemeral layers
        self._ephemeral = InMemoryBackend(max_entries=1000)
        self._session = InMemoryBackend(max_entries=5000)
        self._working = InMemoryBackend(max_entries=2000)
        
        # Persistent backends for long-term memory
        self._persistent = PostgresBackend()
        
        self._initialized = False
        self._decay_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> None:
        """Initialize all memory backends."""
        if self._initialized:
            return
        
        await self._persistent.initialize()
        
        # Start decay background task
        self._decay_task = asyncio.create_task(self._decay_loop())
        
        self._initialized = True
        logger.info("MYCA Memory system initialized")
    
    def _get_backend(self, layer: MemoryLayer) -> MemoryBackend:
        """Get the appropriate backend for a memory layer."""
        if layer == MemoryLayer.EPHEMERAL:
            return self._ephemeral
        elif layer == MemoryLayer.SESSION:
            return self._session
        elif layer == MemoryLayer.WORKING:
            return self._working
        else:
            return self._persistent
    
    async def remember(
        self,
        content: Dict[str, Any],
        layer: MemoryLayer = MemoryLayer.SESSION,
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UUID:
        """Store a memory in the specified layer."""
        entry = MemoryEntry(
            id=uuid4(),
            layer=layer,
            content=content,
            metadata=metadata or {},
            importance=min(1.0, max(0.0, importance)),
            tags=tags or []
        )
        
        backend = self._get_backend(layer)
        await backend.store(entry)
        
        logger.debug(f"Stored memory {entry.id} in {layer.value} layer")
        return entry.id
    
    async def recall(
        self,
        entry_id: Optional[UUID] = None,
        query: Optional[MemoryQuery] = None
    ) -> List[MemoryEntry]:
        """Recall memories by ID or query."""
        if entry_id:
            # Direct retrieval - check all backends
            for backend in [self._ephemeral, self._session, self._working, self._persistent]:
                entry = await backend.retrieve(entry_id)
                if entry:
                    return [entry]
            return []
        
        if query:
            backend = self._get_backend(query.layer) if query.layer else None
            
            if backend:
                return await backend.query(query)
            else:
                # Search all layers
                all_results = []
                for layer in MemoryLayer:
                    layer_backend = self._get_backend(layer)
                    layer_query = MemoryQuery(
                        layer=layer,
                        tags=query.tags,
                        min_importance=query.min_importance,
                        since=query.since,
                        limit=query.limit,
                        include_archived=query.include_archived
                    )
                    results = await layer_backend.query(layer_query)
                    all_results.extend(results)
                
                # Sort by importance and recency
                all_results.sort(key=lambda e: (e.importance, e.accessed_at), reverse=True)
                return all_results[:query.limit]
        
        return []
    
    async def forget(self, entry_id: UUID, hard_delete: bool = False) -> bool:
        """Forget a memory (archive or delete)."""
        for backend in [self._ephemeral, self._session, self._working, self._persistent]:
            entry = await backend.retrieve(entry_id)
            if entry:
                if hard_delete:
                    return await backend.delete(entry_id)
                else:
                    return await backend.update(entry_id, {"status": MemoryStatus.ARCHIVED.value})
        return False
    
    async def consolidate(self, from_layer: MemoryLayer, to_layer: MemoryLayer) -> int:
        """Consolidate memories from one layer to another."""
        if from_layer == to_layer:
            return 0
        
        source = self._get_backend(from_layer)
        dest = self._get_backend(to_layer)
        
        # Get high-importance memories from source
        query = MemoryQuery(layer=from_layer, min_importance=0.7, limit=100)
        memories = await source.query(query)
        
        count = 0
        for memory in memories:
            memory.layer = to_layer
            await dest.store(memory)
            await source.delete(memory.id)
            count += 1
        
        logger.info(f"Consolidated {count} memories from {from_layer.value} to {to_layer.value}")
        return count
    
    async def _decay_loop(self) -> None:
        """Background task to decay old memories."""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                
                now = datetime.now(timezone.utc)
                
                for layer, retention in self.RETENTION.items():
                    if retention is None:
                        continue
                    
                    backend = self._get_backend(layer)
                    cutoff = now - retention
                    
                    # Query old entries
                    query = MemoryQuery(layer=layer, limit=1000, include_archived=False)
                    entries = await backend.query(query)
                    
                    for entry in entries:
                        if entry.created_at < cutoff:
                            # High importance memories get consolidated instead of deleted
                            if entry.importance >= 0.8:
                                # Move to next permanent layer
                                if layer == MemoryLayer.EPHEMERAL:
                                    entry.layer = MemoryLayer.SESSION
                                    await self._session.store(entry)
                                elif layer == MemoryLayer.SESSION:
                                    entry.layer = MemoryLayer.EPISODIC
                                    await self._persistent.store(entry)
                                elif layer == MemoryLayer.WORKING:
                                    entry.layer = MemoryLayer.SEMANTIC
                                    await self._persistent.store(entry)
                            
                            await backend.delete(entry.id)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in decay loop: {e}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get memory system statistics."""
        stats = {
            "layers": {},
            "total_memories": 0,
            "initialized": self._initialized
        }
        
        for layer in MemoryLayer:
            backend = self._get_backend(layer)
            query = MemoryQuery(layer=layer, limit=10000)
            entries = await backend.query(query)
            
            layer_stats = {
                "count": len(entries),
                "avg_importance": sum(e.importance for e in entries) / len(entries) if entries else 0,
                "retention": str(self.RETENTION[layer]) if self.RETENTION[layer] else "permanent"
            }
            stats["layers"][layer.value] = layer_stats
            stats["total_memories"] += len(entries)
        
        return stats
    
    async def shutdown(self) -> None:
        """Shutdown the memory system."""
        if self._decay_task:
            self._decay_task.cancel()
            try:
                await self._decay_task
            except asyncio.CancelledError:
                pass
        
        logger.info("MYCA Memory system shutdown")


# Singleton instance
_myca_memory: Optional[MYCAMemory] = None


async def get_myca_memory() -> MYCAMemory:
    """Get or create the singleton MYCA memory instance."""
    global _myca_memory
    if _myca_memory is None:
        _myca_memory = MYCAMemory()
        await _myca_memory.initialize()
    return _myca_memory
