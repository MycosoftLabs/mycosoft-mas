"""MDP nav/cam command dispatch for Psathyrella GCS contract."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from mycosoft_mas.core.routers import device_registry_api
from mycosoft_mas.devices.psathyrella.autonomy import WaypointRecord
from mycosoft_mas.devices.psathyrella.constants import (
    PSATHYRELLA_DEVICE_ID,
    resolve_mdp_device_id,
    resolve_registry_device_id,
)
from mycosoft_mas.devices.psathyrella.runtime_state import (
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


def _map_nav_mode(mode: str) -> str:
    upper = (mode or "MANUAL").upper()
    return upper if upper in FRONTEND_MODES else "MANUAL"


async def handle_mdp_command(
    device_id: str,
    *,
    target: str,
    cmd: str,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Handle nav.* and cam.* MDP envelope from the GCS."""
    params = params or {}
    catalog_id = PSATHYRELLA_DEVICE_ID
    registry_id = resolve_registry_device_id(device_id)
    runtime = get_runtime(catalog_id)
    autonomy = get_autonomy_controller(catalog_id)

    device_registry_api._cleanup_expired_devices()  # noqa: SLF001
    device = device_registry_api._device_registry.get(registry_id, {})  # noqa: SLF001
    mdp_path = resolve_mdp_device_id(registry_id, device.get("extra") if isinstance(device.get("extra"), dict) else {})

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
        return {"ok": True, "cmd": cmd, "target": target, "response": response}

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
        return {"ok": True, "cmd": cmd, "target": target, "response": response}

    if cmd == "nav.all_stop":
        runtime.commanded_vector = {"headingDeg": 0, "magnitudePct": 0, "yawRateDegS": 0}
        for t in runtime.thrusters:
            t.throttle_pct = 0.0
        response = await _forward_device_command(
            "psa_thruster_vector_set",
            {"vx": 0.0, "vy": 0.0, "yaw": 0.0, "spin": 0.0},
        )
        return {"ok": True, "cmd": cmd, "target": target, "response": response}

    if cmd == "nav.set_mode":
        runtime.mode = _map_nav_mode(str(params.get("mode", "MANUAL")))
        return {"ok": True, "cmd": cmd, "mode": runtime.mode, "detail": "mode_stored_pending_mavlink"}

    if cmd == "nav.arm":
        runtime.armed = bool(params.get("armed", False))
        return {"ok": True, "cmd": cmd, "armed": runtime.armed}

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
        return {"ok": True, "cmd": cmd, "waypoint_id": record.waypoint_id}

    if cmd == "nav.clear_waypoints":
        autonomy.replace_waypoints([])
        return {"ok": True, "cmd": cmd}

    if cmd == "nav.goto":
        wp_id = str(params.get("id", ""))
        autonomy.state.active_waypoint_id = wp_id or None
        runtime.mode = "GUIDED"
        return {"ok": True, "cmd": cmd, "activeWaypointId": wp_id}

    if cmd == "nav.station_keep":
        runtime.mode = "STATION_KEEP"
        return {"ok": True, "cmd": cmd, "mode": runtime.mode}

    if cmd == "nav.fight_current":
        runtime.fight_current = bool(params.get("enabled", True))
        return {"ok": True, "cmd": cmd, "fightCurrent": runtime.fight_current}

    if cmd == "nav.camera_hold":
        bearing = params.get("bearing")
        runtime.camera_hold_bearing_deg = float(bearing) if bearing is not None else None
        return {"ok": True, "cmd": cmd, "cameraHoldBearingDeg": runtime.camera_hold_bearing_deg}

    if cmd == "cam.zoom":
        zoom = float(params.get("zoom", 1))
        runtime.camera_zoom = zoom
        response = await _forward_device_command("psa_camera_point", {"zoom": zoom})
        return {"ok": True, "cmd": cmd, "target": target, "response": response}

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
        return {"ok": True, "cmd": cmd, "target": target, "response": response}

    raise ValueError(f"unsupported_mdp_command:{cmd}")


async def handle_legacy_operator_command(device_id: str, operator_cmd: str) -> Dict[str, Any]:
    """Forward legacy operator strings (led, buzzer, hydrophone) to MycoBrain."""
    registry_id = resolve_registry_device_id(device_id)
    return await device_registry_api.send_device_command(
        device_id=registry_id,
        cmd=device_registry_api.DeviceCommand(command=operator_cmd.strip(), timeout=8.0),
        use_mycorrhizae=False,
    )
