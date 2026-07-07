from __future__ import annotations

import httpx
import pytest

from mycosoft_mas.core.routers import device_registry_api
from mycosoft_mas.devices.psathyrella.constants import PSATHYRELLA_REGISTRY_ID
from mycosoft_mas.devices.psathyrella.jetson_forward import (
    _decode_json_response,
    _post_mdp_payload,
    forward_mdp_command,
)


@pytest.mark.asyncio
async def test_nav_commands_use_propulsion_agent_port(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    monkeypatch.delenv("PSATHYRELLA_PROPULSION_AGENT_URL", raising=False)
    monkeypatch.delenv("PSATHYRELLA_PROPULSION_AGENT_PORT", raising=False)
    monkeypatch.delenv("PSATHYRELLA_JETSON_PROPULSION_PORT", raising=False)
    monkeypatch.setattr(
        device_registry_api,
        "_device_registry",
        {
            PSATHYRELLA_REGISTRY_ID: {
                "host": "192.168.0.123",
                "port": 8787,
                "extra": {"agent_url": "http://192.168.0.123:8787"},
            }
        },
    )

    async def _fake_post(base_url: str, *, target: str, cmd: str, params: dict, timeout_s: float):
        captured["base_url"] = base_url
        captured["cmd"] = cmd
        return {"ok": True}, None

    async def _unexpected_fallback(*_args, **_kwargs):
        raise AssertionError("nav commands must not fall back to device registry")

    monkeypatch.setattr(
        "mycosoft_mas.devices.psathyrella.jetson_forward._post_mdp_payload",
        _fake_post,
    )
    monkeypatch.setattr(device_registry_api, "send_device_command", _unexpected_fallback)

    result = await forward_mdp_command(
        PSATHYRELLA_REGISTRY_ID,
        target="side_b",
        cmd="nav.all_stop",
        params={},
    )

    assert captured["base_url"] == "http://192.168.0.123:8788"
    assert captured["cmd"] == "nav.all_stop"
    assert result["relay"] == "jetson_mdp"
    assert result["base_url"] == "http://192.168.0.123:8788"


@pytest.mark.asyncio
async def test_nav_commands_do_not_fallback_when_propulsion_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(device_registry_api, "_device_registry", {})

    async def _fake_post(*_args, **_kwargs):
        return None, "agent_unreachable"

    async def _unexpected_fallback(*_args, **_kwargs):
        raise AssertionError("nav commands must not fall back to device registry")

    monkeypatch.setattr(
        "mycosoft_mas.devices.psathyrella.jetson_forward._post_mdp_payload",
        _fake_post,
    )
    monkeypatch.setattr(device_registry_api, "send_device_command", _unexpected_fallback)

    result = await forward_mdp_command(
        PSATHYRELLA_REGISTRY_ID,
        target="side_b",
        cmd="nav.arm",
        params={"armed": True},
    )

    assert result["relay"] == "jetson_mdp"
    assert result["response"] is None
    assert result["error"] == "agent_unreachable"


def test_decode_json_response_hardens_invalid_json() -> None:
    response = httpx.Response(200, text='{"ok": true, "serialConnected": 1e}')

    payload, err = _decode_json_response(response, "/command")

    assert err == "agent_invalid_json:/command"
    assert payload is not None
    assert payload["ok"] is False
    assert '1e' in payload["raw"]


@pytest.mark.asyncio
async def test_post_mdp_payload_reports_missing_command_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [
        httpx.Response(404, text='{"ok":false,"error":"not found"}'),
        httpx.Response(404, text='{"ok":false,"error":"not found"}'),
        httpx.Response(404, text='{"ok":false,"error":"not found"}'),
    ]

    class _FakeClient:
        is_closed = False

        async def post(self, *_args, **_kwargs):
            return responses.pop(0)

    fake = _FakeClient()

    async def _fake_get_client() -> _FakeClient:
        return fake

    monkeypatch.setattr(
        "mycosoft_mas.devices.psathyrella.jetson_forward._get_propulsion_http_client",
        _fake_get_client,
    )

    payload, err = await _post_mdp_payload(
        "http://192.168.0.123:8788",
        target="side_b",
        cmd="nav.all_stop",
        params={},
        timeout_s=5.0,
    )

    assert payload is None
    assert err == "agent_no_command_endpoint"


@pytest.mark.asyncio
async def test_nav_az_zero_uses_propulsion_agent_port(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    monkeypatch.setattr(device_registry_api, "_device_registry", {})

    async def _fake_post(base_url: str, *, target: str, cmd: str, params: dict, timeout_s: float):
        captured["base_url"] = base_url
        captured["cmd"] = cmd
        return {"ok": True, "detail": "azimuth home set for [0, 1, 2, 3]"}, None

    monkeypatch.setattr(
        "mycosoft_mas.devices.psathyrella.jetson_forward._post_mdp_payload",
        _fake_post,
    )

    result = await forward_mdp_command(
        PSATHYRELLA_REGISTRY_ID,
        target="side_b",
        cmd="nav.az_zero",
        params={},
    )

    assert captured["cmd"] == "nav.az_zero"
    assert result["relay"] == "jetson_mdp"
    assert result["base_url"].endswith(":8788")
