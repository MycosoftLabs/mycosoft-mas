"""
Memory Updates WebSocket Router - Feb 28, 2026

Streams memory layer updates via Redis pub/sub.

NO MOCK DATA - Real Redis channel stream.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from mycosoft_mas.core.routers.ws_stream_base import RedisWebSocketManager
from mycosoft_mas.realtime.redis_pubsub import Channel

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Memory Updates Stream"])

manager = RedisWebSocketManager(
    channel=Channel.MEMORY_UPDATES.value,
    message_type="memory_update",
)


@router.websocket("/ws/memory/updates")
async def memory_updates_stream(websocket: WebSocket) -> None:
    """Stream memory updates across layers."""
    await manager.connect(websocket)

    try:
        await websocket.send_json(
            {
                "type": "connected",
                "message": "Memory updates stream connected",
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
                logger.error("Memory updates WS receive error: %s", exc)
    finally:
        await manager.disconnect(websocket)
