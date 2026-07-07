"""MDP nav/cam/comms/acoustic/mission command dispatch for Psathyrella GCS contract."""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, Optional

from mycosoft_mas.core.routers import device_registry_api
from mycosoft_mas.devices.psathyrella.autonomy import WaypointRecord
from mycosoft_mas.devices.psathyrella.comms_bridge import get_psathyrella_comms_bridge
from mycosoft_mas.devices.psathyrella.constants import (
    PSATHYRELLA_DEFAULT_BEARER,
    PSATHYRELLA_DEVICE_ID,
    resolve_public_device_id,
    resolve_mdp_device_id,
    resolve_registry_device_id,
)
from mycosoft_mas.devices.psathyrella.jetson_forward import (
    apply_thruster_feedback,
    forward_mdp_command,
    propulsion_agent_reachable,
)
from mycosoft_mas.devices.psathyrella.mission_executor import get_mission_executor, load_mission_plan
from mycosoft_mas.devices.psathyrella.runtime_state import (
    VALID_BEARERS,
    derive_contact_state,
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

RF_CONTACT_BEARERS = frozenset({"ble", "cellular", "wifi", "lora"})

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


def _ensure_psathyrella_comms_defaults(
    catalog_id: str,
    runtime: Any,
    bridge: Any,
) -> None:
    """Persist bench bearer so contactState is not derived as dark after MAS restart."""
    default_raw = os.getenv("PSATHYRELLA_DEFAULT_BEARER")
    if default_raw is None:
        default = PSATHYRELLA_DEFAULT_BEARER
    else:
        default = default_raw.strip().lower()
    if not default or default not in VALID_BEARERS:
        return
    if runtime.preferred_bearer is None:
        runtime.preferred_bearer = default
    bridge_state = bridge.get_state(catalog_id)
    if not bridge_state.get("preferred_bearer") and runtime.preferred_bearer:
        bridge.set_bearer(catalog_id, runtime.preferred_bearer)


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
    catalog_id = resolve_public_device_id(device_id) or PSATHYRELLA_DEVICE_ID
    registry_id = resolve_registry_device_id(
        device_id,
        set(device_registry_api._device_registry.keys()),  # noqa: SLF001
    )
    runtime = get_runtime(catalog_id)
    autonomy = get_autonomy_controller(catalog_id)
    accepted_ms = int(time.time() * 1000)
    bridge = get_psathyrella_comms_bridge()
    _ensure_psathyrella_comms_defaults(catalog_id, runtime, bridge)
    bearer = bridge.select_bearer(catalog_id)

    device_registry_api._cleanup_expired_devices()  # noqa: SLF001
    device = device_registry_api._device_registry.get(registry_id, {})  # noqa: SLF001
    resolve_mdp_device_id(registry_id, device.get("extra") if isinstance(device.get("extra"), dict) else {})

    def _effective_bearer() -> Optional[str]:
        bridge_pref = bridge.get_state(catalog_id).get("preferred_bearer")
        return runtime.preferred_bearer or bridge_pref or bridge.select_bearer(catalog_id)

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

    def _contact_state_now() -> str:
        sat = bridge.get_satellite_state(catalog_id)
        active_bearer = _effective_bearer()
        bench_rf_via_jetson = os.getenv("PSATHYRELLA_BENCH_RF_VIA_JETSON", "1") == "1"
        rf_connected = active_bearer in RF_CONTACT_BEARERS and (
            device.get("status") == "online"
            or bool(device)
            or (bench_rf_via_jetson and active_bearer in {"wifi", "cellular"})
        )
        return derive_contact_state(
            rf_connected=rf_connected,
            sat_connected=bool(sat.get("connected")),
            sat_last_contact_ms_ago=sat.get("lastContactMsAgo"),
        )

    def _maybe_queue_mt(payload: Dict[str, Any], *, ack_bearer: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if _contact_state_now() != "dark":
            return None
        bridge.enqueue_mt_command(
            catalog_id,
            {"target": target, "cmd": cmd, "params": params, "clientCommandId": client_command_id},
            bearer=bridge.select_bearer(catalog_id),
            priority=0,
        )
        return _wrap(
            {"ok": True, "cmd": cmd, "queued": True},
            state="sent",
            detail="queued for next pass",
            ack_bearer=ack_bearer or bridge.select_bearer(catalog_id),
        )

    def _relay_error(response: Optional[Dict[str, Any]]) -> Optional[str]:
        if not isinstance(response, dict):
            return None
        error = response.get("error")
        if isinstance(error, str) and error.strip():
            return error.strip()
        return None

    if cmd == "nav.thrust_vector":
        queued = None
        if _contact_state_now() == "dark":
            if not await propulsion_agent_reachable(device):
                queued = _maybe_queue_mt(
                    {"heading": params.get("heading"), "magnitude": params.get("magnitude")}
                )
        if queued:
            return queued
        heading = float(params.get("heading", 0))
        magnitude = float(params.get("magnitude", 0))
        yaw_rate = float(params.get("yaw_rate", 0))
        runtime.commanded_vector = {
            "headingDeg": heading,
            "magnitudePct": magnitude,
            "yawRateDegS": yaw_rate,
        }
        response = await forward_mdp_command(
            registry_id,
            target=target,
            cmd=cmd,
            params={"heading": heading, "magnitude": magnitude, "yaw_rate": yaw_rate},
        )
        apply_thruster_feedback(runtime, response)
        relay_err = _relay_error(response)
        if relay_err:
            return _wrap(
                {"ok": False, "cmd": cmd, "response": response},
                state="failed",
                detail=relay_err,
                response=response,
            )
        return _wrap({"ok": True, "cmd": cmd, "response": response}, response=response)

    if cmd == "nav.thruster":
        thr_id = int(params.get("id", 0))
        throttle = float(params.get("throttle", 0))
        azimuth = float(params.get("azimuth", 0))
        throttle = max(-100.0, min(100.0, throttle))
        azimuth = azimuth % 360.0
        if 0 <= thr_id < len(runtime.thrusters):
            runtime.thrusters[thr_id].throttle_pct = throttle
            runtime.thrusters[thr_id].azimuth_deg = azimuth
        mdp_params = {"id": thr_id, "throttle": int(throttle), "azimuth": int(azimuth)}
        response = await forward_mdp_command(
            registry_id,
            target=target,
            cmd=cmd,
            params=mdp_params,
        )
        apply_thruster_feedback(runtime, response)
        relay_err = _relay_error(response)
        if relay_err:
            return _wrap(
                {"ok": False, "cmd": cmd, "response": response},
                state="failed",
                detail=relay_err,
                response=response,
            )
        return _wrap({"ok": True, "cmd": cmd, "response": response}, response=response)

    if cmd == "nav.thruster_azimuth":
        thr_id = int(params.get("id", params.get("motorId", 0)))
        rate = params.get("rate")
        if rate is not None:
            rate_pct = max(-100.0, min(100.0, float(rate)))
            mdp_params = {"id": thr_id, "rate": rate_pct}
        else:
            azimuth = float(params.get("azimuth", params.get("azimuthDeg", 0))) % 360.0
            if 0 <= thr_id < len(runtime.thrusters):
                runtime.thrusters[thr_id].azimuth_deg = azimuth
            mdp_params = {"id": thr_id, "azimuth": int(azimuth)}
        response = await forward_mdp_command(
            registry_id,
            target=target,
            cmd="nav.thruster_azimuth",
            params=mdp_params,
        )
        apply_thruster_feedback(runtime, response)
        relay_err = _relay_error(response)
        if relay_err:
            return _wrap(
                {"ok": False, "cmd": cmd, "response": response},
                state="failed",
                detail=relay_err,
                response=response,
            )
        return _wrap({"ok": True, "cmd": cmd, "response": response}, response=response)

    if cmd == "nav.az_zero":
        mdp_params: Dict[str, Any] = {}
        if params.get("id") is not None:
            thr_id = int(params["id"])
            mdp_params["id"] = thr_id
            if 0 <= thr_id < len(runtime.thrusters):
                runtime.thrusters[thr_id].azimuth_deg = 0.0
        else:
            for t in runtime.thrusters:
                t.azimuth_deg = 0.0
        response = await forward_mdp_command(
            registry_id,
            target=target,
            cmd=cmd,
            params=mdp_params,
        )
        apply_thruster_feedback(runtime, response)
        relay_err = _relay_error(response)
        if relay_err:
            return _wrap(
                {"ok": False, "cmd": cmd, "response": response},
                state="failed",
                detail=relay_err,
                response=response,
            )
        nested = response.get("response") if isinstance(response, dict) else None
        detail = nested.get("detail") if isinstance(nested, dict) else None
        return _wrap(
            {"ok": True, "cmd": cmd, "response": response},
            response=response,
            detail=detail,
        )

    if cmd == "nav.esc_calibrate":
        mdp_params = {k: v for k, v in params.items() if k in {"id", "dry_run", "hold_s"}}
        response = await forward_mdp_command(
            registry_id,
            target=target,
            cmd=cmd,
            params=mdp_params,
            timeout_s=30.0,
        )
        relay_err = _relay_error(response)
        if relay_err:
            return _wrap(
                {"ok": False, "cmd": cmd, "response": response},
                state="failed",
                detail=relay_err,
                response=response,
            )
        nested = response.get("response") if isinstance(response, dict) else None
        detail = nested.get("detail") if isinstance(nested, dict) else "esc_calibrate"
        return _wrap(
            {"ok": True, "cmd": cmd, "response": response},
            response=response,
            detail=detail,
        )

    if cmd == "nav.all_stop":
        runtime.commanded_vector = {"headingDeg": 0, "magnitudePct": 0, "yawRateDegS": 0}
        for t in runtime.thrusters:
            t.throttle_pct = 0.0
            t.azimuth_deg = 0.0
        response = await forward_mdp_command(
            registry_id,
            target=target,
            cmd=cmd,
            params={},
        )
        apply_thruster_feedback(runtime, response)
        relay_err = _relay_error(response)
        if relay_err:
            return _wrap(
                {"ok": False, "cmd": cmd, "response": response},
                state="failed",
                detail=relay_err,
                response=response,
            )
        return _wrap({"ok": True, "cmd": cmd, "response": response}, response=response)

    if cmd == "nav.pwm_raw":
        channel = int(params.get("channel", -1))
        pulse_us = max(1000.0, min(2000.0, float(params.get("us", 1500))))
        response = await forward_mdp_command(
            registry_id,
            target=target,
            cmd=cmd,
            params={"channel": channel, "us": pulse_us},
        )
        relay_err = _relay_error(response)
        if relay_err:
            return _wrap(
                {
                    "ok": False,
                    "cmd": cmd,
                    "channel": channel,
                    "pulse_us": pulse_us,
                    "response": response,
                },
                state="failed",
                detail=relay_err,
                response=response,
            )
        return _wrap(
            {
                "ok": True,
                "cmd": cmd,
                "channel": channel,
                "pulse_us": pulse_us,
                "response": response,
            },
            response=response,
            detail=f"ch{channel}={int(pulse_us)}us",
        )

    if cmd == "nav.set_mode":
        runtime.mode = _map_nav_mode(str(params.get("mode", "MANUAL")))
        return _wrap({"ok": True, "cmd": cmd, "mode": runtime.mode, "detail": "mode_stored_pending_mavlink"})

    if cmd == "nav.arm":
        armed = bool(params.get("armed", False))
        runtime.armed = armed
        response = await forward_mdp_command(
            registry_id,
            target=target,
            cmd=cmd,
            params={"armed": armed},
        )
        relay_err = _relay_error(response)
        if relay_err:
            return _wrap(
                {"ok": False, "cmd": cmd, "armed": runtime.armed, "response": response},
                state="failed",
                detail=relay_err,
                response=response,
            )
        return _wrap(
            {"ok": True, "cmd": cmd, "armed": runtime.armed, "response": response},
            response=response,
            detail="arm_interlock_forwarded",
        )

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
    """Forward legacy operator strings (led, buzzer, hydrophone, gps) to MycoBrain."""
    registry_id = resolve_registry_device_id(
        device_id,
        set(device_registry_api._device_registry.keys()),  # noqa: SLF001
    )
    normalized = operator_cmd.strip().lower()
    if normalized.startswith("psa_gps_passthrough") or normalized.startswith("gps passthrough"):
        return await device_registry_api.send_device_command(
            device_id=registry_id,
            cmd=device_registry_api.DeviceCommand(command="psa_gps_passthrough", timeout=8.0),
            use_mycorrhizae=False,
        )
    return await device_registry_api.send_device_command(
        device_id=registry_id,
        cmd=device_registry_api.DeviceCommand(command=operator_cmd.strip(), timeout=8.0),
        use_mycorrhizae=False,
    )
