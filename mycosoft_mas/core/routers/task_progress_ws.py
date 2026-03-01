"""
Task Progress WebSocket Router - Feb 28, 2026

Streams task execution progress via Redis pub/sub.

NO MOCK DATA - Real Redis channel stream.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from mycosoft_mas.core.routers.ws_stream_base import RedisWebSocketManager
from mycosoft_mas.realtime.redis_pubsub import Channel

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Task Progress Stream"])

manager = RedisWebSocketManager(
    channel=Channel.TASK_PROGRESS.value,
    message_type="task_progress",
)


@router.websocket("/ws/tasks/progress")
async def task_progress_stream(websocket: WebSocket) -> None:
    """Stream task execution progress updates."""
    await manager.connect(websocket)

    try:
        await websocket.send_json(
            {
                "type": "connected",
                "message": "Task progress stream connected",
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
                logger.error("Task progress WS receive error: %s", exc)
    finally:
        await manager.disconnect(websocket)
