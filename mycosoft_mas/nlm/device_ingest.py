"""
NLM live device ingest — MAS device registry + MycoBrain/MDP.

Real data only. If no registered device or no telemetry, returns empty state.
Maps device_id, sensor_id, and protocol metadata for NLM/FormSpace UI agents.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

MYCOBRAIN_DEFAULT_PORT = int(os.getenv("MYCOBRAIN_PORT", "8003"))
TELEMETRY_TIMEOUT = float(os.getenv("NLM_INGEST_TELEMETRY_TIMEOUT", "8.0"))


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        # Heuristic: ms vs s
        ts = float(value)
        if ts > 1e12:
            ts = ts / 1000.0
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    if isinstance(value, str) and value.strip():
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _age_seconds(ts: Optional[datetime], now: Optional[datetime] = None) -> Optional[float]:
    if ts is None:
        return None
    now = now or _utcnow()
    return max(0.0, (now - ts).total_seconds())


def _mycobrain_headers() -> Dict[str, str]:
    key = os.getenv("MYCOBRAIN_SERVICE_FORWARD_API_KEY") or os.getenv("MYCOBRAIN_API_KEY")
    if key:
        return {"X-API-Key": key}
    return {}


def _device_base_url(device: Dict[str, Any]) -> str:
    host = str(device.get("host") or "").strip()
    port = int(device.get("port") or MYCOBRAIN_DEFAULT_PORT)
    if host.startswith("http://") or host.startswith("https://"):
        return host.rstrip("/")
    if device.get("connection_type") == "cloudflare":
        return f"https://{host}"
    return f"http://{host}:{port}"


def _protocol_metadata(device: Dict[str, Any], mdp_path_id: Optional[str] = None) -> Dict[str, Any]:
    extra = device.get("extra") if isinstance(device.get("extra"), dict) else {}
    return {
        "connection_type": device.get("connection_type") or "lan",
        "ingestion_source": device.get("ingestion_source") or "serial",
        "board_type": device.get("board_type") or "unknown",
        "firmware_version": device.get("firmware_version") or "unknown",
        "host": device.get("host"),
        "port": device.get("port"),
        "mdp_path_id": mdp_path_id or extra.get("mdp_device_id") or extra.get("primary_serial_device_id"),
        "mdp_device_ids_on_host": extra.get("mdp_device_ids_on_host"),
        "network_source": "mycobrain",
        "protocol_family": "mdp",
    }


def _sensor_rows_from_declared(sensors: Any) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if isinstance(sensors, list):
        for s in sensors:
            if isinstance(s, str) and s.strip():
                rows.append(
                    {
                        "sensor_id": s.strip(),
                        "channels": [],
                        "last_sample_at": None,
                        "sample_age_seconds": None,
                        "has_data": False,
                        "source": "registry_declared",
                    }
                )
            elif isinstance(s, dict) and (s.get("sensor_id") or s.get("id")):
                sid = str(s.get("sensor_id") or s.get("id"))
                rows.append(
                    {
                        "sensor_id": sid,
                        "channels": list(s.get("channels") or []),
                        "last_sample_at": s.get("last_sample_at"),
                        "sample_age_seconds": s.get("sample_age_seconds"),
                        "has_data": bool(s.get("has_data")),
                        "source": "registry_declared",
                    }
                )
    return rows


def _extract_sensors_from_telemetry(
    telemetry: Dict[str, Any],
    now: datetime,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Parse MycoBrain / field-operator telemetry into sensor rows. No invention."""
    sensors: List[Dict[str, Any]] = []
    last_sample_at: Optional[str] = None

    # Common shapes: {sensors: {...}}, {readings: {...}}, {telemetry: {...}}, flat BME keys
    candidates: List[Tuple[str, Any]] = []
    for key in ("sensors", "readings", "channels", "telemetry", "data"):
        block = telemetry.get(key)
        if isinstance(block, dict):
            for sid, payload in block.items():
                candidates.append((str(sid), payload))
        elif isinstance(block, list):
            for item in block:
                if isinstance(item, dict):
                    sid = str(item.get("sensor_id") or item.get("id") or item.get("name") or "")
                    if sid:
                        candidates.append((sid, item))

    # Flat environmental keys → one synthetic sensor_id only when values present
    flat_env = {}
    for k in (
        "temperature",
        "humidity",
        "pressure",
        "gas_resistance",
        "voc",
        "co2",
        "iaq",
        "voltage",
        "impedance",
        "accel_x",
        "accel_y",
        "accel_z",
    ):
        if k in telemetry and telemetry[k] is not None:
            flat_env[k] = telemetry[k]
    if flat_env and not candidates:
        candidates.append(("environmental", flat_env))

    for sid, payload in candidates:
        channels: List[str] = []
        sample_ts = None
        has_data = False
        if isinstance(payload, dict):
            sample_ts = (
                _parse_iso(payload.get("timestamp"))
                or _parse_iso(payload.get("ts"))
                or _parse_iso(payload.get("last_sample_at"))
                or _parse_iso(telemetry.get("timestamp"))
                or _parse_iso(telemetry.get("ts"))
            )
            for ck, cv in payload.items():
                if ck in ("timestamp", "ts", "last_sample_at", "sensor_id", "id", "name", "unit"):
                    continue
                if cv is not None:
                    channels.append(ck)
                    has_data = True
        elif payload is not None:
            has_data = True
            channels = ["value"]
            sample_ts = _parse_iso(telemetry.get("timestamp")) or _parse_iso(telemetry.get("ts"))

        ts_iso = sample_ts.isoformat() if sample_ts else None
        if ts_iso:
            last_sample_at = ts_iso
        sensors.append(
            {
                "sensor_id": sid,
                "channels": channels,
                "last_sample_at": ts_iso,
                "sample_age_seconds": _age_seconds(sample_ts, now),
                "has_data": has_data,
                "source": "live_telemetry",
            }
        )

    return sensors, last_sample_at


async def _fetch_mycobrain_telemetry(
    device_id: str,
    device: Dict[str, Any],
    client: httpx.AsyncClient,
) -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[str]]:
    """
    Returns (telemetry_body, mdp_path_id, error_message).
    Uses same MDP resolve rules as device_registry_api.
    """
    from mycosoft_mas.core.routers.device_registry_api import (
        _resolve_mycobrain_mdp_http_id,
        _is_agent_api,
        _fetch_agent_telemetry,
    )

    base_url = _device_base_url(device)
    headers = _mycobrain_headers()
    try:
        if _is_agent_api(device):
            body = await _fetch_agent_telemetry(client, base_url)
            path_id = str((device.get("extra") or {}).get("mdp_device_id") or device_id)
            if isinstance(body, dict):
                return body, path_id, None
            return None, path_id, "agent_telemetry_non_object"

        path_id = await _resolve_mycobrain_mdp_http_id(device_id, device, base_url, client)
        response = await client.get(
            f"{base_url}/devices/{path_id}/telemetry",
            headers=headers,
        )
        if response.status_code != 200:
            return None, path_id, f"telemetry_http_{response.status_code}"
        body = response.json()
        if isinstance(body, dict):
            return body, path_id, None
        return None, path_id, "telemetry_non_object"
    except Exception as exc:
        logger.debug("NLM ingest telemetry failed for %s: %s", device_id, exc)
        return None, None, str(exc)


async def build_live_ingest(
    *,
    include_offline: bool = False,
    fetch_telemetry: bool = True,
) -> Dict[str, Any]:
    """
    Build live ingest snapshot for NLM UI.

    Empty when no devices or no sensor data — never invents waveforms.
    """
    from mycosoft_mas.core.routers.device_registry_api import (
        _list_devices_impl,
        _get_device_status,
    )

    now = _utcnow()
    listing = await _list_devices_impl(status=None, include_offline=include_offline)
    registry_devices: List[Dict[str, Any]] = listing.get("devices") or []

    out_devices: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []

    async with httpx.AsyncClient(timeout=TELEMETRY_TIMEOUT) as client:
        for device in registry_devices:
            device_id = str(device.get("device_id") or "")
            if not device_id:
                continue
            status = device.get("status") or _get_device_status(device_id)
            sensors = _sensor_rows_from_declared(device.get("sensors"))
            mdp_path_id = None
            telemetry: Optional[Dict[str, Any]] = None
            last_sample_at = None

            if fetch_telemetry and status in ("online", "stale"):
                telemetry, mdp_path_id, err = await _fetch_mycobrain_telemetry(
                    device_id, device, client
                )
                if err:
                    errors.append({"device_id": device_id, "error": err})
                if telemetry:
                    live_sensors, last_sample_at = _extract_sensors_from_telemetry(telemetry, now)
                    if live_sensors:
                        # Prefer live sensor rows; keep declared-only as has_data=false if not overlapping
                        live_ids = {s["sensor_id"] for s in live_sensors}
                        sensors = live_sensors + [
                            s for s in sensors if s["sensor_id"] not in live_ids
                        ]

            has_any_data = any(bool(s.get("has_data")) for s in sensors)
            out_devices.append(
                {
                    "device_id": device_id,
                    "display_name": device.get("device_display_name")
                    or device.get("device_name")
                    or device_id,
                    "device_name": device.get("device_name"),
                    "role": device.get("device_role") or "standalone",
                    "status": status,
                    "protocol": _protocol_metadata(device, mdp_path_id=mdp_path_id),
                    "sensors": sensors,
                    "sensor_count": len(sensors),
                    "has_sensor_data": has_any_data,
                    "last_sample_at": last_sample_at,
                    "last_seen": device.get("last_seen"),
                    "nmf_id": None,
                    "frame_id": None,
                    "capabilities": list(device.get("capabilities") or []),
                }
            )

    with_data = [d for d in out_devices if d.get("has_sensor_data")]
    empty = len(out_devices) == 0 or len(with_data) == 0

    message = None
    if len(out_devices) == 0:
        message = (
            "No devices registered in MAS device registry. "
            "MycoBrain must heartbeat to POST /api/devices/heartbeat."
        )
    elif empty:
        message = (
            "Devices are registered but no live sensor samples are available. "
            "Showing device/protocol mapping only — no synthetic waveforms."
        )

    return {
        "status": "ok",
        "empty": empty,
        "model_kind": "nature_learning_model",
        "bound_to_ollama": False,
        "timestamp": now.isoformat(),
        "count": len(out_devices),
        "devices_with_data": len(with_data),
        "devices": out_devices,
        "errors": errors,
        "message": message,
        "sources": {
            "device_registry": "/api/devices",
            "protocol": "mdp",
            "mycobrain_service": True,
        },
    }


async def build_device_protocol_map() -> Dict[str, Any]:
    """Network/protocol mapping without requiring telemetry samples."""
    snap = await build_live_ingest(include_offline=True, fetch_telemetry=False)
    mapping = []
    for d in snap.get("devices") or []:
        mapping.append(
            {
                "device_id": d["device_id"],
                "display_name": d["display_name"],
                "role": d["role"],
                "status": d["status"],
                "protocol": d["protocol"],
                "sensor_ids": [s["sensor_id"] for s in (d.get("sensors") or [])],
            }
        )
    return {
        "status": "ok",
        "empty": len(mapping) == 0,
        "count": len(mapping),
        "mapping": mapping,
        "timestamp": snap.get("timestamp"),
        "message": snap.get("message") if len(mapping) == 0 else None,
        "model_kind": "nature_learning_model",
    }
