"""
Agent Status WebSocket Router - Feb 28, 2026

Streams live agent state via Redis pub/sub.

NO MOCK DATA - Real Redis channel stream.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from mycosoft_mas.core.routers.ws_stream_base import RedisWebSocketManager
from mycosoft_mas.realtime.redis_pubsub import Channel

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Agent Status Stream"])

manager = RedisWebSocketManager(
    channel=Channel.AGENTS_STATUS.value,
    message_type="agent_status",
)


@router.websocket("/ws/agents/status")
async def agent_status_stream(websocket: WebSocket) -> None:
    """Stream live agent status updates."""
    await manager.connect(websocket)

    try:
        await websocket.send_json(
            {
                "type": "connected",
                "message": "Agent status stream connected",
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
                logger.error("Agent status WS receive error: %s", exc)
    finally:
        await manager.disconnect(websocket)
