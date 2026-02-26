"""
Tests for Agent Event Bus - February 9, 2026

Unit tests for event schema, agent bus router, and session management.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from mycosoft_mas.realtime.event_schema import AgentEvent, EVENT_TYPES


class TestAgentEventSchema:
    """Tests for AgentEvent Pydantic model."""

    def test_valid_event_minimal(self):
        """Minimal valid event passes validation."""
        ev = AgentEvent(
            type="task",
            from_agent="agent-a",
            to_agent="agent-b",
        )
        assert ev.type == "task"
        assert ev.from_agent == "agent-a"
        assert ev.to_agent == "agent-b"
        assert ev.payload == {}
        assert ev.trace_id
        assert ev.classification == "UNCLASS"

    def test_valid_event_broadcast(self):
        """Broadcast target is valid."""
        ev = AgentEvent(
            type="heartbeat",
            from_agent="agent-x",
            to_agent="broadcast",
            payload={"status": "alive"},
        )
        assert ev.to_agent == "broadcast"
        assert ev.payload["status"] == "alive"

    def test_valid_event_types(self):
        """All EVENT_TYPES are accepted."""
        for t in ["task", "result", "alert", "heartbeat", "tool_call", "status"]:
            ev = AgentEvent(type=t, from_agent="a", to_agent="b")
            assert ev.type == t

    def test_from_agent_required(self):
        """from_agent is required."""
        with pytest.raises(ValueError):
            AgentEvent(type="task", from_agent="", to_agent="b")

    def test_extra_forbidden(self):
        """Extra fields are rejected."""
        with pytest.raises(ValueError):
            AgentEvent(
                type="task",
                from_agent="a",
                to_agent="b",
                unknown_field="x",
            )


class TestAgentBusRouter:
    """Tests for Agent Bus router creation and behavior."""

    @patch.dict("os.environ", {"MYCA_AGENT_BUS_ENABLED": "true"})
    def test_router_created(self):
        """Router can be created when bus enabled."""
        from mycosoft_mas.realtime.agent_bus import create_agent_bus_router

        router = create_agent_bus_router()
        assert router.prefix == "/ws"
        assert router.routes

    @patch.dict("os.environ", {"MYCA_AGENT_BUS_ENABLED": "false"})
    def test_router_still_creatable_when_disabled(self):
        """Router is created even when bus disabled (endpoint will close connections)."""
        from mycosoft_mas.realtime.agent_bus import create_agent_bus_router

        router = create_agent_bus_router()
        assert router is not None


class TestAgentSessionManager:
    """Tests for AgentSessionManager."""

    def test_register_and_get(self):
        """Session can be registered and retrieved."""
        from mycosoft_mas.realtime.agent_session import AgentSessionManager

        mgr = AgentSessionManager()
        mgr.register("conn-1", "agent-x", metadata={"foo": "bar"})
        sess = mgr.get("conn-1")
        assert sess is not None
        assert sess.agent_id == "agent-x"
        assert sess.metadata.get("foo") == "bar"

    def test_unregister_returns_session(self):
        """Unregister returns the session."""
        from mycosoft_mas.realtime.agent_session import AgentSessionManager

        mgr = AgentSessionManager()
        mgr.register("conn-1", "agent-x")
        sess = mgr.unregister("conn-1")
        assert sess is not None
        assert sess.agent_id == "agent-x"
        assert mgr.get("conn-1") is None
