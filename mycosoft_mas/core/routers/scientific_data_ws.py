"""
Scientific Data WebSocket Router - Feb 28, 2026

Streams scientific experiment data via Redis pub/sub.

NO MOCK DATA - Real Redis channel stream.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from mycosoft_mas.core.routers.ws_stream_base import RedisWebSocketManager
from mycosoft_mas.realtime.redis_pubsub import Channel

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Scientific Data Stream"])

manager = RedisWebSocketManager(
    channel=Channel.EXPERIMENTS_DATA.value,
    message_type="scientific_data",
)


@router.websocket("/ws/scientific/data")
async def scientific_data_stream(websocket: WebSocket) -> None:
    """Stream scientific experiment data."""
    await manager.connect(websocket)

    try:
        await websocket.send_json(
            {
                "type": "connected",
                "message": "Scientific data stream connected",
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
                logger.error("Scientific data WS receive error: %s", exc)
    finally:
        await manager.disconnect(websocket)
