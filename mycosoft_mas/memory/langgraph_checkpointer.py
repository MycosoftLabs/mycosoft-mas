"""
LangGraph MAS Checkpointer - Persistent State Storage.
Created: February 5, 2026

Implements LangGraph's checkpoint interface using the MAS memory system
for persistent state storage across restarts.

Replaces the in-memory MemorySaver with PostgreSQL-backed persistence.

Usage:
    from mycosoft_mas.memory.langgraph_checkpointer import MASCheckpointer
    
    checkpointer = MASCheckpointer()
    await checkpointer.initialize()
    
    app = graph.compile(checkpointer=checkpointer)
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, Optional, Sequence, Tuple
from uuid import uuid4

logger = logging.getLogger("MASCheckpointer")


class CheckpointMetadata:
    """Metadata for a checkpoint."""
    
    def __init__(
        self,
        source: str = "input",
        step: int = -1,
        writes: Optional[Dict[str, Any]] = None,
        parents: Optional[Dict[str, str]] = None
    ):
        self.source = source
        self.step = step
        self.writes = writes or {}
        self.parents = parents or {}


class Checkpoint:
    """A checkpoint representing graph state at a point in time."""
    
    def __init__(
        self,
        v: int = 1,
        id: Optional[str] = None,
        ts: Optional[str] = None,
        channel_values: Optional[Dict[str, Any]] = None,
        channel_versions: Optional[Dict[str, int]] = None,
        versions_seen: Optional[Dict[str, Dict[str, int]]] = None,
        pending_sends: Optional[Sequence[Any]] = None
    ):
        self.v = v
        self.id = id or str(uuid4())
        self.ts = ts or datetime.now(timezone.utc).isoformat()
        self.channel_values = channel_values or {}
        self.channel_versions = channel_versions or {}
        self.versions_seen = versions_seen or {}
        self.pending_sends = list(pending_sends) if pending_sends else []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "v": self.v,
            "id": self.id,
            "ts": self.ts,
            "channel_values": self.channel_values,
            "channel_versions": self.channel_versions,
            "versions_seen": self.versions_seen,
            "pending_sends": self.pending_sends
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Checkpoint":
        return cls(
            v=data.get("v", 1),
            id=data.get("id"),
            ts=data.get("ts"),
            channel_values=data.get("channel_values", {}),
            channel_versions=data.get("channel_versions", {}),
            versions_seen=data.get("versions_seen", {}),
            pending_sends=data.get("pending_sends", [])
        )


class CheckpointTuple:
    """Tuple of checkpoint data."""
    
    def __init__(
        self,
        config: Dict[str, Any],
        checkpoint: Checkpoint,
        metadata: Optional[CheckpointMetadata] = None,
        parent_config: Optional[Dict[str, Any]] = None,
        pending_writes: Optional[Sequence[Tuple[str, str, Any]]] = None
    ):
        self.config = config
        self.checkpoint = checkpoint
        self.metadata = metadata or CheckpointMetadata()
        self.parent_config = parent_config
        self.pending_writes = list(pending_writes) if pending_writes else []


class MASCheckpointer:
    """
    LangGraph checkpointer backed by MAS memory system.
    
    Stores checkpoints in PostgreSQL via the memory coordinator,
    enabling persistent state across restarts.
    
    Key features:
    - Thread-based namespacing (conversation continuity)
    - Checkpoint history for state rollback
    - Integration with MAS episodic memory
    """
    
    def __init__(self):
        self._memory = None
        self._initialized = False
        self._cache: Dict[str, CheckpointTuple] = {}
        self._pool = None
    
    async def initialize(self) -> None:
        """Initialize the checkpointer with memory system."""
        if self._initialized:
            return
        
        try:
            from mycosoft_mas.memory import get_memory_coordinator
            self._memory = await get_memory_coordinator()
            
            # Also initialize direct DB connection for efficiency
            import os
            import asyncpg
            db_url = os.getenv(
                "MINDEX_DATABASE_URL",
                "postgresql://mycosoft:REDACTED_VM_SSH_PASSWORD@192.168.0.189:5432/mindex"
            )
            self._pool = await asyncpg.create_pool(db_url, min_size=1, max_size=3)
            
            self._initialized = True
            logger.info("MASCheckpointer initialized with memory system")
            
        except Exception as e:
            logger.warning(f"Failed to initialize MASCheckpointer: {e}")
            # Fall back to in-memory only
            self._initialized = True
    
    def _get_thread_id(self, config: Dict[str, Any]) -> str:
        """Extract thread_id from config for namespacing."""
        configurable = config.get("configurable", {})
        return configurable.get("thread_id", "default")
    
    def _make_config(self, thread_id: str, checkpoint_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a config dict from thread_id and checkpoint_id."""
        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id
            }
        }
    
    async def aget(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
        """Get the latest checkpoint for a thread."""
        thread_id = self._get_thread_id(config)
        
        # Check cache first
        if thread_id in self._cache:
            return self._cache[thread_id]
        
        # Try database
        if self._pool:
            try:
                async with self._pool.acquire() as conn:
                    row = await conn.fetchrow("""
                        SELECT checkpoint_id, checkpoint_data, metadata, parent_id, created_at
                        FROM memory.langgraph_checkpoints
                        WHERE thread_id = $1
                        ORDER BY created_at DESC
                        LIMIT 1
                    """.replace('$', '$'), thread_id)
                    
                    if row:
                        checkpoint = Checkpoint.from_dict(json.loads(row["checkpoint_data"]))
                        metadata = CheckpointMetadata(**json.loads(row["metadata"])) if row["metadata"] else None
                        parent_config = self._make_config(thread_id, row["parent_id"]) if row["parent_id"] else None
                        
                        tuple_ = CheckpointTuple(
                            config=self._make_config(thread_id, row["checkpoint_id"]),
                            checkpoint=checkpoint,
                            metadata=metadata,
                            parent_config=parent_config
                        )
                        self._cache[thread_id] = tuple_
                        return tuple_
            except Exception as e:
                logger.debug(f"Database lookup failed: {e}")
        
        # Try memory coordinator
        if self._memory:
            try:
                results = await self._memory.agent_recall(
                    agent_id=f"langgraph:{thread_id}",
                    tags=["checkpoint"],
                    layer="system",
                    limit=1
                )
                
                if results:
                    data = results[0].get("content", {})
                    checkpoint = Checkpoint.from_dict(data.get("checkpoint", {}))
                    tuple_ = CheckpointTuple(
                        config=self._make_config(thread_id, checkpoint.id),
                        checkpoint=checkpoint,
                        metadata=CheckpointMetadata(**data.get("metadata", {}))
                    )
                    self._cache[thread_id] = tuple_
                    return tuple_
            except Exception as e:
                logger.debug(f"Memory lookup failed: {e}")
        
        return None
    
    async def aput(
        self,
        config: Dict[str, Any],
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Store a checkpoint."""
        thread_id = self._get_thread_id(config)
        checkpoint_id = checkpoint.id
        
        # Get parent from config
        parent_id = config.get("configurable", {}).get("checkpoint_id")
        
        # Store in database
        if self._pool:
            try:
                async with self._pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO memory.langgraph_checkpoints 
                            (thread_id, checkpoint_id, checkpoint_data, metadata, parent_id)
                        VALUES ($1, $2, $3::jsonb, $4::jsonb, $5)
                        ON CONFLICT (thread_id, checkpoint_id) DO UPDATE SET
                            checkpoint_data = EXCLUDED.checkpoint_data,
                            metadata = EXCLUDED.metadata,
                            updated_at = NOW()
                    """.replace('$', '$'),
                        thread_id,
                        checkpoint_id,
                        json.dumps(checkpoint.to_dict()),
                        json.dumps({
                            "source": metadata.source,
                            "step": metadata.step,
                            "writes": metadata.writes,
                            "parents": metadata.parents
                        }),
                        parent_id
                    )
            except Exception as e:
                logger.debug(f"Database store failed: {e}")
        
        # Store in memory coordinator as backup
        if self._memory:
            try:
                await self._memory.agent_remember(
                    agent_id=f"langgraph:{thread_id}",
                    content={
                        "type": "checkpoint",
                        "checkpoint_id": checkpoint_id,
                        "checkpoint": checkpoint.to_dict(),
                        "metadata": {
                            "source": metadata.source,
                            "step": metadata.step
                        }
                    },
                    layer="system",
                    importance=0.8,
                    tags=["checkpoint", "langgraph", thread_id]
                )
            except Exception as e:
                logger.debug(f"Memory store failed: {e}")
        
        # Update cache
        tuple_ = CheckpointTuple(
            config=self._make_config(thread_id, checkpoint_id),
            checkpoint=checkpoint,
            metadata=metadata,
            parent_config=self._make_config(thread_id, parent_id) if parent_id else None
        )
        self._cache[thread_id] = tuple_
        
        return self._make_config(thread_id, checkpoint_id)
    
    async def aput_writes(
        self,
        config: Dict[str, Any],
        writes: Sequence[Tuple[str, Any]],
        task_id: str
    ) -> None:
        """Store pending writes for a checkpoint."""
        thread_id = self._get_thread_id(config)
        checkpoint_id = config.get("configurable", {}).get("checkpoint_id")
        
        if self._pool and checkpoint_id:
            try:
                async with self._pool.acquire() as conn:
                    for channel, value in writes:
                        await conn.execute("""
                            INSERT INTO memory.langgraph_writes 
                                (thread_id, checkpoint_id, task_id, channel, value)
                            VALUES ($1, $2, $3, $4, $5::jsonb)
                        """.replace('$', '$'),
                            thread_id,
                            checkpoint_id,
                            task_id,
                            channel,
                            json.dumps(value) if not isinstance(value, str) else value
                        )
            except Exception as e:
                logger.debug(f"Failed to store writes: {e}")
    
    async def alist(
        self,
        config: Optional[Dict[str, Any]] = None,
        *,
        filter: Optional[Dict[str, Any]] = None,
        before: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> Iterator[CheckpointTuple]:
        """List checkpoints for a thread."""
        if not config:
            return
        
        thread_id = self._get_thread_id(config)
        results = []
        
        if self._pool:
            try:
                async with self._pool.acquire() as conn:
                    rows = await conn.fetch("""
                        SELECT checkpoint_id, checkpoint_data, metadata, parent_id, created_at
                        FROM memory.langgraph_checkpoints
                        WHERE thread_id = $1
                        ORDER BY created_at DESC
                        LIMIT $2
                    """.replace('$', '$'), thread_id, limit or 10)
                    
                    for row in rows:
                        checkpoint = Checkpoint.from_dict(json.loads(row["checkpoint_data"]))
                        metadata = CheckpointMetadata(**json.loads(row["metadata"])) if row["metadata"] else None
                        
                        results.append(CheckpointTuple(
                            config=self._make_config(thread_id, row["checkpoint_id"]),
                            checkpoint=checkpoint,
                            metadata=metadata,
                            parent_config=self._make_config(thread_id, row["parent_id"]) if row["parent_id"] else None
                        ))
            except Exception as e:
                logger.debug(f"List failed: {e}")
        
        for result in results:
            yield result
    
    # Sync wrappers for LangGraph compatibility
    def get(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
        """Sync wrapper for aget."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.aget(config))
    
    def put(
        self,
        config: Dict[str, Any],
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Sync wrapper for aput."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.aput(config, checkpoint, metadata, new_versions))
    
    def put_writes(
        self,
        config: Dict[str, Any],
        writes: Sequence[Tuple[str, Any]],
        task_id: str
    ) -> None:
        """Sync wrapper for aput_writes."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.run_until_complete(self.aput_writes(config, writes, task_id))
    
    def list(
        self,
        config: Optional[Dict[str, Any]] = None,
        *,
        filter: Optional[Dict[str, Any]] = None,
        before: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> Iterator[CheckpointTuple]:
        """Sync wrapper for alist."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        async def _collect():
            results = []
            async for item in self.alist(config, filter=filter, before=before, limit=limit):
                results.append(item)
            return results
        
        for item in loop.run_until_complete(_collect()):
            yield item


# Migration SQL for langgraph tables
LANGGRAPH_MIGRATION = """
-- LangGraph Checkpoint Tables
CREATE TABLE IF NOT EXISTS memory.langgraph_checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_id TEXT NOT NULL,
    checkpoint_data JSONB NOT NULL,
    metadata JSONB,
    parent_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (thread_id, checkpoint_id)
);

CREATE TABLE IF NOT EXISTS memory.langgraph_writes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id TEXT NOT NULL,
    checkpoint_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    value JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_langgraph_checkpoints_thread ON memory.langgraph_checkpoints(thread_id);
CREATE INDEX IF NOT EXISTS idx_langgraph_writes_thread ON memory.langgraph_writes(thread_id, checkpoint_id);
"""
