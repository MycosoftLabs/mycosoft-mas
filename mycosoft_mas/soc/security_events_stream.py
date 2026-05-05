"""
Publish SOC incident lifecycle events to Redis Streams (`security:events`).

Downstream consumers (WS broadcaster, SIEM bridges) can XREAD without polling Postgres.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

STREAM_KEY = os.getenv("SOC_SECURITY_EVENTS_STREAM", "security:events")
_redis_client: Any = None


async def _client():
    global _redis_client
    url = (os.getenv("REDIS_URL") or "").strip()
    if not url:
        return None
    if _redis_client is None:
        import redis.asyncio as redis_async

        client = redis_async.Redis.from_url(url, decode_responses=True)
        try:
            await client.ping()
        except Exception as exc:  # noqa: BLE001
            logger.warning("SOC Redis stream unavailable: %s", exc)
            try:
                await client.aclose()
            except Exception:
                pass
            return None
        _redis_client = client
    return _redis_client


async def publish_security_stream_event(
    event_type: str,
    payload: Dict[str, Any],
) -> Optional[str]:
    """XADD a single-field JSON payload. Returns Redis message id or None."""
    r = await _client()
    if r is None:
        return None
    body = {
        "event_type": event_type,
        "payload": payload,
    }
    try:
        msg_id = await r.xadd(STREAM_KEY, {"data": json.dumps(body, default=str)})
        return str(msg_id)
    except Exception as exc:  # noqa: BLE001
        logger.debug("security stream xadd failed: %s", exc)
        return None


async def publish_incident_created(incident: Dict[str, Any]) -> None:
    await publish_security_stream_event(
        "incident.created",
        {"incident": incident},
    )


async def publish_incident_updated(incident: Dict[str, Any], patch: Dict[str, Any]) -> None:
    await publish_security_stream_event(
        "incident.updated",
        {"incident": incident, "patch": patch},
    )
