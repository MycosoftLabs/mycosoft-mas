"""
WebSocket Pub/Sub System - February 6, 2026

Real-time message broadcasting with Redis.
"""

import asyncio
import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


@dataclass
class ChannelMessage:
    """Message sent through a channel."""
    channel: str
    data: Dict[str, Any]
    timestamp: str
    sender: Optional[str] = None


class WebSocketHub:
    """
    Manages WebSocket connections and pub/sub channels.
    """
    
    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}
        self.subscriptions: Dict[str, Set[str]] = defaultdict(set)  # channel -> connection_ids
        self.connection_channels: Dict[str, Set[str]] = defaultdict(set)  # conn_id -> channels
        self._redis = None
        self._listener_task: Optional[asyncio.Task] = None
    
    async def initialize(self, redis_url: str = "redis://localhost:6379") -> None:
        """Initialize Redis connection."""
        try:
            import redis.asyncio as redis
            self._redis = redis.from_url(redis_url)
            self._listener_task = asyncio.create_task(self._redis_listener())
            logger.info("WebSocketHub initialized with Redis")
        except ImportError:
            logger.warning("Redis not available, running in local mode only")
    
    async def shutdown(self) -> None:
        """Shutdown the hub."""
        if self._listener_task:
            self._listener_task.cancel()
        if self._redis:
            await self._redis.close()
    
    async def connect(self, websocket: WebSocket, connection_id: str) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.connections[connection_id] = websocket
        logger.info(f"WebSocket connected: {connection_id}")
    
    async def disconnect(self, connection_id: str) -> None:
        """Handle WebSocket disconnection."""
        # Remove from all subscriptions
        for channel in list(self.connection_channels.get(connection_id, [])):
            await self.unsubscribe(connection_id, channel)
        
        # Remove connection
        self.connections.pop(connection_id, None)
        self.connection_channels.pop(connection_id, None)
        logger.info(f"WebSocket disconnected: {connection_id}")
    
    async def subscribe(self, connection_id: str, channels: List[str]) -> None:
        """Subscribe a connection to channels."""
        for channel in channels:
            self.subscriptions[channel].add(connection_id)
            self.connection_channels[connection_id].add(channel)
        
        logger.debug(f"{connection_id} subscribed to {channels}")
    
    async def unsubscribe(self, connection_id: str, channel: str) -> None:
        """Unsubscribe from a channel."""
        self.subscriptions[channel].discard(connection_id)
        self.connection_channels[connection_id].discard(channel)
    
    async def publish(
        self,
        channel: str,
        data: Dict[str, Any],
        sender: Optional[str] = None
    ) -> int:
        """Publish message to channel."""
        message = ChannelMessage(
            channel=channel,
            data=data,
            timestamp=datetime.utcnow().isoformat(),
            sender=sender
        )
        
        # Local broadcast
        local_count = await self._broadcast_local(message)
        
        # Redis broadcast for cross-instance
        if self._redis:
            await self._redis.publish(
                f"ws:{channel}",
                json.dumps({
                    "channel": channel,
                    "data": data,
                    "timestamp": message.timestamp,
                    "sender": sender
                })
            )
        
        return local_count
    
    async def _broadcast_local(self, message: ChannelMessage) -> int:
        """Broadcast to local connections."""
        subscribers = self.subscriptions.get(message.channel, set())
        count = 0
        
        msg_json = json.dumps({
            "type": "message",
            "channel": message.channel,
            "data": message.data,
            "timestamp": message.timestamp
        })
        
        for conn_id in list(subscribers):
            ws = self.connections.get(conn_id)
            if ws:
                try:
                    await ws.send_text(msg_json)
                    count += 1
                except Exception as e:
                    logger.warning(f"Failed to send to {conn_id}: {e}")
                    await self.disconnect(conn_id)
        
        return count
    
    async def _redis_listener(self) -> None:
        """Listen for Redis pub/sub messages."""
        try:
            pubsub = self._redis.pubsub()
            await pubsub.psubscribe("ws:*")
            
            async for message in pubsub.listen():
                if message["type"] == "pmessage":
                    try:
                        data = json.loads(message["data"])
                        msg = ChannelMessage(
                            channel=data["channel"],
                            data=data["data"],
                            timestamp=data["timestamp"],
                            sender=data.get("sender")
                        )
                        await self._broadcast_local(msg)
                    except Exception as e:
                        logger.error(f"Redis message error: {e}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Redis listener error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get hub statistics."""
        return {
            "total_connections": len(self.connections),
            "channels": {
                channel: len(subscribers)
                for channel, subscribers in self.subscriptions.items()
            },
            "redis_connected": self._redis is not None
        }


class ChannelManager:
    """
    Manages channel hierarchy and permissions.
    """
    
    CHANNEL_PATTERNS = {
        "timeline": "timeline:{entity_type}:{region}",
        "aircraft": "aircraft:{region}",
        "vessels": "vessels:{region}",
        "satellites": "satellites:all",
        "earthquakes": "earthquakes:all",
        "weather": "weather:{region}",
        "wildlife": "wildlife:{region}",
    }
    
    def __init__(self, hub: WebSocketHub):
        self.hub = hub
    
    def get_channel_name(
        self,
        category: str,
        region: Optional[str] = None,
        entity_type: Optional[str] = None
    ) -> str:
        """Build channel name from pattern."""
        pattern = self.CHANNEL_PATTERNS.get(category, category)
        
        name = pattern
        if "{region}" in name:
            name = name.replace("{region}", region or "global")
        if "{entity_type}" in name:
            name = name.replace("{entity_type}", entity_type or "all")
        
        return name
    
    async def subscribe_to_timeline(
        self,
        connection_id: str,
        entity_types: List[str],
        region: Optional[str] = None
    ) -> List[str]:
        """Subscribe to timeline channels."""
        channels = []
        
        for entity_type in entity_types:
            channel = self.get_channel_name(
                "timeline",
                region=region,
                entity_type=entity_type
            )
            channels.append(channel)
        
        await self.hub.subscribe(connection_id, channels)
        return channels


# Global hub instance
_hub: Optional[WebSocketHub] = None


def get_hub() -> WebSocketHub:
    global _hub
    if _hub is None:
        _hub = WebSocketHub()
    return _hub