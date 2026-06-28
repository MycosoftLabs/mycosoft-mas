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


@pytest.mark.asyncio
async def test_nav_thruster_params_and_runtime_echo(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    async def _fake_forward(registry_id, *, target, cmd, params, timeout_s=8.0):
        captured.update(
            {"registry_id": registry_id, "target": target, "cmd": cmd, "params": params}
        )
        return {
            "relay": "jetson_mdp",
            "response": {
                "propulsion": {
                    "thrusters": [
                        {
                            "id": 0,
                            "throttlePct": params["throttle"],
                            "azimuthDeg": params["azimuth"],
                            "currentA": 1.8,
                            "rpm": 2400,
                            "faulted": False,
                        }
                    ]
                }
            },
        }

    monkeypatch.setattr(
        "mycosoft_mas.devices.psathyrella.command_handler.forward_mdp_command",
        _fake_forward,
    )

    runtime = get_runtime(PSATHYRELLA_DEVICE_ID)
    runtime.thrusters[0].throttle_pct = 0
    runtime.thrusters[0].azimuth_deg = 0
    runtime.thrusters[0].current_a = None
    runtime.thrusters[0].rpm = None

    result = await handle_mdp_command(
        PSATHYRELLA_DEVICE_ID,
        target="side_b",
        cmd="nav.thruster",
        params={"id": 0, "throttle": 35, "azimuth": 90},
        client_command_id="cmd_jog_1",
    )

    assert result["ok"] is True
    assert result["cmd"] == "nav.thruster"
    assert captured["target"] == "side_b"
    assert captured["params"] == {"id": 0, "throttle": 35, "azimuth": 90}
    assert result["ack"]["state"] == "applied"
    assert result["ack"]["commandId"] == "cmd_jog_1"
    assert runtime.thrusters[0].throttle_pct == 35.0
    assert runtime.thrusters[0].azimuth_deg == 90.0
    assert runtime.thrusters[0].current_a == 1.8
    assert runtime.thrusters[0].rpm == 2400.0


@pytest.mark.asyncio
async def test_nav_thruster_azimuth_only(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    async def _fake_forward(registry_id, *, target, cmd, params, timeout_s=8.0):
        captured.update({"cmd": cmd, "params": params, "target": target})
        return {"relay": "jetson_mdp", "response": {"ok": True}}

    monkeypatch.setattr(
        "mycosoft_mas.devices.psathyrella.command_handler.forward_mdp_command",
        _fake_forward,
    )

    runtime = get_runtime(PSATHYRELLA_DEVICE_ID)
    result = await handle_mdp_command(
        PSATHYRELLA_DEVICE_ID,
        target="side_b",
        cmd="nav.thruster_azimuth",
        params={"id": 0, "azimuthDeg": 270},
    )

    assert result["ok"] is True
    assert captured["cmd"] == "nav.thruster_azimuth"
    assert captured["params"] == {"id": 0, "azimuth": 270}
    assert runtime.thrusters[0].azimuth_deg == 270.0


@pytest.mark.asyncio
async def test_nav_all_stop_and_arm_forward(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list = []

    async def _fake_forward(registry_id, *, target, cmd, params, timeout_s=8.0):
        calls.append({"cmd": cmd, "params": params, "target": target})
        return {"relay": "jetson_mdp", "response": {"ok": True}}

    monkeypatch.setattr(
        "mycosoft_mas.devices.psathyrella.command_handler.forward_mdp_command",
        _fake_forward,
    )

    runtime = get_runtime(PSATHYRELLA_DEVICE_ID)
    runtime.thrusters[0].throttle_pct = 50
    runtime.armed = False

    stop = await handle_mdp_command(
        PSATHYRELLA_DEVICE_ID,
        target="side_b",
        cmd="nav.all_stop",
        params={},
    )
    assert stop["ok"] is True
    assert runtime.thrusters[0].throttle_pct == 0.0
    assert any(c["cmd"] == "nav.all_stop" for c in calls)

    arm = await handle_mdp_command(
        PSATHYRELLA_DEVICE_ID,
        target="side_b",
        cmd="nav.arm",
        params={"armed": True},
    )
    assert arm["ok"] is True
    assert runtime.armed is True
    assert any(c["cmd"] == "nav.arm" and c["params"]["armed"] is True for c in calls)
