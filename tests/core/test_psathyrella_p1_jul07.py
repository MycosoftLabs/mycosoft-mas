"""Psathyrella P1 bench features — registry persist + esc calibrate forward."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from mycosoft_mas.core.routers import device_registry_api
from mycosoft_mas.devices.psathyrella.command_handler import handle_mdp_command
from mycosoft_mas.devices.psathyrella.constants import PSATHYRELLA_CANONICAL_DEVICE_ID


@pytest.mark.asyncio
async def test_nav_esc_calibrate_forwards(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    async def _fake_forward(registry_id, *, target, cmd, params, timeout_s=8.0):
        captured.update({"cmd": cmd, "params": params, "timeout_s": timeout_s})
        return {
            "relay": "jetson_mdp",
            "response": {"ok": True, "detail": "esc_range_calibration", "calibration": {"dry_run": True}},
        }

    monkeypatch.setattr(
        "mycosoft_mas.devices.psathyrella.command_handler.forward_mdp_command",
        _fake_forward,
    )

    result = await handle_mdp_command(
        PSATHYRELLA_CANONICAL_DEVICE_ID,
        target="side_b",
        cmd="nav.esc_calibrate",
        params={"dry_run": True, "id": 0},
    )

    assert result["ok"] is True
    assert captured["cmd"] == "nav.esc_calibrate"
    assert captured["params"] == {"dry_run": True, "id": 0}
    assert captured["timeout_s"] == 30.0
    assert result["ack"]["state"] == "applied"


def test_psathyrella_bench_registry_not_expired(monkeypatch: pytest.MonkeyPatch) -> None:
    device_id = PSATHYRELLA_CANONICAL_DEVICE_ID
    stale = datetime.now(timezone.utc) - timedelta(seconds=device_registry_api.DEVICE_TTL_SECONDS + 60)

    device_registry_api._device_registry[device_id] = {  # noqa: SLF001
        "device_id": device_id,
        "host": "192.168.0.123",
    }
    device_registry_api._device_last_seen[device_id] = stale  # noqa: SLF001

    monkeypatch.setattr(
        "mycosoft_mas.devices.psathyrella.constants.PSATHYRELLA_BENCH_REGISTRY_PERSIST",
        True,
    )

    device_registry_api._cleanup_expired_devices()  # noqa: SLF001

    assert device_id in device_registry_api._device_registry  # noqa: SLF001

    device_registry_api._device_last_seen.pop(device_id, None)  # noqa: SLF001
    device_registry_api._device_registry.pop(device_id, None)  # noqa: SLF001


def test_esc_neutral_channel_override_parsing() -> None:
    raw = "8:1610,9:1595,10:1600,11:1605"
    neutral_default = 1600
    overrides: dict[int, int] = {}
    for entry in raw.split(","):
        ch_s, us_s = entry.split(":", 1)
        overrides[int(ch_s)] = int(us_s)

    def esc_us(throttle: float, channel: int) -> float:
        neutral = overrides.get(channel, neutral_default)
        return neutral + (max(-100, min(100, throttle)) / 100.0) * 500.0

    assert esc_us(100, 8) == 2110.0
    assert esc_us(-100, 9) == 1095.0
    assert esc_us(0, 11) == 1605.0
