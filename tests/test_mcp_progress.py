"""
Tests for MCP Progress Notifier - February 9, 2026

Unit tests for progress emission to agents:tool_calls.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestProgressNotifier:
    """Tests for emit_progress."""

    @pytest.mark.asyncio
    async def test_emit_progress_no_raise_when_redis_unavailable(self):
        """emit_progress does not raise when Redis unavailable."""
        from mycosoft_mas.mcp.progress_notifier import emit_progress

        with patch("mycosoft_mas.realtime.redis_pubsub.get_client", new_callable=AsyncMock) as m:
            m.side_effect = ImportError("redis not available")
            await emit_progress("test_tool", 0, 1, "Starting")

    @pytest.mark.asyncio
    async def test_emit_progress_publishes_when_connected(self):
        """emit_progress publishes when Redis connected."""
        from mycosoft_mas.mcp.progress_notifier import emit_progress

        mock_client = MagicMock()
        mock_client.is_connected.return_value = True
        mock_client.publish = AsyncMock(return_value=True)

        with patch("mycosoft_mas.realtime.redis_pubsub.get_client", new_callable=AsyncMock) as m:
            m.return_value = mock_client
            await emit_progress("memory_search", 1, 2, "Searching")
            mock_client.publish.assert_called_once()
            call_args = mock_client.publish.call_args
            assert call_args[0][0] == "agents:tool_calls"
            data = call_args[0][1]
            assert data["type"] == "progress"
            assert data["tool"] == "memory_search"
            assert data["progress"] == 1
            assert data["total"] == 2
