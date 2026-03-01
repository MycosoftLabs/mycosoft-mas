"""
Earth2 Predictions WebSocket Router - Feb 28, 2026

Streams Earth2 weather/climate prediction updates via Redis pub/sub.

NO MOCK DATA - Real Redis channel stream.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from mycosoft_mas.core.routers.ws_stream_base import RedisWebSocketManager
from mycosoft_mas.realtime.redis_pubsub import Channel

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Earth2 Predictions Stream"])

manager = RedisWebSocketManager(
    channel=Channel.EARTH2_PREDICTIONS.value,
    message_type="earth2_prediction",
)


@router.websocket("/ws/earth2/predictions")
async def earth2_predictions_stream(websocket: WebSocket) -> None:
    """Stream Earth2 prediction updates."""
    await manager.connect(websocket)

    try:
        await websocket.send_json(
            {
                "type": "connected",
                "message": "Earth2 predictions stream connected",
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
                logger.error("Earth2 predictions WS receive error: %s", exc)
    finally:
        await manager.disconnect(websocket)
