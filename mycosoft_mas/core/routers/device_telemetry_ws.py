"""
Device Telemetry WebSocket Router - Feb 28, 2026

Streams all device telemetry via Redis pub/sub.

NO MOCK DATA - Real Redis channel stream.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from mycosoft_mas.core.routers.ws_stream_base import RedisWebSocketManager
from mycosoft_mas.realtime.redis_pubsub import Channel

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Device Telemetry Stream"])

manager = RedisWebSocketManager(
    channel=Channel.DEVICES_TELEMETRY.value,
    message_type="device_telemetry",
)


@router.websocket("/ws/devices/telemetry")
async def device_telemetry_stream(websocket: WebSocket) -> None:
    """Stream all device telemetry updates."""
    await manager.connect(websocket)

    try:
        await websocket.send_json(
            {
                "type": "connected",
                "message": "Device telemetry stream connected",
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
                logger.error("Device telemetry WS receive error: %s", exc)
    finally:
        await manager.disconnect(websocket)
