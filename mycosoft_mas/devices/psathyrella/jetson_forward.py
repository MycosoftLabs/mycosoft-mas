"""Forward Psathyrella MDP nav commands to Jetson field agent (:8787) or MycoBrain gateway."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional, Tuple

import httpx

from mycosoft_mas.core.routers import device_registry_api

logger = logging.getLogger(__name__)

NAV_MDP_COMMANDS = frozenset(
    {
        "nav.thruster",
        "nav.thruster_azimuth",
        "nav.thrust_vector",
        "nav.all_stop",
        "nav.arm",
        "nav.set_mode",
        "nav.station_keep",
        "nav.fight_current",
    }
)


def _mycobrain_forward_headers() -> Dict[str, str]:
    key = os.getenv("MYCOBRAIN_SERVICE_FORWARD_API_KEY") or os.getenv("MYCOBRAIN_API_KEY")
    if key:
        return {"X-API-Key": key}
    return {}


def _device_base_url(device: Dict[str, Any]) -> str:
    extra = device.get("extra") or {}
    agent_url = extra.get("agent_url")
    if isinstance(agent_url, str) and agent_url.strip():
        return agent_url.rstrip("/")

    override = (os.getenv("PSATHYRELLA_JETSON_AGENT_URL") or os.getenv("JETSON_AGENT_URL") or "").strip()
    if override:
        return override.rstrip("/")

    jetson_ip = (os.getenv("JETSON_IP") or "192.168.0.123").strip()
    jetson_port = int(os.getenv("JETSON_AGENT_PORT") or os.getenv("PSATHYRELLA_JETSON_PORT") or "8787")
    host = device.get("host", "")
    port = int(device.get("port") or 8003)

    if host.startswith("http://") or host.startswith("https://"):
        return host.rstrip("/")
    if device_registry_api._is_agent_api(device):  # noqa: SLF001
        if host:
            return f"http://{host}:{port}"
        return f"http://{jetson_ip}:{jetson_port}"
    if host:
        return f"http://{host}:{port}"
    return f"http://{jetson_ip}:{jetson_port}"


def _is_agent_device(device: Dict[str, Any]) -> bool:
    return device_registry_api._is_agent_api(device)  # noqa: SLF001


async def _post_mdp_payload(
    base_url: str,
    *,
    target: str,
    cmd: str,
    params: Dict[str, Any],
    timeout_s: float,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Try agent MDP `/command` then legacy operator endpoints."""
    mdp_body = {
        "target": target,
        "cmd": cmd,
        "params": params,
        "ack_requested": True,
        "timeout_ms": int(timeout_s * 1000),
    }
    headers = _mycobrain_forward_headers()
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        for path, body in (
            ("/command", mdp_body),
            ("/side-b/command", {"command": cmd, "params": params, "ack_requested": True}),
            ("/side-a/command", {"command": cmd, "params": params, "ack_requested": True}),
        ):
            try:
                response = await client.post(f"{base_url}{path}", json=body, headers=headers)
                if response.status_code != 200:
                    continue
                payload = response.json()
                if isinstance(payload, dict) and payload.get("ok") is False:
                    return payload, f"agent_rejected:{path}"
                return payload, None
            except Exception as exc:  # noqa: BLE001
                logger.debug("MDP forward %s failed: %s", path, exc)
                continue
    return None, "agent_unreachable"


async def forward_mdp_command(
    registry_id: str,
    *,
    target: str,
    cmd: str,
    params: Optional[Dict[str, Any]] = None,
    timeout_s: float = 8.0,
) -> Dict[str, Any]:
    """
    Forward GCS MDP envelope to Jetson/on-device agent when registered, else registry proxy.

    Returns a dict suitable for command_handler ack `device_response`.
    """
    params = params or {}
    device_registry_api._cleanup_expired_devices()  # noqa: SLF001
    device = device_registry_api._device_registry.get(registry_id, {})  # noqa: SLF001

    if device:
        base_url = _device_base_url(device)
        if _is_agent_device(device) or cmd in NAV_MDP_COMMANDS:
            payload, err = await _post_mdp_payload(
                base_url,
                target=target,
                cmd=cmd,
                params=params,
                timeout_s=timeout_s,
            )
            if payload is not None:
                return {"relay": "jetson_mdp", "base_url": base_url, "response": payload, "error": err}
            if err and err != "agent_unreachable":
                return {"relay": "jetson_mdp", "base_url": base_url, "response": None, "error": err}

    # Registry HTTP proxy (MycoBrain :8003 or agent :8787) with MDP cmd as operator command name.
    try:
        result = await device_registry_api.send_device_command(
            device_id=registry_id,
            cmd=device_registry_api.DeviceCommand(
                command=cmd,
                params={**params, "target": target},
                timeout=timeout_s,
            ),
            use_mycorrhizae=False,
        )
        return {"relay": "device_registry", "response": result}
    except Exception as exc:  # noqa: BLE001
        logger.warning("MDP forward via registry failed for %s %s: %s", registry_id, cmd, exc)
        return {"relay": "none", "response": None, "error": str(exc)}


def apply_thruster_feedback(runtime, device_response: Optional[Dict[str, Any]]) -> None:
    """Merge ESC/servo telemetry from Jetson/MDP response into runtime thrusters."""
    if not device_response:
        return
    nested = device_response.get("response") if isinstance(device_response, dict) else None
    candidates = [device_response]
    if isinstance(nested, dict):
        candidates.append(nested)
        inner = nested.get("response") or nested.get("payload") or nested.get("result")
        if isinstance(inner, dict):
            candidates.append(inner)
        if isinstance(inner, dict) and isinstance(inner.get("payload"), dict):
            candidates.append(inner["payload"])

    for block in candidates:
        if not isinstance(block, dict):
            continue
        propulsion = block.get("propulsion")
        if not isinstance(propulsion, dict):
            propulsion = block
        thr_list = propulsion.get("thrusters") if isinstance(propulsion, dict) else None
        if not isinstance(thr_list, list):
            thr_list = block.get("thrusters")
        if not isinstance(thr_list, list):
            continue
        for entry in thr_list:
            if not isinstance(entry, dict):
                continue
            try:
                idx = int(entry.get("id", -1))
            except (TypeError, ValueError):
                continue
            if not (0 <= idx < len(runtime.thrusters)):
                continue
            thr = runtime.thrusters[idx]
            if entry.get("throttle_pct") is not None or entry.get("throttlePct") is not None:
                thr.throttle_pct = float(entry.get("throttle_pct") or entry.get("throttlePct") or 0)
            if entry.get("azimuth_deg") is not None or entry.get("azimuthDeg") is not None:
                thr.azimuth_deg = float(entry.get("azimuth_deg") or entry.get("azimuthDeg") or 0)
            if entry.get("current_a") is not None or entry.get("currentA") is not None:
                thr.current_a = float(entry.get("current_a") or entry.get("currentA"))
            if entry.get("rpm") is not None:
                thr.rpm = float(entry.get("rpm"))
            if "faulted" in entry:
                thr.faulted = bool(entry.get("faulted"))
