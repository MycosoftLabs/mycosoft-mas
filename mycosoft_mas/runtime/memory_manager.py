"""
MAS v2 Memory Manager

Unified memory system for agents with:
- Short-term memory (Redis) - Conversation context, task state
- Long-term memory (MINDEX/PostgreSQL) - Activity logs, decision history
- Vector memory (Qdrant) - Knowledge embeddings
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

import redis.asyncio as redis
import aiohttp

from mycosoft_mas.runtime import AgentMessage


logger = logging.getLogger("MemoryManager")


class ShortTermMemory:
    """
    Redis-based short-term memory.
    
    Stores:
    - Conversation context (last N messages)
    - Current task state
    - Agent configuration
    - Temporary data
    """
    
    def __init__(self, agent_id: str, redis_url: Optional[str] = None):
        self.agent_id = agent_id
        self.redis_url = redis_url or os.environ.get("REDIS_URL", "redis://redis:6379/0")
        self.redis: Optional[redis.Redis] = None
        self.prefix = f"mas:memory:{agent_id}"
        self.default_ttl = 3600  # 1 hour
    
    async def connect(self):
        """Connect to Redis"""
        self.redis = redis.from_url(self.redis_url, decode_responses=True)
        await self.redis.ping()
        logger.info(f"Short-term memory connected for {self.agent_id}")
    
    async def close(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set a value in memory"""
        full_key = f"{self.prefix}:{key}"
        serialized = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
        await self.redis.set(full_key, serialized, ex=ttl or self.default_ttl)
    
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from memory"""
        full_key = f"{self.prefix}:{key}"
        value = await self.redis.get(full_key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None
    
    async def delete(self, key: str):
        """Delete a value from memory"""
        full_key = f"{self.prefix}:{key}"
        await self.redis.delete(full_key)
    
    async def add_to_conversation(self, message: Dict[str, Any]):
        """Add a message to conversation history"""
        conv_key = f"{self.prefix}:conversation"
        await self.redis.rpush(conv_key, json.dumps(message))
        await self.redis.ltrim(conv_key, -10, -1)  # Keep last 10 messages
        await self.redis.expire(conv_key, self.default_ttl)
    
    async def get_conversation(self) -> List[Dict[str, Any]]:
        """Get conversation history"""
        conv_key = f"{self.prefix}:conversation"
        messages = await self.redis.lrange(conv_key, 0, -1)
        return [json.loads(m) for m in messages]
    
    async def set_task_state(self, task_id: str, state: Dict[str, Any]):
        """Set current task state"""
        await self.set(f"task:{task_id}", state)
    
    async def get_task_state(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get current task state"""
        return await self.get(f"task:{task_id}")


class LongTermMemory:
    """
    MINDEX-based long-term memory.
    
    Stores:
    - Agent activity logs
    - Decision history
    - Performance metrics
    - Permanent knowledge
    """
    
    def __init__(self, agent_id: str, mindex_url: Optional[str] = None):
        self.agent_id = agent_id
        self.mindex_url = mindex_url or os.environ.get("MINDEX_URL", "http://mindex:8000")
    
    async def log_activity(
        self,
        action_type: str,
        input_summary: str,
        output_summary: Optional[str] = None,
        success: bool = True,
        duration_ms: int = 0,
        related_agents: Optional[List[str]] = None,
    ):
        """Log an activity to MINDEX"""
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(
                    f"{self.mindex_url}/api/agent_logs",
                    json={
                        "agent_id": self.agent_id,
                        "action_type": action_type,
                        "input_summary": input_summary[:500],
                        "output_summary": output_summary[:500] if output_summary else None,
                        "success": success,
                        "duration_ms": duration_ms,
                        "related_agents": related_agents or [],
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to log activity to MINDEX: {e}")
    
    async def log_decision(
        self,
        decision_type: str,
        context: Dict[str, Any],
        decision: str,
        reasoning: str,
    ):
        """Log a decision for future reference"""
        await self.log_activity(
            action_type=f"decision:{decision_type}",
            input_summary=json.dumps(context)[:500],
            output_summary=f"{decision}: {reasoning}"[:500],
            success=True,
        )
    
    async def get_activity_history(
        self,
        limit: int = 100,
        action_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get activity history from MINDEX"""
        try:
            params = {"agent_id": self.agent_id, "limit": limit}
            if action_type:
                params["action_type"] = action_type
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.mindex_url}/api/agent_logs",
                    params=params
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception as e:
            logger.warning(f"Failed to get activity history: {e}")
        
        return []
    
    async def store_knowledge(self, key: str, value: Dict[str, Any]):
        """Store permanent knowledge"""
        # This would use a dedicated knowledge table
        await self.log_activity(
            action_type="knowledge:store",
            input_summary=f"key={key}",
            output_summary=json.dumps(value)[:500],
            success=True,
        )
    
    async def query_knowledge(self, query: str) -> List[Dict[str, Any]]:
        """Query stored knowledge"""
        # This would perform a semantic search
        return []


class VectorMemory:
    """
    Qdrant-based vector memory for semantic search.
    
    Stores:
    - Document embeddings
    - Conversation embeddings
    - Knowledge graph embeddings
    """
    
    def __init__(self, agent_id: str, qdrant_url: Optional[str] = None):
        self.agent_id = agent_id
        self.qdrant_url = qdrant_url or os.environ.get("QDRANT_URL", "http://qdrant:6333")
        self.collection_name = f"agent_{agent_id.replace('-', '_')}"
    
    async def ensure_collection(self):
        """Ensure collection exists"""
        try:
            async with aiohttp.ClientSession() as session:
                # Check if collection exists
                async with session.get(
                    f"{self.qdrant_url}/collections/{self.collection_name}"
                ) as resp:
                    if resp.status == 404:
                        # Create collection
                        await session.put(
                            f"{self.qdrant_url}/collections/{self.collection_name}",
                            json={
                                "vectors": {
                                    "size": 1536,  # OpenAI embedding size
                                    "distance": "Cosine",
                                }
                            }
                        )
                        logger.info(f"Created Qdrant collection: {self.collection_name}")
        except Exception as e:
            logger.warning(f"Failed to ensure Qdrant collection: {e}")
    
    async def store_embedding(
        self,
        embedding: List[float],
        payload: Dict[str, Any],
        point_id: Optional[str] = None,
    ):
        """Store an embedding"""
        point_id = point_id or str(uuid4())
        
        try:
            async with aiohttp.ClientSession() as session:
                await session.put(
                    f"{self.qdrant_url}/collections/{self.collection_name}/points",
                    json={
                        "points": [{
                            "id": point_id,
                            "vector": embedding,
                            "payload": payload,
                        }]
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to store embedding: {e}")
    
    async def search(
        self,
        query_embedding: List[float],
        limit: int = 5,
        filter_conditions: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar embeddings"""
        try:
            body = {
                "vector": query_embedding,
                "limit": limit,
                "with_payload": True,
            }
            if filter_conditions:
                body["filter"] = filter_conditions
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.qdrant_url}/collections/{self.collection_name}/points/search",
                    json=body
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return result.get("result", [])
        except Exception as e:
            logger.warning(f"Failed to search embeddings: {e}")
        
        return []


class UnifiedMemoryManager:
    """
    Unified interface for all memory systems.
    
    Provides a single API for:
    - Short-term memory operations
    - Long-term memory storage
    - Semantic search
    """
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.short_term = ShortTermMemory(agent_id)
        self.long_term = LongTermMemory(agent_id)
        self.vector = VectorMemory(agent_id)
        self._connected = False
    
    async def connect(self):
        """Connect to all memory systems"""
        await self.short_term.connect()
        await self.vector.ensure_collection()
        self._connected = True
        logger.info(f"Memory manager connected for {self.agent_id}")
    
    async def close(self):
        """Close all connections"""
        await self.short_term.close()
        self._connected = False
    
    async def remember(
        self,
        key: str,
        value: Any,
        duration: str = "short",  # short, long, permanent
    ):
        """Store a memory"""
        if duration == "short":
            await self.short_term.set(key, value)
        elif duration == "long":
            await self.short_term.set(key, value, ttl=86400)  # 24 hours
        else:  # permanent
            await self.long_term.store_knowledge(key, {"value": value})
    
    async def recall(self, key: str) -> Optional[Any]:
        """Recall a memory"""
        # Try short-term first
        value = await self.short_term.get(key)
        if value:
            return value
        
        # Then try long-term
        history = await self.long_term.get_activity_history(
            limit=1,
            action_type=f"knowledge:store"
        )
        for item in history:
            if f"key={key}" in item.get("input_summary", ""):
                return item.get("output_summary")
        
        return None
    
    async def log(self, action: str, data: Dict[str, Any], success: bool = True):
        """Log an action"""
        await self.long_term.log_activity(
            action_type=action,
            input_summary=json.dumps(data)[:500],
            success=success,
        )
    
    async def add_to_context(self, message: Dict[str, Any]):
        """Add message to conversation context"""
        await self.short_term.add_to_conversation(message)
    
    async def get_context(self) -> List[Dict[str, Any]]:
        """Get conversation context"""
        return await self.short_term.get_conversation()
