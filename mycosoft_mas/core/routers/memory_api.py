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
    USER = "user"                  # MINDEX + Qdrant, permanent
    AGENT = "agent"                # Redis, 24h TTL
    SYSTEM = "system"              # MINDEX, permanent
    EPHEMERAL = "ephemeral"        # In-memory, request only


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
        """Get or create Redis connection."""
        if self._redis is None:
            import redis.asyncio as redis
            redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
            self._redis = redis.from_url(redis_url, decode_responses=True)
        return self._redis
    
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
            
            # Store based on scope
            if scope in [MemoryScope.CONVERSATION, MemoryScope.AGENT, MemoryScope.EPHEMERAL]:
                # Use Redis for short-term storage
                redis = await self._get_redis()
                serialized = json.dumps(stored_value)
                if ttl:
                    await redis.set(full_key, serialized, ex=ttl)
                else:
                    await redis.set(full_key, serialized)
            else:
                # Use MINDEX for long-term storage
                # TODO: Implement MINDEX write
                redis = await self._get_redis()
                serialized = json.dumps(stored_value)
                await redis.set(full_key, serialized)
            
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
                redis = await self._get_redis()
                stored = await redis.get(full_key)
                
                if stored:
                    data = json.loads(stored)
                    self._log_operation("read", scope, namespace, key, True)
                    return data.get("value")
                
                self._log_operation("read", scope, namespace, key, False)
                return None
            else:
                # Read all keys in namespace
                pattern = self._build_key(scope, namespace, "*")
                redis = await self._get_redis()
                keys = await redis.keys(pattern)
                
                results = {}
                for k in keys:
                    stored = await redis.get(k)
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
            redis = await self._get_redis()
            result = await redis.delete(full_key)
            
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
            redis = await self._get_redis()
            keys = await redis.keys(pattern)
            
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
            
            # TODO: Call LLM to generate summary
            # For now, create a simple summary
            summary = f"Conversation summary for {namespace} at {datetime.now(timezone.utc).isoformat()}"
            
            # Archive to long-term memory
            await self.write(
                scope=archive_to,
                namespace=namespace,
                key=f"summary_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
                value=summary,
                metadata={"source_scope": scope.value, "window": window},
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
    Check memory system health.
    """
    manager = get_memory_manager()
    
    redis_ok = False
    try:
        redis = await manager._get_redis()
        await redis.ping()
        redis_ok = True
    except Exception:
        pass
    
    return {
        "status": "healthy" if redis_ok else "degraded",
        "redis": "connected" if redis_ok else "disconnected",
        "scopes": [s.value for s in MemoryScope],
        "audit_entries": len(manager._audit_log),
    }
