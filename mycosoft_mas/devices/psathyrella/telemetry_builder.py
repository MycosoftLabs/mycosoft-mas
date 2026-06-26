"""Build BuoyTelemetry envelope matching website lib/psathyrella/contract.ts."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

from mycosoft_mas.devices.psathyrella.comms_bridge import get_psathyrella_comms_bridge
from mycosoft_mas.devices.psathyrella.constants import (
    PROJECT_OYSTER_ANCHOR,
    PSATHYRELLA_DEVICE_ID,
    PSATHYRELLA_REGISTRY_ID,
    resolve_mdp_device_id,
    resolve_registry_device_id,
)
from mycosoft_mas.devices.psathyrella.runtime_state import get_runtime, waypoints_for_telemetry

MYCOBRAIN_FALLBACK_URL = (os.getenv("MYCOBRAIN_SERVICE_URL") or "http://localhost:8003").rstrip("/")
DEVICE_STALE_SECONDS = int(os.getenv("DEVICE_STALE_SECONDS", "60"))
DEVICE_TTL_SECONDS = int(os.getenv("DEVICE_TTL_SECONDS", "120"))


def _num(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)) and value == value:
        return float(value)
    return None


def _map_bme(raw: Optional[Dict[str, Any]], *, default_label: str, default_address: str) -> Optional[Dict[str, Any]]:
    if not raw or not isinstance(raw, dict):
        return None
    return {
        "temperature": _num(raw.get("temperature") or raw.get("temperature_c") or raw.get("temp_c")),
        "humidity": _num(raw.get("humidity") or raw.get("humidity_pct") or raw.get("rh")),
        "pressure": _num(raw.get("pressure") or raw.get("pressure_hpa") or raw.get("p_hPa")),
        "gasResistance": _num(
            raw.get("gas_resistance")
            or raw.get("gas_resistance_ohm")
            or raw.get("gas_ohm")
            or raw.get("gas")
        ),
        "iaq": _num(raw.get("iaq") or raw.get("iaq_index")),
        "iaqAccuracy": _num(raw.get("iaq_accuracy") or raw.get("accuracy")),
        "co2Equivalent": _num(raw.get("co2_equivalent") or raw.get("co2eq")),
        "vocEquivalent": _num(raw.get("voc_equivalent") or raw.get("voc")),
        "present": raw.get("present") is not False,
        "address": raw.get("address") if isinstance(raw.get("address"), str) else default_address,
        "label": raw.get("label") if isinstance(raw.get("label"), str) else default_label,
    }


def _link_from_status(status: str, sensors_ok: bool) -> str:
    if sensors_ok:
        return "online"
    normalized = (status or "").lower()
    if normalized == "offline":
        return "offline"
    if normalized == "stale":
        return "stale"
    if normalized == "online":
        return "online"
    return "unknown"


def _parse_location(device: Dict[str, Any]) -> Tuple[Optional[float], Optional[float], str]:
    loc = device.get("location")
    lat: Optional[float] = None
    lon: Optional[float] = None
    if isinstance(loc, str) and "," in loc:
        parts = [p.strip() for p in loc.split(",", 1)]
        try:
            lat = float(parts[0])
            lon = float(parts[1])
        except (TypeError, ValueError):
            pass
    elif isinstance(loc, dict):
        lat = _num(loc.get("lat") or loc.get("latitude"))
        lon = _num(loc.get("lon") or loc.get("lng") or loc.get("longitude"))
    if lat is None or lon is None:
        lat = PROJECT_OYSTER_ANCHOR["lat"]
        lon = PROJECT_OYSTER_ANCHOR["lon"]
        return lat, lon, "site"
    return lat, lon, "site"


def _empty_thrusters() -> List[Dict[str, Any]]:
    labels = ["BOW-P", "BOW-S", "AFT-P", "AFT-S"]
    return [
        {
            "id": i,
            "label": labels[i],
            "throttlePct": 0,
            "azimuthDeg": 0,
            "currentA": None,
            "rpm": None,
            "faulted": False,
        }
        for i in range(4)
    ]


def _default_radios() -> List[Dict[str, Any]]:
    return [
        {"kind": kind, "connected": False, "rssiDbm": None, "latencyMs": None, "throughputKbps": None}
        for kind in ("ble", "cellular", "wifi", "lora")
    ]


def _vision_url(device_id: str, source: str) -> Optional[str]:
    env_key = f"PSATHYRELLA_{source.upper()}_STREAM_URL"
    configured = (os.getenv(env_key) or "").strip()
    return configured or None


async def _fetch_bme_from_mycobrain(
    base_url: str,
    mdp_device_id: str,
    headers: Optional[Dict[str, str]] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[str], bool]:
    """Return (bme_a, bme_b, timestamp_iso, ok)."""
    headers = headers or {}
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.post(
                f"{base_url.rstrip('/')}/devices/{mdp_device_id}/command",
                json={"command": {"cmd": "read_sensors"}},
                headers=headers,
            )
            if response.status_code != 200:
                return None, None, None, False
            payload = response.json()
            raw = payload.get("response") or ""
            if isinstance(raw, dict):
                sensors = raw.get("sensors") or raw.get("bme688") or raw
                if isinstance(sensors, dict):
                    a = sensors.get("bme688_1") or sensors.get("bme1") or (sensors.get("a") if "a" in sensors else None)
                    b = sensors.get("bme688_2") or sensors.get("bme2") or (sensors.get("b") if "b" in sensors else None)
                    if isinstance(sensors.get("bme688"), dict):
                        block = sensors["bme688"]
                        a = a or block.get("a")
                        b = b or block.get("b")
                    ts = payload.get("timestamp") or datetime.now(timezone.utc).isoformat()
                    return (
                        _map_bme(a if isinstance(a, dict) else None, default_label="BME688 A - I2C-1 AMB", default_address="0x77"),
                        _map_bme(b if isinstance(b, dict) else None, default_label="BME688 B - I2C-2 ENV", default_address="0x76"),
                        ts,
                        bool(a or b),
                    )
            text = str(raw)
            bme_a: Optional[Dict[str, Any]] = None
            bme_b: Optional[Dict[str, Any]] = None
            for line in text.splitlines():
                if "AMB addr=0x77" in line or '"a"' in line:
                    bme_a = _map_bme({"raw": line}, default_label="BME688 A - I2C-1 AMB", default_address="0x77")
                if "ENV addr=0x76" in line or '"b"' in line:
                    bme_b = _map_bme({"raw": line}, default_label="BME688 B - I2C-2 ENV", default_address="0x76")
            ts = payload.get("timestamp") or datetime.now(timezone.utc).isoformat()
            return bme_a, bme_b, ts, bool(bme_a or bme_b)
    except Exception:
        return None, None, None, False


def _extract_power(raw_telemetry: Dict[str, Any]) -> Dict[str, Any]:
    power = raw_telemetry.get("power") if isinstance(raw_telemetry.get("power"), dict) else {}
    battery_v = _num(power.get("battery_v") or raw_telemetry.get("battery_v"))
    solar_mv = _num(power.get("solar_mv") or raw_telemetry.get("solar_mv"))
    load_w = _num(power.get("load_w") or raw_telemetry.get("load_w"))
    soc = _num(power.get("battery_soc_pct") or raw_telemetry.get("battery_soc_pct"))
    solar_w = _num(power.get("solar_input_w") or raw_telemetry.get("solar_input_w"))
    if solar_w is None and solar_mv is not None:
        solar_w = round(solar_mv / 1000.0, 2)
    return {
        "solarInputW": solar_w,
        "panelTempC": _num(power.get("panel_temp_c")),
        "batterySocPct": soc,
        "batteryVoltage": battery_v,
        "loadW": load_w,
        "estRuntimeH": _num(power.get("est_runtime_h")),
        "sunRepositionSuggested": bool(power.get("sun_reposition_suggested", False)),
    }


async def build_buoy_telemetry(
    device_id: str,
    *,
    registry_snapshot: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Assemble BuoyTelemetry dict (camelCase) for the GCS contract.
    Uses real MycoBrain BME when reachable; other fields are honest null/standby.
    """
    from mycosoft_mas.core.routers import device_registry_api

    catalog_id = PSATHYRELLA_DEVICE_ID if device_id in (
        PSATHYRELLA_DEVICE_ID,
        PSATHYRELLA_REGISTRY_ID,
        resolve_registry_device_id(device_id),
    ) else device_id

    registry_id = resolve_registry_device_id(device_id)
    device_registry_api._cleanup_expired_devices()  # noqa: SLF001
    registry = registry_snapshot or device_registry_api._device_registry  # noqa: SLF001
    device = registry.get(registry_id) or registry.get(device_id) or {}

    status = device_registry_api._get_device_status(registry_id) if registry_id in registry else "unknown"  # noqa: SLF001

    extra = device.get("extra") if isinstance(device.get("extra"), dict) else {}
    mdp_id = resolve_mdp_device_id(registry_id, extra)

    base_url = MYCOBRAIN_FALLBACK_URL
    if device.get("host"):
        host = str(device["host"])
        port = int(device.get("port") or 8003)
        if host.startswith("http"):
            base_url = host.rstrip("/")
        else:
            base_url = f"http://{host}:{port}"

    headers: Dict[str, str] = {}
    api_key = os.getenv("MYCOBRAIN_SERVICE_FORWARD_API_KEY") or os.getenv("MYCOBRAIN_API_KEY")
    if api_key:
        headers["X-API-Key"] = api_key

    bme_a, bme_b, sensor_ts, sensors_ok = await _fetch_bme_from_mycobrain(base_url, mdp_id, headers)

    lat, lon, gps_lock = _parse_location(device)
    link = _link_from_status(status, sensors_ok)

    last_update_ms: Optional[int] = None
    if sensor_ts:
        try:
            ts = datetime.fromisoformat(sensor_ts.replace("Z", "+00:00"))
            last_update_ms = max(0, int((datetime.now(timezone.utc) - ts).total_seconds() * 1000))
        except (TypeError, ValueError):
            last_update_ms = None

    runtime = get_runtime(catalog_id)
    waypoints, active_wp = waypoints_for_telemetry(catalog_id)
    bridge = get_psathyrella_comms_bridge()
    comms_state = bridge.get_state(catalog_id)

    raw_telemetry: Dict[str, Any] = {}
    if device.get("telemetry") and isinstance(device["telemetry"], dict):
        raw_telemetry = device["telemetry"]
    elif extra.get("last_telemetry") and isinstance(extra["last_telemetry"], dict):
        raw_telemetry = extra["last_telemetry"]

    power = _extract_power(raw_telemetry)
    camera_url = _vision_url(catalog_id, "camera")

    thrusters = [
        {
            "id": t.id,
            "label": t.label,
            "throttlePct": t.throttle_pct,
            "azimuthDeg": t.azimuth_deg,
            "currentA": t.current_a,
            "rpm": t.rpm,
            "faulted": t.faulted,
        }
        for t in runtime.thrusters
    ]

    return {
        "deviceId": catalog_id,
        "link": link,
        "lastUpdateMsAgo": last_update_ms,
        "source": "field" if sensors_ok else (device.get("connection_type") or "mas"),
        "simulated": False,
        "pose": {
            "lat": lat,
            "lon": lon,
            "headingDeg": _num(raw_telemetry.get("heading_deg") or raw_telemetry.get("heading")),
            "speedKn": _num(raw_telemetry.get("speed_kn") or raw_telemetry.get("speed")),
            "depthM": _num(raw_telemetry.get("depth_m") or raw_telemetry.get("depth")),
            "gpsLock": gps_lock,
        },
        "bme": {"a": bme_a, "b": bme_b},
        "propulsion": {
            "thrusters": thrusters or _empty_thrusters(),
            "commandedVector": runtime.commanded_vector,
        },
        "autonomy": {
            "mode": runtime.mode,
            "armed": runtime.armed,
            "waypoints": waypoints,
            "activeWaypointId": active_wp,
            "cameraHoldBearingDeg": runtime.camera_hold_bearing_deg,
            "fightCurrent": runtime.fight_current,
        },
        "power": power,
        "comms": {
            "radios": _default_radios(),
            "acoustic": {
                "connected": bool(comms_state.get("bridge_enabled", False)),
                "carrierKhz": None,
                "snrDb": None,
                "rangeM": None,
                "lastPingMsAgo": None,
            },
            "hydrophone": {"levelDb": None, "peakBearingDeg": None, "bandHz": None},
            "bridgeActive": bool(comms_state.get("bridge_enabled", False)),
            "lastUplink": None,
        },
        "camera": {
            "active": runtime.camera_active and bool(camera_url),
            "streamUrl": camera_url,
            "zoom": runtime.camera_zoom,
            "bearingDeg": runtime.camera_bearing_deg,
            "tiltDeg": runtime.camera_tilt_deg,
        },
        "lidar": {
            "sweepDeg": None,
            "maxRangeM": 500,
            "contacts": [],
            "active": bool(_vision_url(catalog_id, "lidar")),
        },
        "radar": {
            "sweepDeg": None,
            "maxRangeM": 4000,
            "contacts": [],
            "active": bool(_vision_url(catalog_id, "radar")),
        },
        "bluesight": {
            "wifi": [],
            "active": bool(_vision_url(catalog_id, "wifi")),
        },
    }
