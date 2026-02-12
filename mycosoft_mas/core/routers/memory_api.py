"""
MYCA Memory API - February 2026

Namespace-based memory API for safe, scoped memory operations.

Memory Scopes:
- conversation: Current dialog context (TTL: session duration)
- user: User preferences and history (permanent)
- agent: Agent-specific working memory (TTL: 24h)
- system: Global MAS state and configs (permanent)
- ephemeral: Scratch space for reasoning (request only)

Safety Features:
- Namespace isolation prevents cross-scope corruption
- Explicit scope + namespace + key required for deletion
- Summarization is separate action, not side effect of GET
- All operations are logged for audit
"""

import json
import logging
import os
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

# Cryptographic Integrity Service import
try:
    from mycosoft_mas.security.integrity_service import hash_and_record, get_integrity_service
    INTEGRITY_AVAILABLE = True
except ImportError:
    INTEGRITY_AVAILABLE = False
    hash_and_record = None

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

logger = logging.getLogger("MemoryAPI")

router = APIRouter(prefix="/api/memory", tags=["memory"])


# ============================================================================
# Enums and Models
# ============================================================================

class MemoryScope(str, Enum):
    """Memory scope determines storage backend and TTL."""
    CONVERSATION = "conversation"  # Redis, session TTL
    USER = "user"                  # Postgres + Qdrant, permanent
    AGENT = "agent"                # Redis, 24h TTL
    SYSTEM = "system"              # Postgres, permanent
    EPHEMERAL = "ephemeral"        # In-memory, request only
    DEVICE = "device"              # Postgres, permanent - NatureOS device state
    EXPERIMENT = "experiment"      # Postgres + Qdrant, permanent - scientific data
    WORKFLOW = "workflow"          # Redis + Postgres, 7 days - n8n executions


class MemoryWriteRequest(BaseModel):
    """Request to write a memory value."""
    scope: MemoryScope = Field(..., description="Memory scope")
    namespace: str = Field(..., description="Namespace (e.g., user_123, agent_code_review)")
    key: str = Field(..., description="Memory key (e.g., preferences.theme)")
    value: Any = Field(..., description="Value to store (any JSON-serializable type)")
    ttl_seconds: Optional[int] = Field(None, description="TTL in seconds (null = use scope default)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class MemoryReadRequest(BaseModel):
    """Request to read memory values."""
    scope: MemoryScope = Field(..., description="Memory scope")
    namespace: str = Field(..., description="Namespace to read from")
    key: Optional[str] = Field(None, description="Specific key to read (null = all keys)")
    semantic_query: Optional[str] = Field(None, description="Semantic search query (for vector memory)")


class MemoryDeleteRequest(BaseModel):
    """Request to delete a memory value. Requires all three identifiers."""
    scope: MemoryScope = Field(..., description="Memory scope")
    namespace: str = Field(..., description="Namespace")
    key: str = Field(..., description="Key to delete (required - no bulk deletes)")


class MemorySummarizeRequest(BaseModel):
    """Request to summarize conversation memory."""
    scope: MemoryScope = Field(MemoryScope.CONVERSATION, description="Scope to summarize")
    namespace: str = Field(..., description="Namespace (e.g., conversation_id)")
    window: str = Field("last_10_turns", description="Window to summarize")
    archive_to: Optional[MemoryScope] = Field(MemoryScope.USER, description="Scope to archive summary to")


class MemoryResponse(BaseModel):
    """Standard memory operation response."""
    success: bool
    scope: str
    namespace: str
    key: Optional[str] = None
    value: Optional[Any] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: str


class MemoryListResponse(BaseModel):
    """Response for listing memory keys."""
    success: bool
    scope: str
    namespace: str
    keys: List[str]
    count: int


# ============================================================================
# Memory Manager Singleton
# ============================================================================

class NamespacedMemoryManager:
    """
    Unified memory manager with namespace isolation.
    
    Wraps the existing UnifiedMemoryManager with namespace safety.
    """
    
    def __init__(self):
        self._redis = None
        self._redis_available = None  # None = not checked, True/False = checked
        self._memory_store: Dict[str, str] = {}  # In-memory fallback
        self._mindex_url = os.getenv("MINDEX_URL", "http://mindex:8000")
        self._qdrant_url = os.getenv("QDRANT_URL", "http://qdrant:6333")
        self._audit_log: List[Dict[str, Any]] = []
        
        # Scope-specific TTLs (in seconds)
        self.default_ttls = {
            MemoryScope.CONVERSATION: 3600,      # 1 hour
            MemoryScope.USER: None,              # Permanent
            MemoryScope.AGENT: 86400,            # 24 hours
            MemoryScope.SYSTEM: None,            # Permanent
            MemoryScope.EPHEMERAL: 60,           # 1 minute
        }
    
    async def _get_redis(self):
        """Get or create Redis connection, returns None if unavailable."""
        if self._redis_available is False:
            return None
        if self._redis is None:
            try:
                import redis.asyncio as redis
                redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
                self._redis = redis.from_url(redis_url, decode_responses=True)
                await self._redis.ping()
                self._redis_available = True
            except Exception as e:
                logger.warning(f"Redis unavailable, using in-memory fallback: {e}")
                self._redis_available = False
                return None
        return self._redis
    
    async def _memory_set(self, key: str, value: str, ttl: int = None):
        """Set value in Redis or in-memory fallback."""
        redis = await self._get_redis()
        if redis:
            if ttl:
                await redis.set(key, value, ex=ttl)
            else:
                await redis.set(key, value)
        else:
            self._memory_store[key] = value
    
    async def _memory_get(self, key: str) -> Optional[str]:
        """Get value from Redis or in-memory fallback."""
        redis = await self._get_redis()
        if redis:
            return await redis.get(key)
        else:
            return self._memory_store.get(key)
    
    async def _memory_delete(self, key: str) -> bool:
        """Delete key from Redis or in-memory fallback."""
        redis = await self._get_redis()
        if redis:
            return await redis.delete(key) > 0
        else:
            if key in self._memory_store:
                del self._memory_store[key]
                return True
            return False
    
    async def _memory_keys(self, pattern: str) -> List[str]:
        """Get keys matching pattern from Redis or in-memory fallback."""
        redis = await self._get_redis()
        if redis:
            return await redis.keys(pattern)
        else:
            import fnmatch
            return [k for k in self._memory_store.keys() if fnmatch.fnmatch(k, pattern)]
    
    def _build_key(self, scope: MemoryScope, namespace: str, key: str) -> str:
        """Build fully qualified key with namespace isolation."""
        # Sanitize namespace and key to prevent injection
        safe_namespace = namespace.replace(":", "_").replace("/", "_")
        safe_key = key.replace(":", "_").replace("/", "_")
        return f"mas:memory:{scope.value}:{safe_namespace}:{safe_key}"
    
    def _log_operation(self, operation: str, scope: MemoryScope, namespace: str, key: str, success: bool):
        """Log operation for audit trail."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": operation,
            "scope": scope.value,
            "namespace": namespace,
            "key": key,
            "success": success,
        }
        self._audit_log.append(entry)
        # Keep only last 1000 entries in memory
        if len(self._audit_log) > 1000:
            self._audit_log = self._audit_log[-1000:]
        logger.info(f"Memory {operation}: {scope.value}/{namespace}/{key} - {'OK' if success else 'FAIL'}")
    
    async def write(
        self,
        scope: MemoryScope,
        namespace: str,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Write a value to memory with namespace isolation.
        
        Args:
            scope: Memory scope
            namespace: Namespace identifier
            key: Memory key
            value: Value to store
            ttl_seconds: TTL override (null = use scope default)
            metadata: Additional metadata
            
        Returns:
            True if successful
        """
        try:
            full_key = self._build_key(scope, namespace, key)
            
            # Determine TTL
            ttl = ttl_seconds if ttl_seconds is not None else self.default_ttls.get(scope)
            
            # Prepare value with metadata
            stored_value = {
                "value": value,
                "metadata": metadata or {},
                "created_at": datetime.now(timezone.utc).isoformat(),
                "scope": scope.value,
                "namespace": namespace,
                "key": key,
            }
            
            # Store using memory helper (Redis or in-memory fallback)
            serialized = json.dumps(stored_value)
            await self._memory_set(full_key, serialized, ttl)
            
            # Record in cryptographic ledger for integrity verification
            if INTEGRITY_AVAILABLE and hash_and_record:
                try:
                    await hash_and_record(
                        entry_type="memory_write",
                        data=stored_value,
                        metadata={
                            "full_key": full_key,
                            "scope": scope.value,
                            "namespace": namespace,
                            "key": key,
                            "ttl": ttl,
                        },
                        with_signature=True,
                    )
                except Exception as e:
                    logger.warning(f"Integrity service recording failed (non-blocking): {e}")
            
            self._log_operation("write", scope, namespace, key, True)
            return True
            
        except Exception as e:
            logger.error(f"Memory write failed: {e}")
            self._log_operation("write", scope, namespace, key, False)
            return False
    
    async def read(
        self,
        scope: MemoryScope,
        namespace: str,
        key: Optional[str] = None,
        semantic_query: Optional[str] = None,
    ) -> Optional[Any]:
        """
        Read from memory.
        
        Args:
            scope: Memory scope
            namespace: Namespace identifier
            key: Specific key (or None for all keys in namespace)
            semantic_query: Semantic search query
            
        Returns:
            Value(s) if found
        """
        try:
            if key:
                # Read specific key
                full_key = self._build_key(scope, namespace, key)
                stored = await self._memory_get(full_key)
                
                if stored:
                    data = json.loads(stored)
                    self._log_operation("read", scope, namespace, key, True)
                    return data.get("value")
                
                self._log_operation("read", scope, namespace, key, False)
                return None
            else:
                # Read all keys in namespace
                pattern = self._build_key(scope, namespace, "*")
                keys = await self._memory_keys(pattern)
                
                results = {}
                for k in keys:
                    stored = await self._memory_get(k)
                    if stored:
                        data = json.loads(stored)
                        # Extract the actual key from full key
                        actual_key = k.split(":")[-1]
                        results[actual_key] = data.get("value")
                
                self._log_operation("read_all", scope, namespace, "*", True)
                return results
                
        except Exception as e:
            logger.error(f"Memory read failed: {e}")
            self._log_operation("read", scope, namespace, key or "*", False)
            return None
    
    async def delete(
        self,
        scope: MemoryScope,
        namespace: str,
        key: str,
    ) -> bool:
        """
        Delete a specific memory key.
        
        Requires all three identifiers - no bulk deletes allowed.
        
        Args:
            scope: Memory scope
            namespace: Namespace identifier
            key: Key to delete
            
        Returns:
            True if deleted
        """
        try:
            full_key = self._build_key(scope, namespace, key)
            result = await self._memory_delete(full_key)
            
            success = result > 0
            self._log_operation("delete", scope, namespace, key, success)
            return success
            
        except Exception as e:
            logger.error(f"Memory delete failed: {e}")
            self._log_operation("delete", scope, namespace, key, False)
            return False
    
    async def list_keys(
        self,
        scope: MemoryScope,
        namespace: str,
    ) -> List[str]:
        """
        List all keys in a namespace.
        
        Args:
            scope: Memory scope
            namespace: Namespace identifier
            
        Returns:
            List of keys
        """
        try:
            pattern = self._build_key(scope, namespace, "*")
            keys = await self._memory_keys(pattern)
            
            # Extract actual keys from full keys
            actual_keys = []
            for k in keys:
                parts = k.split(":")
                if len(parts) >= 5:
                    actual_keys.append(parts[-1])
            
            return actual_keys
            
        except Exception as e:
            logger.error(f"Memory list failed: {e}")
            return []
    
    async def summarize_and_archive(
        self,
        scope: MemoryScope,
        namespace: str,
        window: str = "last_10_turns",
        archive_to: MemoryScope = MemoryScope.USER,
    ) -> Optional[str]:
        """
        Summarize conversation and archive to long-term memory.
        
        This is a SEPARATE action, not a side effect of GET.
        
        Args:
            scope: Source scope (usually conversation)
            namespace: Namespace to summarize
            window: Window specification
            archive_to: Destination scope for summary
            
        Returns:
            Summary text if successful
        """
        try:
            # Read conversation history
            conversation = await self.read(scope, namespace)
            
            if not conversation:
                return None
            
            # Convert conversation data to text
            if isinstance(conversation, dict):
                # Handle dict of messages
                conversation_text = "\n".join(
                    f"{key}: {value}" for key, value in conversation.items()
                )
            elif isinstance(conversation, list):
                # Handle list of messages
                conversation_text = "\n".join(str(item) for item in conversation)
            else:
                conversation_text = str(conversation)
            
            # Use LLM to generate summary
            try:
                from mycosoft_mas.llm.client import get_llm_client
                
                llm_client = get_llm_client()
                
                # Call LLM summarization
                summary = await llm_client.summarize(
                    text=conversation_text,
                    max_length=500,
                    temperature=0.3  # More deterministic summaries
                )
                
                logger.info(f"Generated LLM summary for {namespace}: {len(summary)} chars")
                
            except Exception as llm_error:
                logger.warning(f"LLM summarization failed, using fallback: {llm_error}")
                
                # Fallback: Create a simple summary
                lines = conversation_text.split("\n")
                summary = f"Conversation summary for {namespace} with {len(lines)} entries. "
                
                # Include first few lines as preview
                preview_lines = lines[:3]
                if preview_lines:
                    summary += "Preview: " + " | ".join(preview_lines[:100])
                
                summary += f" (Generated at {datetime.now(timezone.utc).isoformat()})"
            
            # Archive to long-term memory
            await self.write(
                scope=archive_to,
                namespace=namespace,
                key=f"summary_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
                value=summary,
                metadata={
                    "source_scope": scope.value,
                    "window": window,
                    "original_length": len(conversation_text),
                    "summary_length": len(summary)
                },
            )
            
            self._log_operation("summarize", scope, namespace, window, True)
            return summary
            
        except Exception as e:
            logger.error(f"Memory summarize failed: {e}")
            self._log_operation("summarize", scope, namespace, window, False)
            return None
    
    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent audit log entries."""
        return self._audit_log[-limit:]


# Singleton instance
_memory_manager: Optional[NamespacedMemoryManager] = None


def get_memory_manager() -> NamespacedMemoryManager:
    """Get singleton memory manager instance."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = NamespacedMemoryManager()
    return _memory_manager


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/write", response_model=MemoryResponse)
async def write_memory(request: MemoryWriteRequest):
    """
    Write a value to memory.
    
    Requires scope, namespace, and key. Value can be any JSON-serializable type.
    """
    manager = get_memory_manager()
    
    success = await manager.write(
        scope=request.scope,
        namespace=request.namespace,
        key=request.key,
        value=request.value,
        ttl_seconds=request.ttl_seconds,
        metadata=request.metadata,
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to write memory")
    
    return MemoryResponse(
        success=True,
        scope=request.scope.value,
        namespace=request.namespace,
        key=request.key,
        value=request.value,
        metadata=request.metadata,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/read", response_model=MemoryResponse)
async def read_memory(request: MemoryReadRequest):
    """
    Read from memory.
    
    If key is provided, returns specific value.
    If key is null, returns all values in namespace.
    """
    manager = get_memory_manager()
    
    value = await manager.read(
        scope=request.scope,
        namespace=request.namespace,
        key=request.key,
        semantic_query=request.semantic_query,
    )
    
    return MemoryResponse(
        success=value is not None,
        scope=request.scope.value,
        namespace=request.namespace,
        key=request.key,
        value=value,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/delete", response_model=MemoryResponse)
async def delete_memory(request: MemoryDeleteRequest):
    """
    Delete a memory key.
    
    Requires scope, namespace, AND key. No bulk deletes allowed.
    """
    manager = get_memory_manager()
    
    success = await manager.delete(
        scope=request.scope,
        namespace=request.namespace,
        key=request.key,
    )
    
    return MemoryResponse(
        success=success,
        scope=request.scope.value,
        namespace=request.namespace,
        key=request.key,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/summarize", response_model=MemoryResponse)
async def summarize_memory(request: MemorySummarizeRequest):
    """
    Summarize conversation and archive to long-term memory.
    
    This is a SEPARATE action from reading - summarization never happens automatically.
    """
    manager = get_memory_manager()
    
    summary = await manager.summarize_and_archive(
        scope=request.scope,
        namespace=request.namespace,
        window=request.window,
        archive_to=request.archive_to,
    )
    
    if not summary:
        raise HTTPException(status_code=404, detail="No data to summarize")
    
    return MemoryResponse(
        success=True,
        scope=request.scope.value,
        namespace=request.namespace,
        key="summary",
        value=summary,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/list/{scope}/{namespace}", response_model=MemoryListResponse)
async def list_memory_keys(scope: MemoryScope, namespace: str):
    """
    List all keys in a namespace.
    """
    manager = get_memory_manager()
    keys = await manager.list_keys(scope, namespace)
    
    return MemoryListResponse(
        success=True,
        scope=scope.value,
        namespace=namespace,
        keys=keys,
        count=len(keys),
    )


@router.get("/audit")
async def get_audit_log(limit: int = 100):
    """
    Get memory operation audit log.
    """
    manager = get_memory_manager()
    return {
        "entries": manager.get_audit_log(limit),
        "count": min(limit, len(manager._audit_log)),
    }


@router.get("/health")
async def memory_health():
    """
    Check memory system health including integrity service.
    """
    manager = get_memory_manager()
    
    redis_ok = False
    try:
        redis = await manager._get_redis()
        await redis.ping()
        redis_ok = True
    except Exception:
        pass
    
    # Check integrity service status
    integrity_status = {
        "available": INTEGRITY_AVAILABLE,
        "stats": None
    }
    if INTEGRITY_AVAILABLE:
        try:
            service = get_integrity_service()
            integrity_status["stats"] = await service.get_stats()
        except Exception as e:
            integrity_status["error"] = str(e)
    
    return {
        "status": "healthy" if redis_ok else "degraded",
        "redis": "connected" if redis_ok else "disconnected",
        "scopes": [s.value for s in MemoryScope],
        "audit_entries": len(manager._audit_log),
        "integrity_service": integrity_status,
    }




# ============================================================================
# Memory Coordinator API - February 5, 2026
# Integration with the unified 6-layer memory system
# ============================================================================

# MemoryCoordinator models
class AgentRememberRequest(BaseModel):
    """Request to store a memory via the coordinator."""
    agent_id: str = Field(..., description="Agent or namespace identifier")
    content: Dict[str, Any] = Field(..., description="Content to remember")
    layer: str = Field("working", description="Memory layer: ephemeral, session, working, semantic, episodic, system")
    importance: float = Field(0.5, ge=0.0, le=1.0, description="Importance score 0-1")
    tags: Optional[List[str]] = Field(None, description="Tags for categorization")


class AgentRecallRequest(BaseModel):
    """Request to recall memories via the coordinator."""
    agent_id: str = Field(..., description="Agent or namespace identifier")
    query: Optional[str] = Field(None, description="Semantic search query")
    layer: Optional[str] = Field(None, description="Filter by memory layer")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    limit: int = Field(10, ge=1, le=100, description="Maximum results")


class RecordEpisodeRequest(BaseModel):
    """Request to record an episode."""
    agent_id: str = Field(..., description="Agent identifier")
    event_type: str = Field(..., description="Type of event")
    description: str = Field(..., description="Event description")
    participants: Optional[List[str]] = Field(None, description="Participant IDs")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    outcome: Optional[str] = Field(None, description="Event outcome")
    importance: float = Field(0.5, ge=0.0, le=1.0, description="Importance score")


# Lazy coordinator initialization
_coordinator = None


async def _get_coordinator():
    """Get or initialize the MemoryCoordinator singleton."""
    global _coordinator
    if _coordinator is None:
        try:
            from mycosoft_mas.memory import get_memory_coordinator
            _coordinator = await get_memory_coordinator()
            await _coordinator.initialize()
        except Exception as e:
            logger.warning(f"MemoryCoordinator not available: {e}")
            return None
    return _coordinator


@router.post("/remember")
async def remember_memory(request: AgentRememberRequest):
    """
    Store a memory via the MemoryCoordinator.
    
    Uses the 6-layer memory system for appropriate storage.
    """
    coordinator = await _get_coordinator()
    if not coordinator:
        raise HTTPException(status_code=503, detail="Memory coordinator not available")
    
    try:
        memory_id = await coordinator.agent_remember(
            agent_id=request.agent_id,
            content=request.content,
            layer=request.layer,
            importance=request.importance,
            tags=request.tags,
        )
        
        return {
            "success": True,
            "id": str(memory_id) if memory_id else None,
            "agent_id": request.agent_id,
            "layer": request.layer,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Remember failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recall")
async def recall_memory(request: AgentRecallRequest):
    """
    Recall memories via the MemoryCoordinator.
    
    Supports semantic search and filtering by layer/tags.
    """
    coordinator = await _get_coordinator()
    if not coordinator:
        raise HTTPException(status_code=503, detail="Memory coordinator not available")
    
    try:
        memories = await coordinator.agent_recall(
            agent_id=request.agent_id,
            query=request.query,
            layer=request.layer,
            tags=request.tags,
            limit=request.limit,
        )
        
        return {
            "success": True,
            "agent_id": request.agent_id,
            "memories": memories,
            "count": len(memories),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Recall failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/episode")
async def record_episode(request: RecordEpisodeRequest):
    """
    Record an episodic event via the MemoryCoordinator.
    """
    coordinator = await _get_coordinator()
    if not coordinator:
        raise HTTPException(status_code=503, detail="Memory coordinator not available")
    
    try:
        episode_id = await coordinator.record_episode(
            agent_id=request.agent_id,
            event_type=request.event_type,
            description=request.description,
            participants=request.participants,
            context=request.context,
            outcome=request.outcome,
            importance=request.importance,
        )
        
        return {
            "success": True,
            "id": str(episode_id) if episode_id else None,
            "event_type": request.event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Record episode failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def memory_stats():
    """
    Get memory system statistics from the MemoryCoordinator.
    """
    coordinator = await _get_coordinator()
    
    # Basic stats even without coordinator
    base_stats = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "coordinator": {
            "initialized": coordinator is not None,
            "active_conversations": 0,
            "agent_namespaces": [],
        },
        "myca_memory": {
            "total_memories": 0,
            "layers": {},
        },
    }
    
    if not coordinator:
        return base_stats
    
    try:
        stats = await coordinator.get_stats()
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **stats,
        }
    except Exception as e:
        logger.error(f"Stats failed: {e}")
        base_stats["error"] = str(e)
        return base_stats


@router.get("/user/{user_id}/profile")
async def get_user_profile(user_id: str):
    """
    Get user profile from cross-session memory.
    """
    coordinator = await _get_coordinator()
    if not coordinator:
        raise HTTPException(status_code=503, detail="Memory coordinator not available")
    
    try:
        profile = await coordinator.get_user_profile(user_id)
        return {
            "success": True,
            "user_id": user_id,
            "profile": {
                "user_id": profile.user_id,
                "preferences": profile.preferences,
                "context": profile.context,
                "last_interaction": profile.last_interaction.isoformat() if profile.last_interaction else None,
            },
        }
    except Exception as e:
        logger.error(f"Get user profile failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# A2A Memory API - February 5, 2026
# Agent-to-Agent Memory Sharing Endpoints
# ============================================================================

# Lazy A2A memory initialization
_a2a_memory = None


async def _get_a2a_memory():
    """Get or initialize the A2A memory integration."""
    global _a2a_memory
    if _a2a_memory is None:
        try:
            from mycosoft_mas.memory.a2a_memory import get_a2a_memory
            _a2a_memory = await get_a2a_memory()
        except Exception as e:
            logger.warning(f"A2A memory not available: {e}")
            return None
    return _a2a_memory


class A2ABroadcastRequest(BaseModel):
    """Request to broadcast a memory to other agents."""
    sender_id: str = Field(..., description="Agent sending the memory")
    content: Dict[str, Any] = Field(..., description="Content to share")
    tags: Optional[List[str]] = Field(None, description="Tags for categorization")
    importance: float = Field(0.5, ge=0.0, le=1.0, description="Importance score")
    recipients: Optional[List[str]] = Field(None, description="Specific recipients (None = all)")


class A2AQueryRequest(BaseModel):
    """Request to query shared memories."""
    requester_id: str = Field(..., description="Agent making the query")
    query: str = Field(..., description="Search query")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    timeout: float = Field(5.0, ge=0.1, le=30.0, description="Response timeout")


@router.post("/a2a/broadcast")
async def a2a_broadcast(request: A2ABroadcastRequest):
    """
    Broadcast a memory to other agents.
    
    Uses Redis Pub/Sub for real-time delivery and Stream for persistence.
    """
    a2a = await _get_a2a_memory()
    if not a2a:
        raise HTTPException(status_code=503, detail="A2A memory not available")
    
    try:
        message_id = await a2a.broadcast_memory(
            sender_id=request.sender_id,
            content=request.content,
            tags=request.tags,
            importance=request.importance,
            recipients=request.recipients
        )
        
        return {
            "success": True,
            "message_id": message_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"A2A broadcast failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/a2a/query")
async def a2a_query(request: A2AQueryRequest):
    """
    Query memories shared by other agents.
    """
    a2a = await _get_a2a_memory()
    if not a2a:
        raise HTTPException(status_code=503, detail="A2A memory not available")
    
    try:
        results = await a2a.query_shared_memory(
            requester_id=request.requester_id,
            query=request.query,
            tags=request.tags,
            timeout=request.timeout
        )
        
        return {
            "success": True,
            "results": results,
            "count": len(results),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"A2A query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/a2a/shared")
async def get_shared_memories(limit: int = 50, since_id: Optional[str] = None):
    """
    Get shared memories from the A2A stream.
    """
    a2a = await _get_a2a_memory()
    if not a2a:
        raise HTTPException(status_code=503, detail="A2A memory not available")
    
    try:
        memories = await a2a.get_shared_memories(limit=limit, since_id=since_id)
        
        return {
            "success": True,
            "memories": memories,
            "count": len(memories),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Get shared memories failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/a2a/stats")
async def a2a_stats():
    """
    Get A2A memory system statistics.
    """
    a2a = await _get_a2a_memory()
    
    if not a2a:
        return {
            "initialized": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    try:
        stats = await a2a.get_stats()
        return {
            "success": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **stats,
        }
    except Exception as e:
        logger.error(f"A2A stats failed: {e}")
        return {
            "initialized": True,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
