"""
Redis event publisher for Deep Agent lifecycle updates.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class DeepAgentRedisEvents:
    def __init__(self) -> None:
        self._redis: Redis | None = None
        self._channel = os.getenv("MYCA_DEEP_AGENTS_REDIS_CHANNEL", "mas.deep_agents.events")
        self._url = os.getenv("REDIS_URL", "redis://localhost:6379")

    async def initialize(self) -> None:
        if self._redis is not None:
            return
        self._redis = Redis.from_url(self._url, decode_responses=True)
        await self._redis.ping()

    async def shutdown(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
        self._redis = None

    async def publish(self, event_type: str, payload: Dict[str, Any]) -> None:
        if self._redis is None:
            return
        message = {
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        try:
            await self._redis.publish(self._channel, json.dumps(message))
        except Exception as exc:  # noqa: BLE001
            logger.debug("Deep agent redis publish failed: %s", exc)
