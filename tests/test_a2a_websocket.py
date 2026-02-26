"""
Tests for A2A WebSocket - February 9, 2026

Unit tests for /a2a/v1/ws WebSocket endpoint.
"""

import pytest

# Skip if routers import chain fails (e.g. jsonschema not installed)
pytest.importorskip("jsonschema", reason="jsonschema required for core routers")


class TestA2AWebSocketRouter:
    """Tests for A2A WebSocket router."""

    def test_router_has_websocket_route(self):
        """A2A WS router has WebSocket route."""
        from mycosoft_mas.core.routers.a2a_websocket import router

        assert router is not None
        routes = [r.path for r in router.routes]
        assert "/a2a/v1/ws" in routes
