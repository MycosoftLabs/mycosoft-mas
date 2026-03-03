"""
Webhook Security -- signature verification and rate limiting.
"""

import hashlib
import hmac
import logging
import os
import time
from typing import Optional

logger = logging.getLogger(__name__)


def verify_slack_signature(
    body: bytes,
    timestamp: str,
    signature: str,
    signing_secret: Optional[str] = None,
) -> bool:
    """Verify Slack webhook request signature (HMAC-SHA256)."""
    secret = signing_secret or os.getenv("SLACK_SIGNING_SECRET", "")
    if not secret:
        logger.warning("SLACK_SIGNING_SECRET not set")
        return False

    if abs(time.time() - float(timestamp)) > 60 * 5:
        return False

    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    computed = "v0=" + hmac.new(
        secret.encode(), sig_basestring.encode(), hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(computed, signature)


def verify_discord_signature(
    body: bytes,
    timestamp: str,
    signature: str,
    public_key: Optional[str] = None,
) -> bool:
    """Verify Discord webhook request signature (Ed25519)."""
    key_hex = public_key or os.getenv("DISCORD_PUBLIC_KEY", "")
    if not key_hex:
        logger.warning("DISCORD_PUBLIC_KEY not set")
        return False

    try:
        from nacl.signing import VerifyKey
        verify_key = VerifyKey(bytes.fromhex(key_hex))
        message = timestamp.encode() + body
        verify_key.verify(message, bytes.fromhex(signature))
        return True
    except ImportError:
        logger.warning("PyNaCl not installed, cannot verify Discord signatures")
        return False
    except Exception:
        return False


class RateLimiter:
    """Redis-backed rate limiter."""

    def __init__(self, redis_url: Optional[str] = None):
        self._redis_url = redis_url or os.getenv("REDIS_URL", "redis://192.168.0.189:6379")
        self._redis = None
        self._local_counts: dict = {}

    async def _get_redis(self):
        if self._redis is None:
            try:
                import redis.asyncio as aioredis
                self._redis = aioredis.from_url(self._redis_url, decode_responses=True)
            except Exception as exc:
                logger.debug("Redis unavailable for rate limiting: %s", exc)
        return self._redis

    async def check(
        self,
        key: str,
        max_requests: int = 100,
        window_seconds: int = 60,
    ) -> bool:
        """Return True if request is within rate limit, False if exceeded."""
        r = await self._get_redis()
        redis_key = f"rl:{key}"

        if r:
            try:
                pipe = r.pipeline()
                pipe.incr(redis_key)
                pipe.expire(redis_key, window_seconds)
                results = await pipe.execute()
                return results[0] <= max_requests
            except Exception:
                pass

        now = time.time()
        bucket = self._local_counts.setdefault(key, {"count": 0, "window_start": now})
        if now - bucket["window_start"] > window_seconds:
            bucket["count"] = 0
            bucket["window_start"] = now
        bucket["count"] += 1
        return bucket["count"] <= max_requests


def sanitize_input(text: str) -> str:
    """Strip common injection patterns from user input."""
    import re
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"javascript:", "", text, flags=re.IGNORECASE)
    dangerous_patterns = [
        r";\s*(rm|del|drop|delete|shutdown|reboot)\s",
        r"\|\s*(rm|del|drop)\s",
        r"&&\s*(rm|del|drop)\s",
    ]
    for pattern in dangerous_patterns:
        text = re.sub(pattern, " [BLOCKED] ", text, flags=re.IGNORECASE)
    return text.strip()
