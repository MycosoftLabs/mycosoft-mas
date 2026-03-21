"""
Session Manager -- persistence and context pruning for Gateway sessions.

Uses Redis for session state with TTL-based expiry.
"""

import json
import logging
import os
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://192.168.0.189:6379")
SESSION_TTL_SECONDS = int(os.getenv("GATEWAY_SESSION_TTL", "1800"))  # 30 min


class SessionManager:
    """Manages gateway sessions with Redis-backed persistence."""

    def __init__(self, redis_url: str = REDIS_URL):
        self._redis_url = redis_url
        self._redis = None
        self._local_cache: Dict[str, Dict[str, Any]] = {}

    async def _get_redis(self):
        if self._redis is None:
            try:
                import redis.asyncio as aioredis

                self._redis = aioredis.from_url(
                    self._redis_url,
                    decode_responses=True,
                )
            except Exception as exc:
                logger.warning(
                    "Redis unavailable (%s), using local cache: %s", self._redis_url, exc
                )
        return self._redis

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        r = await self._get_redis()
        if r:
            try:
                raw = await r.get(f"gw:session:{session_id}")
                if raw:
                    return json.loads(raw)
            except Exception as exc:
                logger.debug("Redis get failed: %s", exc)
        return self._local_cache.get(session_id)

    async def save_session(self, session_id: str, state: Dict[str, Any]):
        state["_updated_at"] = time.time()
        r = await self._get_redis()
        if r:
            try:
                await r.setex(
                    f"gw:session:{session_id}",
                    SESSION_TTL_SECONDS,
                    json.dumps(state, default=str),
                )
                return
            except Exception as exc:
                logger.debug("Redis setex failed: %s", exc)
        self._local_cache[session_id] = state

    async def delete_session(self, session_id: str):
        r = await self._get_redis()
        if r:
            try:
                await r.delete(f"gw:session:{session_id}")
            except Exception:
                pass
        self._local_cache.pop(session_id, None)

    async def prune_context(self, output: str, max_lines: int = 200) -> str:
        """Truncate large terminal/tool outputs, keeping head + tail + summary."""
        lines = output.splitlines()
        if len(lines) <= max_lines:
            return output
        head = lines[:20]
        tail = lines[-50:]
        omitted = len(lines) - 70
        summary_line = f"\n... [{omitted} lines omitted] ...\n"
        return "\n".join(head) + summary_line + "\n".join(tail)

    async def cleanup_expired(self):
        """Remove locally-cached sessions older than TTL."""
        now = time.time()
        expired = [
            sid
            for sid, state in self._local_cache.items()
            if now - state.get("_updated_at", 0) > SESSION_TTL_SECONDS
        ]
        for sid in expired:
            del self._local_cache[sid]
        if expired:
            logger.info("Cleaned up %d expired local sessions", len(expired))
