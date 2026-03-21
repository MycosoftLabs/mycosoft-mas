"""
Tests for Agent WebSocket Mixin - February 9, 2026

Unit tests for AgentWebSocketMixin and BaseAgent WS integration.
"""

from unittest.mock import patch

import pytest


class TestAgentWebSocketMixin:
    """Tests for AgentWebSocketMixin."""

    def test_init_ws_mixin(self):
        """Mixin initializes state correctly."""
        from mycosoft_mas.agents.websocket_mixin import AgentWebSocketMixin

        mixin = AgentWebSocketMixin()
        mixin.__init_ws_mixin__()
        assert mixin._ws_enabled is False
        assert mixin._ws_connected is False
        assert mixin._ws_connection is None

    @patch.dict("os.environ", {"MYCA_AGENT_WS_ENABLED": "false"})
    @pytest.mark.asyncio
    async def test_connect_when_disabled(self):
        """connect_to_bus returns False when WS disabled."""
        from mycosoft_mas.agents.websocket_mixin import AgentWebSocketMixin

        mixin = AgentWebSocketMixin()
        mixin.__init_ws_mixin__()
        mixin.agent_id = "test-agent"
        result = await mixin.connect_to_bus("test-agent")
        assert result is False

    @patch.dict("os.environ", {"MYCA_AGENT_WS_ENABLED": "true"})
    @pytest.mark.asyncio
    async def test_send_event_buffers_when_disconnected(self):
        """send_event buffers when disconnected."""
        from mycosoft_mas.agents.websocket_mixin import AgentWebSocketMixin

        mixin = AgentWebSocketMixin()
        mixin.__init_ws_mixin__()
        mixin._ws_connected = False
        mixin._ws_enabled = True
        mixin.agent_id = "test-agent"
        await mixin.send_event("heartbeat", "broadcast", {})
        assert len(mixin._ws_outgoing_buffer) == 1
