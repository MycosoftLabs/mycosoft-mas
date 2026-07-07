"""Forward Psathyrella MDP nav commands to the Jetson propulsion agent (:8788)."""

from __future__ import annotations

import asyncio
import logging
import os
from json import JSONDecodeError
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
        "nav.az_zero",
        "nav.esc_calibrate",
        "nav.pwm_raw",
        "nav.set_mode",
        "nav.station_keep",
        "nav.fight_current",
    }
)

_propulsion_http_client: Optional[httpx.AsyncClient] = None
_propulsion_client_lock = asyncio.Lock()


def _request_timeout(timeout_s: float) -> httpx.Timeout:
    connect = min(2.0, max(0.5, timeout_s))
    return httpx.Timeout(timeout_s, connect=connect)


async def _get_propulsion_http_client() -> httpx.AsyncClient:
    """Reuse one keep-alive client for Jetson :8788 — avoids ~1s TCP SYN RTO per command."""
    global _propulsion_http_client
    async with _propulsion_client_lock:
        if _propulsion_http_client is None or _propulsion_http_client.is_closed:
            _propulsion_http_client = httpx.AsyncClient(
                limits=httpx.Limits(
                    max_keepalive_connections=4,
                    max_connections=8,
                    keepalive_expiry=60.0,
                ),
                timeout=_request_timeout(8.0),
            )
        return _propulsion_http_client


async def _post_with_connect_retry(
    client: httpx.AsyncClient,
    url: str,
    *,
    json: Dict[str, Any],
    headers: Dict[str, str],
    timeout_s: float,
) -> httpx.Response:
    timeout = _request_timeout(timeout_s)
    last_exc: Optional[BaseException] = None
    for attempt in range(2):
        try:
            return await client.post(url, json=json, headers=headers, timeout=timeout)
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            last_exc = exc
            if attempt == 0:
                await asyncio.sleep(0.05)
                continue
            raise
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("post_with_connect_retry: unreachable")


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


def _propulsion_base_url(device: Dict[str, Any]) -> str:
    extra = device.get("extra") or {}
    propulsion_url = extra.get("propulsion_agent_url") or extra.get("jetson_propulsion_url")
    if isinstance(propulsion_url, str) and propulsion_url.strip():
        return propulsion_url.rstrip("/")

    override = (os.getenv("PSATHYRELLA_PROPULSION_AGENT_URL") or "").strip()
    if override:
        return override.rstrip("/")

    jetson_ip = (os.getenv("JETSON_IP") or "192.168.0.123").strip()
    propulsion_port = int(
        os.getenv("PSATHYRELLA_PROPULSION_AGENT_PORT")
        or os.getenv("PSATHYRELLA_JETSON_PROPULSION_PORT")
        or "8788"
    )
    host = str(device.get("host") or "").strip()

    if host.startswith("http://") or host.startswith("https://"):
        scheme, remainder = host.split("://", 1)
        hostname = remainder.split(":", 1)[0].rstrip("/")
        return f"{scheme}://{hostname}:{propulsion_port}"
    if host:
        return f"http://{host}:{propulsion_port}"
    return f"http://{jetson_ip}:{propulsion_port}"


def _is_agent_device(device: Dict[str, Any]) -> bool:
    return device_registry_api._is_agent_api(device)  # noqa: SLF001


def _decode_json_response(response: httpx.Response, path: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        payload = response.json()
    except JSONDecodeError:
        body = response.text[:2000]
        logger.warning("Invalid JSON from propulsion agent %s: %s", path, body)
        return {"ok": False, "raw": body}, f"agent_invalid_json:{path}"
    if not isinstance(payload, dict):
        return {"ok": False, "raw": response.text[:2000]}, f"agent_non_object_json:{path}"
    if payload.get("ok") is False:
        return payload, f"agent_rejected:{path}"
    return payload, None


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
    http_failures: list[tuple[str, int]] = []
    client = await _get_propulsion_http_client()
    for path, body in (
        ("/command", mdp_body),
        ("/side-b/command", {"command": cmd, "params": params, "ack_requested": True}),
        ("/side-a/command", {"command": cmd, "params": params, "ack_requested": True}),
    ):
        try:
            response = await _post_with_connect_retry(
                client,
                f"{base_url}{path}",
                json=body,
                headers=headers,
                timeout_s=timeout_s,
            )
            if response.status_code != 200:
                http_failures.append((path, response.status_code))
                continue
            payload, err = _decode_json_response(response, path)
            return payload, err
        except Exception as exc:  # noqa: BLE001
            logger.debug("MDP forward %s failed: %s", path, exc)
            continue
    if http_failures and all(status == 404 for _, status in http_failures):
        return None, "agent_no_command_endpoint"
    if http_failures:
        path, status = http_failures[-1]
        return None, f"agent_http_{status}:{path}"
    return None, "agent_unreachable"


async def propulsion_agent_reachable(
    device: Optional[Dict[str, Any]] = None,
    *,
    timeout_s: float = 1.5,
) -> bool:
    """True when the Jetson :8788 propulsion agent responds to /health."""
    base_url = _propulsion_base_url(device or {})
    try:
        client = await _get_propulsion_http_client()
        response = await client.get(
            f"{base_url}/health",
            timeout=_request_timeout(timeout_s),
        )
        if response.status_code != 200:
            return False
        payload = response.json()
        return isinstance(payload, dict) and payload.get("status") == "ok"
    except Exception:  # noqa: BLE001
        return False


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

    if cmd in NAV_MDP_COMMANDS:
        base_url = _propulsion_base_url(device)
        payload, err = await _post_mdp_payload(
            base_url,
            target=target,
            cmd=cmd,
            params=params,
            timeout_s=timeout_s,
        )
        return {"relay": "jetson_mdp", "base_url": base_url, "response": payload, "error": err}

    if device:
        base_url = _device_base_url(device)
        if _is_agent_device(device):
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
