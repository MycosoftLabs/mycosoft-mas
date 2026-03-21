"""
Agent WebSocket Mixin - February 9, 2026

Optional mixin for BaseAgent to connect to the Agent Event Bus.
Agents work without WS if bus unavailable. Uses env MYCA_AGENT_WS_ENABLED.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections import deque
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MYCA_AGENT_WS_ENABLED = os.getenv("MYCA_AGENT_WS_ENABLED", "false").lower() == "true"
WS_BUS_URL = os.getenv("MYCA_AGENT_BUS_URL", "ws://192.168.0.188:8001/ws/agent-bus")

# Reconnect: 1s, 2s, 4s, 8s, 16s, max 30s
RECONNECT_DELAYS = [1.0, 2.0, 4.0, 8.0, 16.0, 30.0]
MAX_BUFFER_SIZE = 100


class AgentWebSocketMixin:
    """
    Mixin for agents to connect to the Agent Event Bus via WebSocket.
    Optional: agents work without WS if bus unavailable.
    """

    def __init_ws_mixin__(self) -> None:
        """Initialize WebSocket mixin state. Call from __init__ if using mixin."""
        self._ws_enabled: bool = False
        self._ws_connection: Optional[Any] = None
        self._ws_receive_task: Optional[asyncio.Task] = None
        self._ws_outgoing_buffer: deque = deque(maxlen=MAX_BUFFER_SIZE)
        self._ws_incoming_buffer: deque = deque(maxlen=MAX_BUFFER_SIZE)
        self._ws_reconnect_attempt: int = 0
        self._ws_connected: bool = False

    async def connect_to_bus(
        self, agent_id: str, metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Connect to the Agent Event Bus WebSocket.
        Uses exponential backoff on reconnect.

        Returns:
            True if connected, False if unavailable or disabled.
        """
        if not MYCA_AGENT_WS_ENABLED:
            return False

        ws_agent_id = getattr(self, "agent_id", agent_id)
        try:
            import websockets  # type: ignore

            self._ws_connection = await asyncio.wait_for(
                websockets.connect(WS_BUS_URL),
                timeout=10.0,
            )
            await self._ws_connection.send(
                json.dumps(
                    {
                        "agent_id": ws_agent_id,
                        "metadata": metadata or {},
                        "channels": ["agents:status", "agents:tasks", "agents:tool_calls"],
                    }
                )
            )
            resp_raw = await self._ws_connection.recv()
            resp = json.loads(resp_raw)
            if resp.get("type") == "connected":
                self._ws_connected = True
                self._ws_reconnect_attempt = 0
                self._ws_enabled = True
                self._ws_receive_task = asyncio.create_task(self._receive_events_loop())
                logger.info(f"Agent {ws_agent_id} connected to Agent Bus")
                return True
        except ImportError:
            logger.debug("websockets package not installed, Agent Bus disabled")
        except Exception as e:
            logger.warning(f"Agent Bus connect failed: {e}")
        return False

    async def disconnect_from_bus(self) -> None:
        """Disconnect from the Agent Event Bus."""
        self._ws_connected = False
        self._ws_enabled = False
        if self._ws_receive_task:
            self._ws_receive_task.cancel()
            try:
                await self._ws_receive_task
            except asyncio.CancelledError:
                pass
            self._ws_receive_task = None
        if self._ws_connection:
            await self._ws_connection.close()
            self._ws_connection = None
        agent_id = getattr(self, "agent_id", "unknown")
        logger.info(f"Agent {agent_id} disconnected from Agent Bus")

    async def send_event(
        self,
        event_type: str,
        to_agent: str = "broadcast",
        payload: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Send an event to the Agent Bus.
        If disconnected, buffers event for replay on reconnect.

        Returns:
            True if sent, False if buffered or unavailable.
        """
        if not self._ws_enabled:
            return False

        getattr(self, "agent_id", "unknown")
        msg = {
            "type": event_type,
            "to_agent": to_agent,
            "payload": payload or {},
        }
        if self._ws_connected and self._ws_connection:
            try:
                await self._ws_connection.send(json.dumps(msg))
                return True
            except Exception as e:
                logger.warning(f"Agent Bus send failed: {e}")
                self._ws_outgoing_buffer.append(msg)
                self._schedule_reconnect()
        else:
            self._ws_outgoing_buffer.append(msg)
        return False

    async def receive_events(self) -> List[Dict[str, Any]]:
        """
        Return and clear buffered events received from the bus.
        """
        events: List[Dict[str, Any]] = []
        while self._ws_incoming_buffer:
            events.append(self._ws_incoming_buffer.popleft())
        return events

    def _schedule_reconnect(self) -> None:
        """Schedule reconnect with exponential backoff."""
        if self._ws_receive_task and not self._ws_receive_task.done():
            return
        delay = RECONNECT_DELAYS[min(self._ws_reconnect_attempt, len(RECONNECT_DELAYS) - 1)]
        self._ws_reconnect_attempt += 1
        agent_id = getattr(self, "agent_id", "unknown")
        logger.info(f"Agent {agent_id} will reconnect to Agent Bus in {delay}s")
        asyncio.create_task(self._delayed_reconnect(delay))

    async def _delayed_reconnect(self, delay: float) -> None:
        await asyncio.sleep(delay)
        agent_id = getattr(self, "agent_id", "unknown")
        if await self.connect_to_bus(agent_id):
            while self._ws_outgoing_buffer and self._ws_connection:
                msg = self._ws_outgoing_buffer.popleft()
                try:
                    await self._ws_connection.send(json.dumps(msg))
                except Exception:
                    self._ws_outgoing_buffer.appendleft(msg)
                    break

    async def _receive_events_loop(self) -> None:
        """Background loop to receive events from the bus."""
        while self._ws_connected and self._ws_connection:
            try:
                raw = await self._ws_connection.recv()
                data = json.loads(raw)
                if data.get("type") == "message" and "data" in data:
                    self._ws_incoming_buffer.append(data)
                elif data.get("type") == "heartbeat":
                    if self._ws_connection:
                        await self._ws_connection.send(
                            json.dumps({"type": "heartbeat", "payload": {}})
                        )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Agent Bus receive error: {e}")
                self._ws_connected = False
                self._schedule_reconnect()
                break
