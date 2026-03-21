"""
Shared WebSocket + Redis stream utilities.

No mock data: only forwards real Redis pub/sub messages.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Set

from fastapi import WebSocket

from mycosoft_mas.realtime.redis_pubsub import PubSubMessage, get_client

logger = logging.getLogger(__name__)


class RedisWebSocketManager:
    """Manage WebSocket connections and forward Redis pub/sub messages."""

    def __init__(self, *, channel: str, message_type: str, include_channel: bool = True) -> None:
        self.channel = channel
        self.message_type = message_type
        self.include_channel = include_channel
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._subscription_active = False

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
        if not self._subscription_active:
            asyncio.create_task(self._subscribe_to_redis())

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self.active_connections.discard(websocket)

    async def broadcast(self, payload: Dict[str, Any]) -> None:
        async with self._lock:
            connections = set(self.active_connections)
        disconnected: list[WebSocket] = []
        for websocket in connections:
            try:
                await websocket.send_json(payload)
            except Exception as exc:
                logger.warning("WebSocket send failed: %s", exc)
                disconnected.append(websocket)
        if disconnected:
            async with self._lock:
                for websocket in disconnected:
                    self.active_connections.discard(websocket)

    async def _subscribe_to_redis(self) -> None:
        if self._subscription_active:
            return
        self._subscription_active = True

        try:
            client = await get_client()

            async def handle_message(message: PubSubMessage) -> None:
                payload = {
                    "type": self.message_type,
                    "timestamp": message.timestamp,
                    "source": message.source,
                    "data": message.data,
                }
                if self.include_channel:
                    payload["channel"] = message.channel
                await self.broadcast(payload)

            await client.subscribe(self.channel, handle_message)
            logger.info("Subscribed to Redis channel: %s", self.channel)

            while True:
                async with self._lock:
                    if not self.active_connections:
                        break
                await asyncio.sleep(5)

            await client.unsubscribe(self.channel, handle_message)
            logger.info("Unsubscribed from Redis channel: %s", self.channel)
        except Exception as exc:
            logger.error("Redis subscription error (%s): %s", self.channel, exc)
        finally:
            self._subscription_active = False
