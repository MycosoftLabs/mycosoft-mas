"""MDP nav/cam/comms/acoustic/mission command dispatch for Psathyrella GCS contract."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from mycosoft_mas.core.routers import device_registry_api
from mycosoft_mas.devices.psathyrella.autonomy import WaypointRecord
from mycosoft_mas.devices.psathyrella.comms_bridge import get_psathyrella_comms_bridge
from mycosoft_mas.devices.psathyrella.constants import (
    PSATHYRELLA_DEVICE_ID,
    resolve_mdp_device_id,
    resolve_registry_device_id,
)
from mycosoft_mas.devices.psathyrella.mission_executor import get_mission_executor, load_mission_plan
from mycosoft_mas.devices.psathyrella.runtime_state import (
    VALID_BEARERS,
    get_autonomy_controller,
    get_runtime,
)

logger = logging.getLogger(__name__)

FRONTEND_MODES = {
    "MANUAL",
    "STABILIZE",
    "DEPTH_HOLD",
    "STATION_KEEP",
    "GUIDED",
    "AUTO",
    "SIGNAL_FOLLOW",
    "RTL",
}

_ack_seq = 0


def _next_ack_seq() -> int:
    global _ack_seq
    _ack_seq += 1
    return _ack_seq


def build_command_ack(
    *,
    cmd: str,
    state: str = "applied",
    client_command_id: Optional[str] = None,
    bearer: Optional[str] = None,
    accepted_ms: Optional[int] = None,
    applied_ms: Optional[int] = None,
    detail: Optional[str] = None,
    device_response: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Structured ack envelope for GCS command ledger."""
    accepted = accepted_ms if accepted_ms is not None else int(time.time() * 1000)
    applied = applied_ms if applied_ms is not None else accepted
    latency = applied - accepted if applied is not None and accepted is not None else None
    ack: Dict[str, Any] = {
        "commandId": client_command_id,
        "seq": _next_ack_seq(),
        "state": state,
        "bearer": bearer,
        "acceptedMs": accepted,
        "appliedMs": applied if state == "applied" else None,
        "latencyMs": latency if state == "applied" else None,
        "detail": detail,
    }
    if device_response is not None:
        ack["deviceResponse"] = device_response
    return ack


def _map_nav_mode(mode: str) -> str:
    upper = (mode or "MANUAL").upper()
    return upper if upper in FRONTEND_MODES else "MANUAL"


async def handle_mdp_command(
    device_id: str,
    *,
    target: str,
    cmd: str,
    params: Optional[Dict[str, Any]] = None,
    client_command_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle MDP envelope from the GCS (nav.*, cam.*, comms.*, acoustic.*, mission.*)."""
    params = params or {}
    catalog_id = PSATHYRELLA_DEVICE_ID
    registry_id = resolve_registry_device_id(device_id)
    runtime = get_runtime(catalog_id)
    autonomy = get_autonomy_controller(catalog_id)
    accepted_ms = int(time.time() * 1000)
    bridge = get_psathyrella_comms_bridge()
    bearer = bridge.select_bearer(catalog_id)

    device_registry_api._cleanup_expired_devices()  # noqa: SLF001
    device = device_registry_api._device_registry.get(registry_id, {})  # noqa: SLF001
    resolve_mdp_device_id(registry_id, device.get("extra") if isinstance(device.get("extra"), dict) else {})

    async def _forward_device_command(command: str, command_params: Dict[str, Any]) -> Dict[str, Any]:
        return await device_registry_api.send_device_command(
            device_id=registry_id,
            cmd=device_registry_api.DeviceCommand(
                command=command,
                params=command_params,
                timeout=8.0,
            ),
            use_mycorrhizae=False,
        )

    def _wrap(
        result: Dict[str, Any],
        *,
        state: str = "applied",
        detail: Optional[str] = None,
        response: Optional[Dict[str, Any]] = None,
        ack_bearer: Optional[str] = None,
    ) -> Dict[str, Any]:
        applied_ms = int(time.time() * 1000)
        out = dict(result)
        out.setdefault("target", target)
        out["ack"] = build_command_ack(
            cmd=cmd,
            state=state,
            client_command_id=client_command_id,
            bearer=ack_bearer or bearer,
            accepted_ms=accepted_ms,
            applied_ms=applied_ms if state == "applied" else None,
            detail=detail,
            device_response=response,
        )
        if response is not None and "response" not in out:
            out["response"] = response
        return out

    if cmd == "nav.thrust_vector":
        heading = float(params.get("heading", 0))
        magnitude = float(params.get("magnitude", 0))
        yaw_rate = float(params.get("yaw_rate", 0))
        runtime.commanded_vector = {
            "headingDeg": heading,
            "magnitudePct": magnitude,
            "yawRateDegS": yaw_rate,
        }
        vx = magnitude / 100.0
        response = await _forward_device_command(
            "psa_thruster_vector_set",
            {"vx": vx, "vy": 0.0, "yaw": yaw_rate / 45.0, "spin": 0.0},
        )
        return _wrap({"ok": True, "cmd": cmd, "response": response}, response=response)

    if cmd == "nav.thruster":
        thr_id = int(params.get("id", 0))
        throttle = float(params.get("throttle", 0))
        azimuth = float(params.get("azimuth", 0))
        if 0 <= thr_id < len(runtime.thrusters):
            runtime.thrusters[thr_id].throttle_pct = throttle
            runtime.thrusters[thr_id].azimuth_deg = azimuth
        pwm = int(1500 + (throttle / 100.0) * 400)
        motor_keys = [
            "motor_front_left",
            "motor_front_right",
            "motor_rear_left",
            "motor_rear_right",
        ]
        motors = {key: 1500 for key in motor_keys}
        if 0 <= thr_id < len(motor_keys):
            motors[motor_keys[thr_id]] = max(1100, min(1900, pwm))
        response = await _forward_device_command("psa_thruster_pwm_set", motors)
        return _wrap({"ok": True, "cmd": cmd, "response": response}, response=response)

    if cmd == "nav.all_stop":
        runtime.commanded_vector = {"headingDeg": 0, "magnitudePct": 0, "yawRateDegS": 0}
        for t in runtime.thrusters:
            t.throttle_pct = 0.0
        response = await _forward_device_command(
            "psa_thruster_vector_set",
            {"vx": 0.0, "vy": 0.0, "yaw": 0.0, "spin": 0.0},
        )
        return _wrap({"ok": True, "cmd": cmd, "response": response}, response=response)

    if cmd == "nav.set_mode":
        runtime.mode = _map_nav_mode(str(params.get("mode", "MANUAL")))
        return _wrap({"ok": True, "cmd": cmd, "mode": runtime.mode, "detail": "mode_stored_pending_mavlink"})

    if cmd == "nav.arm":
        runtime.armed = bool(params.get("armed", False))
        return _wrap({"ok": True, "cmd": cmd, "armed": runtime.armed})

    if cmd == "nav.add_waypoint":
        wp_id = str(params.get("id") or params.get("waypoint_id") or "")
        lat = float(params.get("lat", 0))
        lon = float(params.get("lon", 0))
        record_kwargs: Dict[str, Any] = {
            "latitude": lat,
            "longitude": lon,
            "metadata": {
                "label": params.get("label"),
                "loiter": params.get("loiter"),
            },
        }
        if wp_id:
            record_kwargs["waypoint_id"] = wp_id
        record = WaypointRecord(**record_kwargs)
        existing = autonomy.list_waypoints()
        existing.append(record)
        autonomy.replace_waypoints(existing)
        return _wrap({"ok": True, "cmd": cmd, "waypoint_id": record.waypoint_id})

    if cmd == "nav.clear_waypoints":
        autonomy.replace_waypoints([])
        return _wrap({"ok": True, "cmd": cmd})

    if cmd == "nav.goto":
        wp_id = str(params.get("id", ""))
        autonomy.state.active_waypoint_id = wp_id or None
        runtime.mode = "GUIDED"
        return _wrap({"ok": True, "cmd": cmd, "activeWaypointId": wp_id})

    if cmd == "nav.station_keep":
        runtime.mode = "STATION_KEEP"
        return _wrap({"ok": True, "cmd": cmd, "mode": runtime.mode})

    if cmd == "nav.fight_current":
        runtime.fight_current = bool(params.get("enabled", True))
        return _wrap({"ok": True, "cmd": cmd, "fightCurrent": runtime.fight_current})

    if cmd == "nav.camera_hold":
        bearing = params.get("bearing")
        runtime.camera_hold_bearing_deg = float(bearing) if bearing is not None else None
        return _wrap({"ok": True, "cmd": cmd, "cameraHoldBearingDeg": runtime.camera_hold_bearing_deg})

    if cmd == "cam.zoom":
        zoom = float(params.get("zoom", 1))
        runtime.camera_zoom = zoom
        response = await _forward_device_command("psa_camera_point", {"zoom": zoom})
        return _wrap({"ok": True, "cmd": cmd, "response": response}, response=response)

    if cmd == "cam.point":
        bearing = float(params.get("bearing", 0))
        tilt = float(params.get("tilt", 0))
        runtime.camera_bearing_deg = bearing
        runtime.camera_tilt_deg = tilt
        runtime.camera_active = True
        autonomy.point_camera(bearing_deg=bearing, pitch_deg=tilt)
        response = await _forward_device_command(
            "psa_camera_point",
            {"bearing_deg": bearing, "pitch_deg": tilt},
        )
        return _wrap({"ok": True, "cmd": cmd, "response": response}, response=response)

    if cmd == "comms.set_bearer":
        bearer_param = str(params.get("bearer", "")).lower()
        if bearer_param not in VALID_BEARERS:
            raise ValueError(f"bad_bearer:{bearer_param}")
        runtime.preferred_bearer = bearer_param
        bridge.set_bearer(catalog_id, bearer_param)
        return _wrap(
            {"ok": True, "cmd": cmd, "bearer": bearer_param},
            ack_bearer=bearer_param,
            detail="bearer_preference_set",
        )

    if cmd == "acoustic.set_gain":
        gain = float(params.get("gain_db", 0))
        gain = max(-12.0, min(48.0, gain))
        runtime.hydrophone_gain_db = gain
        response: Optional[Dict[str, Any]] = None
        try:
            response = await _forward_device_command("acoustic set_gain", {"gain_db": gain})
        except Exception as exc:  # noqa: BLE001
            logger.info("acoustic.set_gain device forward unavailable: %s", exc)
        return _wrap(
            {"ok": True, "cmd": cmd, "gainDb": gain, "response": response},
            response=response,
            detail="gain_stored" if response is None else "gain_applied",
        )

    if cmd == "mission.upload":
        plan = params.get("plan")
        if not isinstance(plan, dict) or not plan.get("id"):
            raise ValueError("mission.upload requires params.plan (MissionPlan)")
        record = await load_mission_plan(plan, device_id=catalog_id)
        executor = get_mission_executor(catalog_id)
        executor.load(record)
        runtime.active_mission_id = record.id
        runtime.comms_loss_policy = record.comms_loss_policy
        return _wrap(
            {
                "ok": True,
                "cmd": cmd,
                "missionId": record.id,
                "tasks": len(record.tasks),
            },
            detail="mission_loaded",
        )

    if cmd == "mission.abort":
        executor = get_mission_executor(catalog_id)
        executor.abort()
        runtime.active_mission_id = None
        if runtime.comms_loss_policy == "rtl":
            runtime.mode = "RTL"
        else:
            runtime.mode = "STATION_KEEP"
        return _wrap({"ok": True, "cmd": cmd, "mode": runtime.mode}, detail="mission_aborted")

    raise ValueError(f"unsupported_mdp_command:{cmd}")


async def handle_legacy_operator_command(device_id: str, operator_cmd: str) -> Dict[str, Any]:
    """Forward legacy operator strings (led, buzzer, hydrophone) to MycoBrain."""
    registry_id = resolve_registry_device_id(device_id)
    return await device_registry_api.send_device_command(
        device_id=registry_id,
        cmd=device_registry_api.DeviceCommand(command=operator_cmd.strip(), timeout=8.0),
        use_mycorrhizae=False,
    )
