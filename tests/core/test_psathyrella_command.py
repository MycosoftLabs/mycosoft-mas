"""Tests for Psathyrella MDP command handlers and ack envelope."""

from __future__ import annotations

import pytest

from mycosoft_mas.devices.psathyrella.command_handler import build_command_ack, handle_mdp_command
from mycosoft_mas.devices.psathyrella.constants import PSATHYRELLA_DEVICE_ID
from mycosoft_mas.devices.psathyrella.runtime_state import get_runtime


@pytest.mark.asyncio
async def test_comms_set_bearer(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = get_runtime(PSATHYRELLA_DEVICE_ID)
    runtime.preferred_bearer = None

    result = await handle_mdp_command(
        PSATHYRELLA_DEVICE_ID,
        target="side_b",
        cmd="comms.set_bearer",
        params={"bearer": "iridium"},
        client_command_id="cmd_test_1",
    )

    assert result["ok"] is True
    assert result["bearer"] == "iridium"
    assert runtime.preferred_bearer == "iridium"
    assert "ack" in result
    assert result["ack"]["state"] == "applied"
    assert result["ack"]["commandId"] == "cmd_test_1"
    assert result["ack"]["bearer"] == "iridium"


@pytest.mark.asyncio
async def test_comms_set_bearer_invalid() -> None:
    with pytest.raises(ValueError, match="bad_bearer"):
        await handle_mdp_command(
            PSATHYRELLA_DEVICE_ID,
            target="side_b",
            cmd="comms.set_bearer",
            params={"bearer": "ham_radio"},
        )


@pytest.mark.asyncio
async def test_acoustic_set_gain_clamps(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _noop_forward(*_args, **_kwargs):
        return {"status": "ok"}

    monkeypatch.setattr(
        "mycosoft_mas.devices.psathyrella.command_handler.device_registry_api.send_device_command",
        _noop_forward,
    )

    runtime = get_runtime(PSATHYRELLA_DEVICE_ID)
    result = await handle_mdp_command(
        PSATHYRELLA_DEVICE_ID,
        target="side_a",
        cmd="acoustic.set_gain",
        params={"gain_db": 99.0},
    )

    assert result["ok"] is True
    assert result["gainDb"] == 48.0
    assert runtime.hydrophone_gain_db == 48.0
    assert result["ack"]["state"] == "applied"


@pytest.mark.asyncio
async def test_mission_upload_and_abort(monkeypatch: pytest.MonkeyPatch) -> None:
    stored: dict = {}

    class _FakeRedis:
        async def set(self, key: str, value: str, ex: int | None = None) -> None:
            stored[key] = value

    async def _fake_get_redis():
        return _FakeRedis()

    monkeypatch.setattr(
        "mycosoft_mas.devices.psathyrella.mission_executor._get_redis",
        _fake_get_redis,
    )

    plan = {
        "id": "m_test_1",
        "name": "Reef survey",
        "tasks": [{"id": "t1", "kind": "transit", "lat": 32.56, "lon": -117.13}],
        "commsLossPolicy": "rtl",
        "createdMs": 1749990000000,
    }

    upload = await handle_mdp_command(
        PSATHYRELLA_DEVICE_ID,
        target="side_b",
        cmd="mission.upload",
        params={"plan": plan},
    )

    assert upload["ok"] is True
    assert upload["missionId"] == "m_test_1"
    assert upload["tasks"] == 1
    runtime = get_runtime(PSATHYRELLA_DEVICE_ID)
    assert runtime.active_mission_id == "m_test_1"
    assert runtime.comms_loss_policy == "rtl"

    abort = await handle_mdp_command(
        PSATHYRELLA_DEVICE_ID,
        target="side_b",
        cmd="mission.abort",
        params={},
    )

    assert abort["ok"] is True
    assert abort["mode"] == "RTL"
    assert runtime.active_mission_id is None
    assert runtime.mode == "RTL"


@pytest.mark.asyncio
async def test_mission_upload_requires_plan() -> None:
    with pytest.raises(ValueError, match="mission.upload"):
        await handle_mdp_command(
            PSATHYRELLA_DEVICE_ID,
            target="side_b",
            cmd="mission.upload",
            params={},
        )


def test_build_command_ack_shape() -> None:
    ack = build_command_ack(
        cmd="nav.station_keep",
        state="applied",
        client_command_id="cmd_abc",
        bearer="lora",
        accepted_ms=1000,
        applied_ms=1333,
        detail="ok",
    )
    assert ack["commandId"] == "cmd_abc"
    assert ack["state"] == "applied"
    assert ack["latencyMs"] == 333
    assert ack["bearer"] == "lora"
