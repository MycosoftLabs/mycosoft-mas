"""
Agent Event Bus - February 9, 2026

WebSocket server for agent-to-agent real-time messaging.
Bridges to Redis pub/sub, extends WebSocketHub for connection management.
Feature flag: MYCA_AGENT_BUS_ENABLED
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .event_schema import AgentEvent
from .agent_session import AgentSessionManager
from .pubsub import get_hub
from .redis_pubsub import get_client, Channel

logger = logging.getLogger(__name__)

AGENT_BUS_ENABLED = os.getenv("MYCA_AGENT_BUS_ENABLED", "false").lower() == "true"


def create_agent_bus_router() -> APIRouter:
    """Create the Agent Bus WebSocket router."""

    router = APIRouter(prefix="/ws", tags=["agent-bus"])
    hub = get_hub()
    session_manager = AgentSessionManager()
    _redis_client = None

    async def get_redis():
        nonlocal _redis_client
        if _redis_client is None:
            try:
                _redis_client = await get_client()
            except Exception as e:
                logger.warning(f"Redis client unavailable for Agent Bus: {e}")
        return _redis_client

    async def on_stale_connection(connection_id: str) -> None:
        """Handle stale session - disconnect from hub."""
        session = session_manager.unregister(connection_id)
        if session:
            await hub.disconnect(connection_id)

    @router.websocket("/agent-bus")
    async def agent_bus_websocket(websocket: WebSocket) -> None:
        if not AGENT_BUS_ENABLED:
            await websocket.close(code=4003, reason="Agent Bus disabled")
            return

        connection_id = str(uuid4())
        agent_id: Optional[str] = None

        try:
            await hub.connect(websocket, connection_id)

            # Expect initial message with agent_id
            raw = await websocket.receive_text()
            init = json.loads(raw)
            agent_id = init.get("agent_id") or init.get("from_agent")
            if not agent_id:
                await websocket.send_json({
                    "type": "error",
                    "payload": {"message": "agent_id or from_agent required in first message"},
                })
                await websocket.close(code=4000, reason="Missing agent_id")
                return

            session_manager.register(connection_id, agent_id, metadata=init.get("metadata", {}))
            channels = init.get("channels", ["agents:status", "agents:tasks", "agents:tool_calls"])
            await hub.subscribe(connection_id, channels)

            await websocket.send_json({
                "type": "connected",
                "payload": {"connection_id": connection_id, "agent_id": agent_id},
            })

            # Start receiving loop
            while True:
                try:
                    raw = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
                except asyncio.TimeoutError:
                    # Send heartbeat request
                    session_manager.heartbeat(connection_id)
                    await websocket.send_json({"type": "heartbeat", "payload": {}})
                    continue

                data = json.loads(raw)
                msg_type = data.get("type", "event")

                if msg_type == "heartbeat":
                    session_manager.heartbeat(connection_id)
                    continue

                if msg_type == "event":
                    try:
                        event = AgentEvent(
                            type=data.get("type", "status"),
                            from_agent=agent_id,
                            to_agent=data.get("to_agent", "broadcast"),
                            payload=data.get("payload", {}),
                        )
                    except Exception as e:
                        await websocket.send_json({
                            "type": "error",
                            "payload": {"message": str(e)},
                        })
                        continue

                    # Route to Redis
                    redis_client = await get_redis()
                    if redis_client and redis_client.is_connected():
                        channel = Channel.AGENTS_STATUS.value
                        if event.type == "task":
                            channel = Channel.AGENTS_TASKS.value
                        elif event.type == "tool_call":
                            channel = Channel.AGENTS_TOOL_CALLS.value
                        await redis_client.publish(
                            channel,
                            event.model_dump(mode="json"),
                            source=agent_id,
                        )

        except WebSocketDisconnect:
            logger.info(f"Agent Bus WebSocket disconnected: {connection_id}")
        except Exception as e:
            logger.error(f"Agent Bus error: {e}", exc_info=True)
        finally:
            session_manager.unregister(connection_id)
            await hub.disconnect(connection_id)

    return router


def get_agent_bus_router() -> Optional[APIRouter]:
    """Return Agent Bus router if enabled, else None."""
    if not AGENT_BUS_ENABLED:
        return None
    return create_agent_bus_router()
