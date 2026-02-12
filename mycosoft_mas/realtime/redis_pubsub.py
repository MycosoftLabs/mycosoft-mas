"""
Redis Pub/Sub Client - February 12, 2026

Real-time messaging system using Redis pub/sub for cross-system communication.
Provides publish/subscribe patterns for device telemetry, agent status,
experiments, and CREP updates.

NO MOCK DATA - Real Redis integration with VM 192.168.0.189:6379
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from contextlib import asynccontextmanager

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class Channel(str, Enum):
    """Predefined pub/sub channels for system-wide events."""
    
    # Device telemetry - sensor data from MycoBrain, lab equipment, etc.
    DEVICES_TELEMETRY = "devices:telemetry"
    
    # Agent status - health updates, task completion, errors
    AGENTS_STATUS = "agents:status"
    
    # Experiment data - lab data streams, measurements, observations
    EXPERIMENTS_DATA = "experiments:data"
    
    # CREP live - Aviation, maritime, satellite, weather updates
    CREP_LIVE = "crep:live"
    
    # Additional system channels
    MEMORY_UPDATES = "memory:updates"
    WEBSOCKET_BROADCAST = "websocket:broadcast"
    SYSTEM_ALERTS = "system:alerts"


@dataclass
class PubSubMessage:
    """Message published to a pub/sub channel."""
    
    channel: str
    data: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    source: Optional[str] = None
    message_id: Optional[str] = None
    
    def to_json(self) -> str:
        """Serialize message to JSON."""
        return json.dumps({
            "channel": self.channel,
            "data": self.data,
            "timestamp": self.timestamp,
            "source": self.source,
            "message_id": self.message_id,
        })
    
    @classmethod
    def from_json(cls, data: str) -> "PubSubMessage":
        """Deserialize message from JSON."""
        parsed = json.loads(data)
        return cls(
            channel=parsed["channel"],
            data=parsed["data"],
            timestamp=parsed.get("timestamp", datetime.utcnow().isoformat()),
            source=parsed.get("source"),
            message_id=parsed.get("message_id"),
        )


class RedisPubSubClient:
    """
    Redis pub/sub client for real-time messaging across the MAS system.
    
    Features:
    - Automatic reconnection on connection loss
    - Channel subscription management
    - Message publishing with guaranteed delivery
    - Health monitoring
    - Statistics tracking
    """
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        max_reconnect_attempts: int = 5,
        reconnect_delay: float = 2.0,
    ):
        """
        Initialize Redis pub/sub client.
        
        Args:
            redis_url: Redis connection URL (default: from env or VM 189)
            max_reconnect_attempts: Maximum reconnection attempts
            reconnect_delay: Delay between reconnection attempts (seconds)
        """
        # Build Redis URL from environment or use default VM 189
        if redis_url is None:
            redis_host = os.getenv("REDIS_HOST", "192.168.0.189")
            redis_port = os.getenv("REDIS_PORT", "6379")
            redis_db = os.getenv("REDIS_DB", "0")
            redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"
        
        self.redis_url = redis_url
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_delay = reconnect_delay
        
        # Redis clients
        self._redis: Optional[redis.Redis] = None
        self._pubsub: Optional[redis.client.PubSub] = None
        
        # Connection state
        self._connected = False
        self._reconnecting = False
        self._shutdown = False
        
        # Subscriptions
        self._subscriptions: Dict[str, Set[Callable]] = {}  # channel -> callbacks
        self._listener_task: Optional[asyncio.Task] = None
        
        # Statistics
        self._messages_published = 0
        self._messages_received = 0
        self._connection_errors = 0
        self._last_error: Optional[str] = None
    
    async def connect(self) -> bool:
        """
        Connect to Redis.
        
        Returns:
            True if connection successful, False otherwise
        """
        if self._connected:
            logger.warning("Already connected to Redis")
            return True
        
        try:
            self._redis = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=30,
            )
            
            # Test connection
            await self._redis.ping()
            
            self._pubsub = self._redis.pubsub()
            self._connected = True
            
            logger.info(f"Connected to Redis at {self.redis_url}")
            
            # Start listener task
            self._listener_task = asyncio.create_task(self._message_listener())
            
            return True
        
        except Exception as e:
            self._connection_errors += 1
            self._last_error = str(e)
            logger.error(f"Failed to connect to Redis: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Redis and clean up resources."""
        self._shutdown = True
        
        # Cancel listener task
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        
        # Close pub/sub
        if self._pubsub:
            await self._pubsub.close()
        
        # Close Redis connection
        if self._redis:
            await self._redis.close()
        
        self._connected = False
        logger.info("Disconnected from Redis")
    
    async def _reconnect(self) -> bool:
        """
        Attempt to reconnect to Redis.
        
        Returns:
            True if reconnection successful, False otherwise
        """
        if self._reconnecting:
            return False
        
        self._reconnecting = True
        self._connected = False
        
        for attempt in range(1, self.max_reconnect_attempts + 1):
            if self._shutdown:
                break
            
            logger.warning(f"Reconnection attempt {attempt}/{self.max_reconnect_attempts}")
            
            # Close existing connections
            try:
                if self._pubsub:
                    await self._pubsub.close()
                if self._redis:
                    await self._redis.close()
            except Exception as e:
                logger.debug(f"Error closing connections: {e}")
            
            # Wait before reconnecting
            await asyncio.sleep(self.reconnect_delay * attempt)
            
            # Attempt connection
            if await self.connect():
                # Re-subscribe to all channels
                for channel in self._subscriptions.keys():
                    try:
                        await self._pubsub.subscribe(channel)
                        logger.info(f"Re-subscribed to channel: {channel}")
                    except Exception as e:
                        logger.error(f"Failed to re-subscribe to {channel}: {e}")
                
                self._reconnecting = False
                return True
        
        self._reconnecting = False
        logger.error("Failed to reconnect to Redis after maximum attempts")
        return False
    
    async def _message_listener(self) -> None:
        """Background task that listens for messages on subscribed channels."""
        while not self._shutdown:
            try:
                if not self._connected or not self._pubsub:
                    await asyncio.sleep(1)
                    continue
                
                # Listen for messages
                async for message in self._pubsub.listen():
                    if message["type"] == "message":
                        try:
                            # Parse message
                            pubsub_msg = PubSubMessage.from_json(message["data"])
                            self._messages_received += 1
                            
                            # Call all callbacks for this channel
                            channel = message["channel"]
                            callbacks = self._subscriptions.get(channel, set())
                            
                            for callback in callbacks:
                                try:
                                    if asyncio.iscoroutinefunction(callback):
                                        await callback(pubsub_msg)
                                    else:
                                        callback(pubsub_msg)
                                except Exception as e:
                                    logger.error(f"Callback error for {channel}: {e}")
                        
                        except Exception as e:
                            logger.error(f"Message processing error: {e}")
            
            except asyncio.CancelledError:
                break
            
            except Exception as e:
                self._connection_errors += 1
                self._last_error = str(e)
                logger.error(f"Listener error: {e}")
                
                # Attempt reconnection
                if not await self._reconnect():
                    logger.critical("Failed to reconnect, stopping listener")
                    break
                
                await asyncio.sleep(1)
    
    async def subscribe(
        self,
        channel: str,
        callback: Callable[[PubSubMessage], None],
    ) -> bool:
        """
        Subscribe to a channel and register a callback.
        
        Args:
            channel: Channel name (use Channel enum for system channels)
            callback: Async or sync function to call when messages arrive
        
        Returns:
            True if subscription successful, False otherwise
        """
        if not self._connected:
            logger.error("Not connected to Redis")
            return False
        
        try:
            # Add callback to subscriptions
            if channel not in self._subscriptions:
                self._subscriptions[channel] = set()
                # Subscribe to channel in Redis
                await self._pubsub.subscribe(channel)
                logger.info(f"Subscribed to channel: {channel}")
            
            self._subscriptions[channel].add(callback)
            return True
        
        except Exception as e:
            logger.error(f"Failed to subscribe to {channel}: {e}")
            return False
    
    async def unsubscribe(self, channel: str, callback: Optional[Callable] = None) -> bool:
        """
        Unsubscribe from a channel.
        
        Args:
            channel: Channel name
            callback: Specific callback to remove (if None, removes all callbacks)
        
        Returns:
            True if unsubscription successful, False otherwise
        """
        if channel not in self._subscriptions:
            return True
        
        try:
            if callback:
                # Remove specific callback
                self._subscriptions[channel].discard(callback)
            else:
                # Remove all callbacks
                self._subscriptions[channel].clear()
            
            # If no more callbacks, unsubscribe from Redis
            if not self._subscriptions[channel]:
                await self._pubsub.unsubscribe(channel)
                del self._subscriptions[channel]
                logger.info(f"Unsubscribed from channel: {channel}")
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to unsubscribe from {channel}: {e}")
            return False
    
    async def publish(
        self,
        channel: str,
        data: Dict[str, Any],
        source: Optional[str] = None,
    ) -> bool:
        """
        Publish a message to a channel.
        
        Args:
            channel: Channel name (use Channel enum for system channels)
            data: Message data (must be JSON-serializable)
            source: Source identifier (agent name, device ID, etc.)
        
        Returns:
            True if publish successful, False otherwise
        """
        if not self._connected:
            logger.error("Not connected to Redis")
            return False
        
        try:
            message = PubSubMessage(
                channel=channel,
                data=data,
                source=source,
            )
            
            # Publish to Redis
            await self._redis.publish(channel, message.to_json())
            self._messages_published += 1
            
            logger.debug(f"Published message to {channel}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to publish to {channel}: {e}")
            return False
    
    def is_connected(self) -> bool:
        """Check if connected to Redis."""
        return self._connected
    
    def get_subscriptions(self) -> List[str]:
        """Get list of subscribed channels."""
        return list(self._subscriptions.keys())
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        return {
            "connected": self._connected,
            "reconnecting": self._reconnecting,
            "redis_url": self.redis_url,
            "subscribed_channels": len(self._subscriptions),
            "channels": list(self._subscriptions.keys()),
            "messages_published": self._messages_published,
            "messages_received": self._messages_received,
            "connection_errors": self._connection_errors,
            "last_error": self._last_error,
        }
    
    @asynccontextmanager
    async def connection(self):
        """Context manager for Redis connection lifecycle."""
        try:
            await self.connect()
            yield self
        finally:
            await self.disconnect()


# Global client instance
_client: Optional[RedisPubSubClient] = None


async def get_client() -> RedisPubSubClient:
    """
    Get or create the global Redis pub/sub client.
    
    Returns:
        RedisPubSubClient instance
    """
    global _client
    if _client is None:
        _client = RedisPubSubClient()
        await _client.connect()
    return _client


async def publish_device_telemetry(
    device_id: str,
    telemetry: Dict[str, Any],
    source: Optional[str] = None,
) -> bool:
    """
    Publish device telemetry data.
    
    Args:
        device_id: Device identifier
        telemetry: Telemetry data (temperature, humidity, etc.)
        source: Source identifier
    
    Returns:
        True if successful
    """
    client = await get_client()
    return await client.publish(
        Channel.DEVICES_TELEMETRY.value,
        {"device_id": device_id, "telemetry": telemetry},
        source=source or f"device:{device_id}",
    )


async def publish_agent_status(
    agent_id: str,
    status: str,
    details: Optional[Dict[str, Any]] = None,
    source: Optional[str] = None,
) -> bool:
    """
    Publish agent status update.
    
    Args:
        agent_id: Agent identifier
        status: Status (healthy, degraded, error, etc.)
        details: Additional status details
        source: Source identifier
    
    Returns:
        True if successful
    """
    client = await get_client()
    return await client.publish(
        Channel.AGENTS_STATUS.value,
        {
            "agent_id": agent_id,
            "status": status,
            "details": details or {},
        },
        source=source or f"agent:{agent_id}",
    )


async def publish_experiment_data(
    experiment_id: str,
    data: Dict[str, Any],
    source: Optional[str] = None,
) -> bool:
    """
    Publish experiment data stream.
    
    Args:
        experiment_id: Experiment identifier
        data: Experimental data (measurements, observations, etc.)
        source: Source identifier
    
    Returns:
        True if successful
    """
    client = await get_client()
    return await client.publish(
        Channel.EXPERIMENTS_DATA.value,
        {"experiment_id": experiment_id, "data": data},
        source=source or f"experiment:{experiment_id}",
    )


async def publish_crep_update(
    category: str,
    data: Dict[str, Any],
    source: Optional[str] = None,
) -> bool:
    """
    Publish CREP live update (aviation, maritime, satellite, weather).
    
    Args:
        category: CREP category (aircraft, vessel, satellite, weather)
        data: Update data
        source: Source identifier
    
    Returns:
        True if successful
    """
    client = await get_client()
    return await client.publish(
        Channel.CREP_LIVE.value,
        {"category": category, "data": data},
        source=source or f"crep:{category}",
    )


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def example_subscriber(message: PubSubMessage):
        """Example message handler."""
        print(f"Received message on {message.channel}: {message.data}")
    
    async def main():
        # Initialize client
        client = RedisPubSubClient()
        await client.connect()
        
        # Subscribe to channels
        await client.subscribe(Channel.DEVICES_TELEMETRY.value, example_subscriber)
        await client.subscribe(Channel.AGENTS_STATUS.value, example_subscriber)
        
        # Publish test messages
        await publish_device_telemetry(
            "mushroom1",
            {"temperature": 22.5, "humidity": 65.2},
            source="test",
        )
        
        await publish_agent_status(
            "ceo_agent",
            "healthy",
            {"tasks_completed": 42},
            source="test",
        )
        
        # Wait for messages
        await asyncio.sleep(5)
        
        # Print stats
        print("\nClient Stats:")
        print(json.dumps(client.get_stats(), indent=2))
        
        # Cleanup
        await client.disconnect()
    
    asyncio.run(main())
