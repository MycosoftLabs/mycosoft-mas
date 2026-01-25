"""
MAS v2 Message Broker

Handles Agent-to-Agent communication via Redis Pub/Sub and Streams.
"""

import asyncio
import json
import logging
import os
from typing import Any, Callable, Dict, List, Optional

import redis.asyncio as redis
from redis.asyncio.client import PubSub


logger = logging.getLogger("MessageBroker")


class MessageBroker:
    """
    Handles Agent-to-Agent communication.
    
    Uses Redis for:
    - Pub/Sub for real-time events and broadcasts
    - Streams for persistent task queues
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.environ.get("REDIS_URL", "redis://redis:6379/0")
        self.redis: Optional[redis.Redis] = None
        self.pubsub: Optional[PubSub] = None
        self._subscriptions: Dict[str, Callable] = {}
        self._listener_task: Optional[asyncio.Task] = None
    
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis.ping()
            self.pubsub = self.redis.pubsub()
            logger.info("Connected to Redis message broker")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def close(self):
        """Close Redis connection"""
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        
        if self.pubsub:
            await self.pubsub.close()
        
        if self.redis:
            await self.redis.close()
        
        logger.info("Disconnected from Redis message broker")
    
    async def publish(self, channel: str, message: str):
        """Publish a message to a channel"""
        if not self.redis:
            raise RuntimeError("Not connected to Redis")
        
        await self.redis.publish(channel, message)
        logger.debug(f"Published to {channel}: {message[:100]}...")
    
    async def subscribe(self, channel: str, callback: Callable[[str], Any]):
        """Subscribe to a channel with a callback"""
        if not self.pubsub:
            raise RuntimeError("Not connected to Redis")
        
        await self.pubsub.subscribe(channel)
        self._subscriptions[channel] = callback
        logger.info(f"Subscribed to channel: {channel}")
        
        # Start listener if not running
        if not self._listener_task or self._listener_task.done():
            self._listener_task = asyncio.create_task(self._listen())
    
    async def unsubscribe(self, channel: str):
        """Unsubscribe from a channel"""
        if not self.pubsub:
            return
        
        await self.pubsub.unsubscribe(channel)
        self._subscriptions.pop(channel, None)
        logger.info(f"Unsubscribed from channel: {channel}")
    
    async def _listen(self):
        """Listen for messages on subscribed channels"""
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    channel = message["channel"]
                    data = message["data"]
                    
                    callback = self._subscriptions.get(channel)
                    if callback:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(data)
                            else:
                                callback(data)
                        except Exception as e:
                            logger.error(f"Error in callback for {channel}: {e}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Listener error: {e}")
    
    # Stream operations for persistent task queues
    
    async def add_to_stream(self, stream: str, data: Dict[str, Any]) -> str:
        """Add a message to a stream"""
        if not self.redis:
            raise RuntimeError("Not connected to Redis")
        
        # Flatten dict for Redis
        flat_data = {k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) for k, v in data.items()}
        
        message_id = await self.redis.xadd(stream, flat_data)
        logger.debug(f"Added to stream {stream}: {message_id}")
        return message_id
    
    async def read_from_stream(
        self,
        stream: str,
        consumer_group: str,
        consumer_name: str,
        count: int = 1,
        block: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Read messages from a stream as a consumer"""
        if not self.redis:
            raise RuntimeError("Not connected to Redis")
        
        try:
            # Ensure consumer group exists
            try:
                await self.redis.xgroup_create(stream, consumer_group, id="0", mkstream=True)
            except redis.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    raise
            
            # Read messages
            messages = await self.redis.xreadgroup(
                consumer_group,
                consumer_name,
                {stream: ">"},
                count=count,
                block=block,
            )
            
            result = []
            for stream_name, stream_messages in messages:
                for message_id, data in stream_messages:
                    # Parse JSON values
                    parsed = {}
                    for k, v in data.items():
                        try:
                            parsed[k] = json.loads(v)
                        except json.JSONDecodeError:
                            parsed[k] = v
                    parsed["_id"] = message_id
                    result.append(parsed)
            
            return result
            
        except Exception as e:
            logger.error(f"Error reading from stream {stream}: {e}")
            return []
    
    async def ack_message(self, stream: str, consumer_group: str, message_id: str):
        """Acknowledge a message from a stream"""
        if not self.redis:
            raise RuntimeError("Not connected to Redis")
        
        await self.redis.xack(stream, consumer_group, message_id)
    
    async def get_stream_length(self, stream: str) -> int:
        """Get the length of a stream"""
        if not self.redis:
            return 0
        
        return await self.redis.xlen(stream)
    
    async def trim_stream(self, stream: str, maxlen: int):
        """Trim a stream to a maximum length"""
        if not self.redis:
            return
        
        await self.redis.xtrim(stream, maxlen=maxlen)
