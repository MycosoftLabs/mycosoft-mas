"""
System Health WebSocket Router - Feb 28, 2026

Streams infrastructure/system health metrics via Redis pub/sub.

NO MOCK DATA - Real Redis channel stream.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from mycosoft_mas.core.routers.ws_stream_base import RedisWebSocketManager
from mycosoft_mas.realtime.redis_pubsub import Channel

logger = logging.getLogger(__name__)

router = APIRouter(tags=["System Health Stream"])

manager = RedisWebSocketManager(
    channel=Channel.SYSTEM_HEALTH.value,
    message_type="system_health",
)


@router.websocket("/ws/system/health")
async def system_health_stream(websocket: WebSocket) -> None:
    """Stream system health metrics and alerts."""
    await manager.connect(websocket)

    try:
        await websocket.send_json(
            {
                "type": "connected",
                "message": "System health stream connected",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        while True:
            try:
                data = await websocket.receive_json()
                if data.get("type") == "ping":
                    await websocket.send_json(
                        {
                            "type": "pong",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    )
            except WebSocketDisconnect:
                break
            except Exception as exc:
                logger.error("System health WS receive error: %s", exc)
    finally:
        await manager.disconnect(websocket)
