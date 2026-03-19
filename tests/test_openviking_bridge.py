"""
Tests for OpenViking integration — client, bridge, sync, API, agent.

Tests cover:
- OpenVikingClient: HTTP client for OpenViking servers
- OpenVikingBridge: MAS ↔ device memory bridge
- OpenVikingSyncService: Periodic and event-driven sync
- OpenVikingAgent: Task handler dispatch
- openviking_api router: REST endpoint validation

Created: March 19, 2026
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Unit Tests: OpenVikingClient ───────────────────────────────────────


class TestOpenVikingClient:
    """Unit tests for the low-level HTTP client."""

    def test_client_construction(self):
        from mycosoft_mas.edge.openviking_client import OpenVikingClient

        client = OpenVikingClient(host="192.168.0.123", port=1933)
        assert client.host == "192.168.0.123"
        assert client.port == 1933
        assert client._base_url == "http://192.168.0.123:1933"
        assert not client.is_connected

    def test_client_custom_url(self):
        from mycosoft_mas.edge.openviking_client import OpenVikingClient

        client = OpenVikingClient(
            host="example.com",
            base_url="https://custom.url:9999",
        )
        assert client._base_url == "https://custom.url:9999"

    def test_client_with_api_key(self):
        from mycosoft_mas.edge.openviking_client import OpenVikingClient

        client = OpenVikingClient(host="localhost", api_key="test-key")
        headers = client._headers()
        assert headers["Authorization"] == "Bearer test-key"

    def test_client_without_api_key(self):
        from mycosoft_mas.edge.openviking_client import OpenVikingClient

        client = OpenVikingClient(host="localhost")
        headers = client._headers()
        assert "Authorization" not in headers

    @pytest.mark.asyncio
    async def test_client_health_check_unreachable(self):
        from mycosoft_mas.edge.openviking_client import OpenVikingClient

        client = OpenVikingClient(host="192.168.0.254", port=1933, timeout=1.0)
        health = await client.health_check()
        assert health["reachable"] is False
        assert "error" in health

    @pytest.mark.asyncio
    async def test_client_connect_unreachable(self):
        from mycosoft_mas.edge.openviking_client import OpenVikingClient

        client = OpenVikingClient(host="192.168.0.254", port=1933, timeout=1.0)
        connected = await client.connect()
        assert connected is False
        assert not client.is_connected

    @pytest.mark.asyncio
    async def test_client_disconnect_no_client(self):
        from mycosoft_mas.edge.openviking_client import OpenVikingClient

        client = OpenVikingClient(host="localhost")
        await client.disconnect()
        assert not client.is_connected


# ── Unit Tests: DeviceConnection ───────────────────────────────────────


class TestDeviceConnection:
    """Tests for the DeviceConnection dataclass."""

    def test_device_connection_creation(self):
        from mycosoft_mas.memory.openviking_bridge import (
            DeviceConnection,
            DeviceConnectionStatus,
        )

        conn = DeviceConnection(
            device_id="mushroom1",
            device_name="Mushroom1",
            openviking_url="http://192.168.0.123:1933",
            host="192.168.0.123",
            port=1933,
        )
        assert conn.device_id == "mushroom1"
        assert conn.status == DeviceConnectionStatus.DISCONNECTED
        assert conn.sync_count == 0
        assert conn.last_sync is None

    def test_device_connection_to_dict(self):
        from mycosoft_mas.memory.openviking_bridge import DeviceConnection

        conn = DeviceConnection(
            device_id="test1",
            device_name="Test Device",
            openviking_url="http://localhost:1933",
            host="localhost",
            port=1933,
            tags=["mushroom", "env"],
        )
        d = conn.to_dict()
        assert d["device_id"] == "test1"
        assert d["device_name"] == "Test Device"
        assert d["status"] == "disconnected"
        assert d["tags"] == ["mushroom", "env"]


# ── Unit Tests: OpenVikingBridge ───────────────────────────────────────


class TestOpenVikingBridge:
    """Unit tests for the MAS ↔ device bridge."""

    @pytest.mark.asyncio
    async def test_bridge_initialization(self):
        from mycosoft_mas.memory.openviking_bridge import OpenVikingBridge

        bridge = OpenVikingBridge()
        assert not bridge._initialized
        assert len(bridge._devices) == 0

    @pytest.mark.asyncio
    async def test_bridge_list_devices_empty(self):
        from mycosoft_mas.memory.openviking_bridge import OpenVikingBridge

        bridge = OpenVikingBridge()
        devices = bridge.list_devices()
        assert devices == []

    @pytest.mark.asyncio
    async def test_bridge_get_device_missing(self):
        from mycosoft_mas.memory.openviking_bridge import OpenVikingBridge

        bridge = OpenVikingBridge()
        assert bridge.get_device("nonexistent") is None

    @pytest.mark.asyncio
    async def test_bridge_unregister_missing_device(self):
        from mycosoft_mas.memory.openviking_bridge import OpenVikingBridge

        bridge = OpenVikingBridge()
        result = await bridge.unregister_device("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_bridge_get_client_raises_for_unknown(self):
        from mycosoft_mas.memory.openviking_bridge import OpenVikingBridge

        bridge = OpenVikingBridge()
        with pytest.raises(ValueError, match="Device not registered"):
            bridge._get_client("unknown")

    @pytest.mark.asyncio
    async def test_bridge_register_unreachable_device(self):
        """Register a device that is unreachable — should still register with ERROR status."""
        from mycosoft_mas.memory.openviking_bridge import (
            DeviceConnectionStatus,
            OpenVikingBridge,
        )

        bridge = OpenVikingBridge()
        conn = await bridge.register_device(
            device_id="test_device",
            openviking_url="http://192.168.0.254:1933",
            device_name="Test",
        )
        assert conn.device_id == "test_device"
        assert conn.status == DeviceConnectionStatus.ERROR
        assert "test_device" in bridge._devices

    @pytest.mark.asyncio
    async def test_bridge_health_check_no_devices(self):
        from mycosoft_mas.memory.openviking_bridge import OpenVikingBridge

        bridge = OpenVikingBridge()
        bridge._initialized = True
        health = await bridge.health_check()
        assert health["bridge_status"] == "healthy"
        assert health["device_count"] == 0


# ── Unit Tests: OpenVikingSyncService ──────────────────────────────────


class TestOpenVikingSyncService:
    """Unit tests for the sync service."""

    def test_sync_service_creation(self):
        from mycosoft_mas.memory.openviking_sync import OpenVikingSyncService

        sync = OpenVikingSyncService(sync_interval=60)
        assert sync._sync_interval == 60
        assert not sync.is_running

    def test_sync_service_default_interval(self):
        from mycosoft_mas.memory.openviking_sync import OpenVikingSyncService

        sync = OpenVikingSyncService()
        assert sync._sync_interval == 300  # 5 minutes default

    def test_sync_service_status(self):
        from mycosoft_mas.memory.openviking_sync import OpenVikingSyncService

        sync = OpenVikingSyncService(sync_interval=120)
        status = sync.get_status()
        assert status["running"] is False
        assert status["sync_interval"] == 120
        assert status["history_count"] == 0
        assert status["last_sync"] is None

    def test_sync_service_history_empty(self):
        from mycosoft_mas.memory.openviking_sync import OpenVikingSyncService

        sync = OpenVikingSyncService()
        history = sync.get_history()
        assert history == []

    def test_sync_event_handler_registration(self):
        from mycosoft_mas.memory.openviking_sync import OpenVikingSyncService

        sync = OpenVikingSyncService()
        handler = MagicMock()
        sync.on_event(handler)
        assert handler in sync._event_handlers


# ── Unit Tests: OpenVikingAgent ────────────────────────────────────────


class TestOpenVikingAgent:
    """Unit tests for the OpenViking agent."""

    def test_agent_creation(self):
        from mycosoft_mas.agents.openviking_agent import OpenVikingAgent

        agent = OpenVikingAgent()
        assert agent.agent_id == "openviking_agent"
        assert agent.name == "OpenViking Agent"
        assert "openviking_device_management" in agent.capabilities
        assert "edge_memory_sync" in agent.capabilities

    def test_agent_custom_id(self):
        from mycosoft_mas.agents.openviking_agent import OpenVikingAgent

        agent = OpenVikingAgent(agent_id="custom_ov", name="Custom OV")
        assert agent.agent_id == "custom_ov"
        assert agent.name == "Custom OV"

    @pytest.mark.asyncio
    async def test_agent_unknown_task_type(self):
        from mycosoft_mas.agents.openviking_agent import OpenVikingAgent

        agent = OpenVikingAgent()
        result = await agent.process_task({"type": "nonexistent_task"})
        assert result["status"] == "error"
        assert "Unknown task type" in result["error"]
        assert "supported_types" in result


# ── Unit Tests: Layer Mapping ──────────────────────────────────────────


class TestLayerMapping:
    """Tests for the viking:// → MAS layer mapping."""

    def test_layer_map_completeness(self):
        from mycosoft_mas.memory.openviking_bridge import VIKING_TO_MAS_LAYER_MAP

        assert "viking://memories/sensor-observations/" in VIKING_TO_MAS_LAYER_MAP
        assert "viking://memories/task-completions/" in VIKING_TO_MAS_LAYER_MAP
        assert "viking://memories/errors-learned/" in VIKING_TO_MAS_LAYER_MAP
        assert "viking://resources/mas-agent-context/" in VIKING_TO_MAS_LAYER_MAP
        assert "viking://skills/" in VIKING_TO_MAS_LAYER_MAP

    def test_sensor_observations_to_episodic(self):
        from mycosoft_mas.memory.openviking_bridge import VIKING_TO_MAS_LAYER_MAP

        assert VIKING_TO_MAS_LAYER_MAP["viking://memories/sensor-observations/"] == "episodic"

    def test_errors_learned_to_semantic(self):
        from mycosoft_mas.memory.openviking_bridge import VIKING_TO_MAS_LAYER_MAP

        assert VIKING_TO_MAS_LAYER_MAP["viking://memories/errors-learned/"] == "semantic"

    def test_skills_to_procedural(self):
        from mycosoft_mas.memory.openviking_bridge import VIKING_TO_MAS_LAYER_MAP

        assert VIKING_TO_MAS_LAYER_MAP["viking://skills/"] == "procedural"


# ── Unit Tests: API Router Models ─────────────────────────────────────


class TestAPIModels:
    """Tests for Pydantic request/response models."""

    def test_device_register_request(self):
        from mycosoft_mas.core.routers.openviking_api import DeviceRegisterRequest

        req = DeviceRegisterRequest(
            device_id="m1",
            openviking_url="http://192.168.0.123:1933",
            device_name="Mushroom1",
            tags=["mushroom", "env"],
        )
        assert req.device_id == "m1"
        assert req.tags == ["mushroom", "env"]

    def test_query_request_defaults(self):
        from mycosoft_mas.core.routers.openviking_api import QueryRequest

        req = QueryRequest(query="temperature readings")
        assert req.tier == "L1"
        assert req.top_k == 10
        assert req.target_uri is None

    def test_push_request_defaults(self):
        from mycosoft_mas.core.routers.openviking_api import PushRequest

        req = PushRequest(content="test content")
        assert req.viking_path == "viking://resources/mas-agent-context/"
        assert req.reason is None

    def test_sync_response_model(self):
        from mycosoft_mas.core.routers.openviking_api import SyncResponse

        resp = SyncResponse(
            device_id="m1",
            synced_items=5,
            pushed_items=3,
            errors=0,
            timestamp="2026-03-19T00:00:00+00:00",
        )
        assert resp.synced_items == 5
        assert resp.errors == 0


# ── Integration Tests (skip if MAS/devices unreachable) ────────────────

SKIP_INTEGRATION = os.environ.get("SKIP_INTEGRATION", "1") == "1"
MAS_URL = os.environ.get("MAS_API_URL", "http://192.168.0.188:8001")


def _mas_reachable() -> bool:
    try:
        import httpx

        r = httpx.get(f"{MAS_URL}/health", timeout=5)
        return r.status_code < 500
    except Exception:
        return False


@pytest.mark.skipif(SKIP_INTEGRATION, reason="SKIP_INTEGRATION=1")
@pytest.mark.skipif(not _mas_reachable(), reason="MAS VM unreachable")
class TestOpenVikingAPIIntegration:
    """Integration tests against the live MAS API."""

    def test_openviking_health(self):
        import httpx

        r = httpx.get(f"{MAS_URL}/api/openviking/health", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert "bridge_status" in data

    def test_openviking_list_devices(self):
        import httpx

        r = httpx.get(f"{MAS_URL}/api/openviking/devices", timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_openviking_sync_status(self):
        import httpx

        r = httpx.get(f"{MAS_URL}/api/openviking/sync/status", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert "running" in data
        assert "sync_interval" in data
