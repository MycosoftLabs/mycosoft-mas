"""
A2A Memory Integration - Agent-to-Agent Memory Sharing.
Created: February 5, 2026

Enables agents to share memories through the message broker:
- Broadcast learned facts to other agents
- Subscribe to memory updates from other agents
- Store shared knowledge in a common namespace
- Coordinate memory across the agent pool

Channels:
- mas:memory:broadcast - For broadcasting new memories
- mas:memory:request - For memory lookup requests
- mas:memory:response - For memory lookup responses
- mas:memory:sync - For memory synchronization events
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import UUID, uuid4

logger = logging.getLogger("A2AMemory")


# Memory message types
class MemoryMessageType:
    BROADCAST = "broadcast"      # Share a new memory
    LEARN = "learn"              # Agent learned something
    QUERY = "query"              # Request for memories
    RESPONSE = "response"        # Response to query
    FORGET = "forget"            # Remove shared memory
    SYNC = "sync"                # Synchronization event


@dataclass
class MemoryMessage:
    """A message for A2A memory sharing."""
    id: str
    type: str
    sender_id: str
    timestamp: str
    content: Dict[str, Any] = field(default_factory=dict)
    recipients: Optional[List[str]] = None  # None = broadcast to all
    tags: List[str] = field(default_factory=list)
    importance: float = 0.5
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "sender_id": self.sender_id,
            "timestamp": self.timestamp,
            "content": self.content,
            "recipients": self.recipients,
            "tags": self.tags,
            "importance": self.importance
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryMessage":
        return cls(
            id=data["id"],
            type=data["type"],
            sender_id=data["sender_id"],
            timestamp=data["timestamp"],
            content=data.get("content", {}),
            recipients=data.get("recipients"),
            tags=data.get("tags", []),
            importance=data.get("importance", 0.5)
        )
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> "MemoryMessage":
        return cls.from_dict(json.loads(json_str))


class A2AMemoryIntegration:
    """
    Integrates the memory system with A2A messaging.
    
    Allows agents to:
    - Share learned facts with other agents
    - Subscribe to memory updates
    - Query shared knowledge base
    - Synchronize memories across agents
    """
    
    # Redis channel names
    CHANNEL_BROADCAST = "mas:memory:broadcast"
    CHANNEL_QUERY = "mas:memory:query"
    CHANNEL_RESPONSE = "mas:memory:response"
    CHANNEL_SYNC = "mas:memory:sync"
    
    # Stream for persistent shared memories
    STREAM_SHARED = "mas:memory:shared"
    
    def __init__(self):
        self._broker = None
        self._coordinator = None
        self._initialized = False
        self._agent_id = "a2a_memory"
        self._subscribed_agents: Set[str] = set()
        self._message_handlers: Dict[str, List[Callable]] = {}
        self._pending_queries: Dict[str, asyncio.Future] = {}
    
    async def initialize(self) -> None:
        """Initialize the A2A memory integration."""
        if self._initialized:
            return
        
        try:
            # Import and initialize message broker
            from mycosoft_mas.runtime.message_broker import MessageBroker
            self._broker = MessageBroker()
            await self._broker.connect()
            
            # Import and get memory coordinator
            from mycosoft_mas.memory import get_memory_coordinator
            self._coordinator = await get_memory_coordinator()
            
            # Subscribe to channels
            await self._broker.subscribe(self.CHANNEL_BROADCAST, self._handle_broadcast)
            await self._broker.subscribe(self.CHANNEL_QUERY, self._handle_query)
            await self._broker.subscribe(self.CHANNEL_RESPONSE, self._handle_response)
            await self._broker.subscribe(self.CHANNEL_SYNC, self._handle_sync)
            
            self._initialized = True
            logger.info("A2A Memory Integration initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize A2A Memory: {e}")
            raise
    
    async def broadcast_memory(
        self,
        sender_id: str,
        content: Dict[str, Any],
        tags: Optional[List[str]] = None,
        importance: float = 0.5,
        recipients: Optional[List[str]] = None
    ) -> str:
        """
        Broadcast a memory to other agents.
        
        Args:
            sender_id: ID of the agent sharing the memory
            content: Memory content to share
            tags: Tags for categorization
            importance: Importance score
            recipients: Specific recipients (None = all agents)
            
        Returns:
            Message ID
        """
        if not self._initialized:
            await self.initialize()
        
        message = MemoryMessage(
            id=str(uuid4()),
            type=MemoryMessageType.BROADCAST,
            sender_id=sender_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            content=content,
            recipients=recipients,
            tags=tags or [],
            importance=importance
        )
        
        # Publish to broadcast channel
        await self._broker.publish(self.CHANNEL_BROADCAST, message.to_json())
        
        # Also store in shared stream for persistence
        await self._broker.add_to_stream(self.STREAM_SHARED, {
            "message_id": message.id,
            "sender_id": sender_id,
            "content": content,
            "tags": tags or [],
            "importance": importance,
            "timestamp": message.timestamp
        })
        
        logger.info(f"Agent {sender_id} broadcast memory: {message.id}")
        return message.id
    
    async def share_learning(
        self,
        agent_id: str,
        fact: Dict[str, Any],
        source: str = "experience",
        confidence: float = 0.8
    ) -> str:
        """
        Share a learned fact with other agents.
        
        Args:
            agent_id: Agent that learned the fact
            fact: The fact content (subject, predicate, object format)
            source: How the fact was learned
            confidence: Confidence in the fact
            
        Returns:
            Message ID
        """
        content = {
            "type": "learned_fact",
            "fact": fact,
            "source": source,
            "confidence": confidence,
            "learned_at": datetime.now(timezone.utc).isoformat()
        }
        
        return await self.broadcast_memory(
            sender_id=agent_id,
            content=content,
            tags=["learning", "fact", fact.get("subject", "unknown")],
            importance=confidence
        )
    
    async def query_shared_memory(
        self,
        requester_id: str,
        query: str,
        tags: Optional[List[str]] = None,
        timeout: float = 5.0
    ) -> List[Dict[str, Any]]:
        """
        Query the shared memory space.
        
        Args:
            requester_id: Agent making the query
            query: Search query
            tags: Filter by tags
            timeout: Response timeout in seconds
            
        Returns:
            List of matching memories
        """
        if not self._initialized:
            await self.initialize()
        
        query_id = str(uuid4())
        
        message = MemoryMessage(
            id=query_id,
            type=MemoryMessageType.QUERY,
            sender_id=requester_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            content={"query": query, "tags": tags or []},
            tags=tags or []
        )
        
        # Create future for response
        response_future: asyncio.Future = asyncio.Future()
        self._pending_queries[query_id] = response_future
        
        try:
            # Send query
            await self._broker.publish(self.CHANNEL_QUERY, message.to_json())
            
            # Wait for response
            result = await asyncio.wait_for(response_future, timeout=timeout)
            return result
            
        except asyncio.TimeoutError:
            logger.warning(f"Query {query_id} timed out")
            return []
        finally:
            self._pending_queries.pop(query_id, None)
    
    async def _handle_broadcast(self, data: str) -> None:
        """Handle incoming broadcast messages."""
        try:
            message = MemoryMessage.from_json(data)
            
            # Skip if we sent this message
            if message.sender_id == self._agent_id:
                return
            
            # Check if we're in recipients list
            if message.recipients and self._agent_id not in message.recipients:
                return
            
            # Store in coordinator's shared namespace
            await self._coordinator.agent_remember(
                agent_id="shared",
                content={
                    "source_agent": message.sender_id,
                    "data": message.content,
                    "shared_at": message.timestamp
                },
                layer="semantic",
                importance=message.importance,
                tags=message.tags + ["shared", f"from:{message.sender_id}"]
            )
            
            # Notify handlers
            await self._notify_handlers(MemoryMessageType.BROADCAST, message)
            
            logger.debug(f"Stored shared memory from {message.sender_id}")
            
        except Exception as e:
            logger.error(f"Error handling broadcast: {e}")
    
    async def _handle_query(self, data: str) -> None:
        """Handle incoming memory queries."""
        try:
            message = MemoryMessage.from_json(data)
            
            # Search shared memories
            query = message.content.get("query", "")
            tags = message.content.get("tags", [])
            
            results = await self._coordinator.agent_recall(
                agent_id="shared",
                query=query,
                tags=tags + ["shared"],
                layer="semantic",
                limit=20
            )
            
            # Send response
            response = MemoryMessage(
                id=str(uuid4()),
                type=MemoryMessageType.RESPONSE,
                sender_id=self._agent_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                content={
                    "query_id": message.id,
                    "results": results
                }
            )
            
            await self._broker.publish(self.CHANNEL_RESPONSE, response.to_json())
            
        except Exception as e:
            logger.error(f"Error handling query: {e}")
    
    async def _handle_response(self, data: str) -> None:
        """Handle incoming query responses."""
        try:
            message = MemoryMessage.from_json(data)
            
            query_id = message.content.get("query_id")
            if query_id and query_id in self._pending_queries:
                future = self._pending_queries[query_id]
                if not future.done():
                    future.set_result(message.content.get("results", []))
            
        except Exception as e:
            logger.error(f"Error handling response: {e}")
    
    async def _handle_sync(self, data: str) -> None:
        """Handle memory synchronization events."""
        try:
            message = MemoryMessage.from_json(data)
            
            # Handle sync events (e.g., memory consolidation, cleanup)
            sync_type = message.content.get("sync_type")
            
            if sync_type == "consolidation":
                logger.info("Received memory consolidation event")
                # Trigger local consolidation if needed
            
            elif sync_type == "cleanup":
                logger.info("Received memory cleanup event")
                # Perform cleanup of stale shared memories
            
            await self._notify_handlers(MemoryMessageType.SYNC, message)
            
        except Exception as e:
            logger.error(f"Error handling sync: {e}")
    
    def register_handler(
        self,
        message_type: str,
        handler: Callable[[MemoryMessage], Any]
    ) -> None:
        """Register a handler for a specific message type."""
        if message_type not in self._message_handlers:
            self._message_handlers[message_type] = []
        self._message_handlers[message_type].append(handler)
    
    async def _notify_handlers(self, message_type: str, message: MemoryMessage) -> None:
        """Notify all handlers for a message type."""
        handlers = self._message_handlers.get(message_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception as e:
                logger.error(f"Handler error: {e}")
    
    async def get_shared_memories(
        self,
        limit: int = 50,
        since_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get shared memories from the stream.
        
        Args:
            limit: Maximum memories to retrieve
            since_id: Only get memories after this ID
            
        Returns:
            List of shared memory entries
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Read from stream
            messages = await self._broker.redis.xrange(
                self.STREAM_SHARED,
                min=since_id or "-",
                max="+",
                count=limit
            )
            
            results = []
            for msg_id, data in messages:
                entry = {"_id": msg_id}
                for k, v in data.items():
                    try:
                        entry[k] = json.loads(v)
                    except (json.JSONDecodeError, TypeError):
                        entry[k] = v
                results.append(entry)
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting shared memories: {e}")
            return []
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get A2A memory statistics."""
        stats = {
            "initialized": self._initialized,
            "subscribed_agents": len(self._subscribed_agents),
            "pending_queries": len(self._pending_queries),
            "handlers_registered": sum(len(h) for h in self._message_handlers.values())
        }
        
        if self._initialized and self._broker:
            try:
                stream_len = await self._broker.get_stream_length(self.STREAM_SHARED)
                stats["shared_memories_count"] = stream_len
            except:
                pass
        
        return stats
    
    async def shutdown(self) -> None:
        """Shutdown the A2A memory integration."""
        if self._broker:
            await self._broker.unsubscribe(self.CHANNEL_BROADCAST)
            await self._broker.unsubscribe(self.CHANNEL_QUERY)
            await self._broker.unsubscribe(self.CHANNEL_RESPONSE)
            await self._broker.unsubscribe(self.CHANNEL_SYNC)
            await self._broker.close()
        
        self._initialized = False
        logger.info("A2A Memory Integration shutdown")


# Singleton instance
_a2a_memory: Optional[A2AMemoryIntegration] = None
_a2a_lock = asyncio.Lock()


async def get_a2a_memory() -> A2AMemoryIntegration:
    """Get or create the singleton A2A memory integration."""
    global _a2a_memory
    
    if _a2a_memory is None:
        async with _a2a_lock:
            if _a2a_memory is None:
                _a2a_memory = A2AMemoryIntegration()
                await _a2a_memory.initialize()
    
    return _a2a_memory
