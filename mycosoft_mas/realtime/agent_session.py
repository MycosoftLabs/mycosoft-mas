"""
Agent Session Manager - February 9, 2026

Session tracking and heartbeat management for Agent Event Bus.
Tracks connected agents, heartbeat timeouts, and session metadata.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

# Default heartbeat interval and timeout (seconds)
DEFAULT_HEARTBEAT_INTERVAL = 30.0
DEFAULT_HEARTBEAT_TIMEOUT = 90.0


@dataclass
class AgentSession:
    """Represents a single agent's WebSocket session."""

    agent_id: str
    connection_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_heartbeat: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    subscribed_channels: set[str] = field(default_factory=set)

    def touch(self) -> None:
        """Update last heartbeat timestamp."""
        self.last_heartbeat = datetime.now(timezone.utc)

    def is_stale(self, timeout_seconds: float = DEFAULT_HEARTBEAT_TIMEOUT) -> bool:
        """Check if session has exceeded heartbeat timeout."""
        delta = (datetime.now(timezone.utc) - self.last_heartbeat).total_seconds()
        return delta > timeout_seconds


class AgentSessionManager:
    """
    Manages agent WebSocket sessions and heartbeat monitoring.
    """

    def __init__(
        self,
        heartbeat_interval: float = DEFAULT_HEARTBEAT_INTERVAL,
        heartbeat_timeout: float = DEFAULT_HEARTBEAT_TIMEOUT,
    ):
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout
        self._sessions: Dict[str, AgentSession] = {}  # connection_id -> session
        self._agent_to_connection: Dict[str, str] = {}  # agent_id -> connection_id
        self._monitor_task: Optional[asyncio.Task] = None

    def register(
        self,
        connection_id: str,
        agent_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentSession:
        """Register a new agent session."""
        session = AgentSession(
            agent_id=agent_id,
            connection_id=connection_id,
            metadata=metadata or {},
        )
        self._sessions[connection_id] = session
        self._agent_to_connection[agent_id] = connection_id
        logger.info(f"Agent session registered: {agent_id} ({connection_id})")
        return session

    def unregister(self, connection_id: str) -> Optional[AgentSession]:
        """Remove an agent session."""
        session = self._sessions.pop(connection_id, None)
        if session:
            self._agent_to_connection.pop(session.agent_id, None)
            logger.info(f"Agent session unregistered: {session.agent_id} ({connection_id})")
        return session

    def get(self, connection_id: str) -> Optional[AgentSession]:
        """Get session by connection ID."""
        return self._sessions.get(connection_id)

    def get_by_agent(self, agent_id: str) -> Optional[AgentSession]:
        """Get session by agent ID."""
        conn_id = self._agent_to_connection.get(agent_id)
        return self._sessions.get(conn_id) if conn_id else None

    def heartbeat(self, connection_id: str) -> bool:
        """Record heartbeat for a session. Returns True if session exists."""
        session = self._sessions.get(connection_id)
        if session:
            session.touch()
            return True
        return False

    def subscribe(self, connection_id: str, channels: set[str]) -> None:
        """Update subscribed channels for a session."""
        session = self._sessions.get(connection_id)
        if session:
            session.subscribed_channels.update(channels)

    def get_stale_connections(self) -> list[str]:
        """Return connection IDs for sessions that have exceeded heartbeat timeout."""
        return [
            conn_id
            for conn_id, session in self._sessions.items()
            if session.is_stale(self.heartbeat_timeout)
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get session manager statistics."""
        return {
            "total_sessions": len(self._sessions),
            "agent_ids": list(self._agent_to_connection.keys()),
            "heartbeat_interval": self.heartbeat_interval,
            "heartbeat_timeout": self.heartbeat_timeout,
        }

    def start_monitor(self, on_stale: Optional[Callable[..., Any]] = None) -> None:
        """
        Start background task to check for stale sessions.
        on_stale: async callback(connection_id) called for each stale session.
        """

        async def _monitor() -> None:
            while True:
                await asyncio.sleep(self.heartbeat_interval)
                stale = self.get_stale_connections()
                for conn_id in stale:
                    logger.warning(f"Agent session stale, disconnecting: {conn_id}")
                    if on_stale and callable(on_stale):
                        try:
                            if asyncio.iscoroutinefunction(on_stale):
                                await on_stale(conn_id)
                            else:
                                on_stale(conn_id)
                        except Exception as e:
                            logger.error(f"Stale callback error: {e}")

        self._monitor_task = asyncio.create_task(_monitor())
        logger.info("Agent session monitor started")

    def stop_monitor(self) -> None:
        """Stop the heartbeat monitor task."""
        if self._monitor_task:
            self._monitor_task.cancel()
            self._monitor_task = None
            logger.info("Agent session monitor stopped")
