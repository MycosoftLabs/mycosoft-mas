"""Build BuoyTelemetry envelope matching website lib/psathyrella/contract.ts."""

from __future__ import annotations

import os
import re
import json
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
from mycosoft_mas.devices.psathyrella.runtime_state import (
    derive_contact_state,
    get_runtime,
    last_contact_ms_ago,
    waypoints_for_telemetry,
)

MYCOBRAIN_FALLBACK_URL = (os.getenv("MYCOBRAIN_SERVICE_URL") or "http://localhost:8003").rstrip("/")
DEVICE_STALE_SECONDS = int(os.getenv("DEVICE_STALE_SECONDS", "60"))
DEVICE_TTL_SECONDS = int(os.getenv("DEVICE_TTL_SECONDS", "120"))
M_TO_FT = 3.28084
MS_TO_KN = 1.94384
C_TO_F_OFFSET = 32.0
C_TO_F_SCALE = 9.0 / 5.0


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


def _parse_bme_from_status_text(text: str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], bool]:
    """Parse MycoBrain `status` / telemetry raw text (matches website sensors route)."""
    if not text:
        return None, None, False

    def _status_slot(label: str, default_address: str, default_label: str) -> Optional[Dict[str, Any]]:
        match = re.search(
            rf"{label}:\s+present=(YES|NO)\s+addr=([^\s]+)\s+begin=(OK|FAIL)\s+sub=(OK|FAIL)",
            text,
            re.I,
        )
        if not match:
            return None
        slot: Dict[str, Any] = {
            "present": match.group(1).upper() == "YES",
            "address": match.group(2) or default_address,
            "label": default_label,
        }
        live = re.search(
            rf"{label} addr={re.escape(default_address)}.*?T=([\d.]+)C RH=([\d.]+)% P=([\d.]+)hPa.*?Gas=(\d+)Ohm IAQ=([\d.]+) acc=(\d+).*?CO2eq=([\d.]+) VOC=([\d.]+)",
            text,
            re.I | re.S,
        )
        if live:
            slot.update(
                {
                    "temperature": float(live.group(1)),
                    "humidity": float(live.group(2)),
                    "pressure": float(live.group(3)),
                    "gas_resistance": float(live.group(4)),
                    "iaq": float(live.group(5)),
                    "iaq_accuracy": float(live.group(6)),
                    "co2_equivalent": float(live.group(7)),
                    "voc_equivalent": float(live.group(8)),
                }
            )
        return _map_bme(slot, default_label=default_label, default_address=default_address)

    bme_a = _status_slot("AMB", "0x77", "BME688 A - I2C-1 AMB")
    bme_b = _status_slot("ENV", "0x76", "BME688 B - I2C-2 ENV")

    # MDP JSON telemetry lines mixed into serial output
    for line in text.splitlines():
        trimmed = line.strip()
        if not trimmed.startswith("{") and "{" in trimmed:
            trimmed = trimmed[trimmed.index("{"):]
        if not trimmed.startswith("{"):
            continue
        try:
            record = json.loads(trimmed)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if not isinstance(record, dict):
            continue
        block = record.get("bme688")
        if isinstance(block, dict):
            if block.get("a"):
                bme_a = _map_bme(
                    block["a"] if isinstance(block["a"], dict) else None,
                    default_label="BME688 A - I2C-1 AMB",
                    default_address="0x77",
                )
            if block.get("b"):
                bme_b = _map_bme(
                    block["b"] if isinstance(block["b"], dict) else None,
                    default_label="BME688 B - I2C-2 ENV",
                    default_address="0x76",
                )
        if record.get("bme1"):
            bme_a = _map_bme(
                record["bme1"] if isinstance(record["bme1"], dict) else None,
                default_label="BME688 A - I2C-1 AMB",
                default_address="0x77",
            )
        if record.get("bme2"):
            bme_b = _map_bme(
                record["bme2"] if isinstance(record["bme2"], dict) else None,
                default_label="BME688 B - I2C-2 ENV",
                default_address="0x76",
            )

    sensors_ok = bool(
        (bme_a and bme_a.get("present"))
        or (bme_b and bme_b.get("present"))
        or (bme_a and bme_a.get("temperature") is not None)
        or (bme_b and bme_b.get("temperature") is not None)
    )
    return bme_a, bme_b, sensors_ok


def _deep_merge(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _iter_json_records(text: str) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    if not text:
        return records
    for line in text.splitlines():
        trimmed = line.strip()
        if not trimmed.startswith("{") and "{" in trimmed:
            trimmed = trimmed[trimmed.index("{"):]
        if not trimmed.startswith("{"):
            continue
        try:
            record = json.loads(trimmed)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def _collect_merged_payload(raw_text: str, telemetry_block: Dict[str, Any]) -> Dict[str, Any]:
    """Merge structured telemetry dict + MDP JSON lines from serial output."""
    merged: Dict[str, Any] = {}
    if isinstance(telemetry_block, dict):
        for key in (
            "gps",
            "pose",
            "power",
            "propulsion",
            "comms",
            "camera",
            "lidar",
            "radar",
            "bluesight",
            "hydrophone",
            "thrusters",
            "links",
            "sensors",
        ):
            block = telemetry_block.get(key)
            if isinstance(block, dict):
                merged = _deep_merge(merged, {key: block})
        for record in _iter_json_records(str(telemetry_block.get("raw") or "")):
            merged = _deep_merge(merged, record)
    for record in _iter_json_records(raw_text):
        merged = _deep_merge(merged, record)
    return merged


def _speed_to_kn(value: Any, unit: Optional[str] = None) -> Optional[float]:
    speed = _num(value)
    if speed is None:
        return None
    normalized = (unit or "kn").lower().replace(" ", "")
    if normalized in {"m/s", "mps", "ms"}:
        return round(speed * MS_TO_KN, 2)
    if normalized in {"km/h", "kmh", "kph"}:
        return round(speed * 0.539957, 2)
    return round(speed, 2)


def _depth_to_m(value: Any, unit: Optional[str] = None) -> Optional[float]:
    depth = _num(value)
    if depth is None:
        return None
    normalized = (unit or "m").lower()
    if normalized in {"ft", "feet", "foot"}:
        return round(depth / M_TO_FT, 2)
    return round(depth, 2)


def _temp_c(value: Any, unit: Optional[str] = None) -> Optional[float]:
    temp = _num(value)
    if temp is None:
        return None
    normalized = (unit or "c").lower()
    if normalized in {"f", "fahrenheit", "degf"}:
        return round((temp - C_TO_F_OFFSET) / C_TO_F_SCALE, 2)
    return round(temp, 2)


def _gps_lock_from_payload(payload: Dict[str, Any], fallback: str) -> str:
    gps = payload.get("gps") if isinstance(payload.get("gps"), dict) else {}
    pose = payload.get("pose") if isinstance(payload.get("pose"), dict) else {}
    lock = (
        gps.get("lock")
        or gps.get("gps_lock")
        or pose.get("gpsLock")
        or pose.get("gps_lock")
    )
    if isinstance(lock, str) and lock.strip():
        normalized = lock.strip().lower()
        if normalized in {"locked", "drift", "unavailable", "manual", "site"}:
            return normalized
    sats = _num(gps.get("satellites") or gps.get("sats"))
    if sats is not None:
        return "locked" if sats >= 4 else "drift"
    if gps.get("lat") is not None or gps.get("latitude") is not None:
        return "locked"
    return fallback


def _extract_pose(
    payload: Dict[str, Any],
    device: Dict[str, Any],
    lat: Optional[float],
    lon: Optional[float],
    gps_lock: str,
) -> Dict[str, Any]:
    gps = payload.get("gps") if isinstance(payload.get("gps"), dict) else {}
    pose = payload.get("pose") if isinstance(payload.get("pose"), dict) else {}
    lat_val = _num(gps.get("lat") or gps.get("latitude") or pose.get("lat") or pose.get("latitude")) or lat
    lon_val = _num(gps.get("lon") or gps.get("lng") or gps.get("longitude") or pose.get("lon") or pose.get("longitude")) or lon
    heading = _num(
        pose.get("heading_deg")
        or pose.get("headingDeg")
        or pose.get("heading")
        or gps.get("heading_deg")
        or gps.get("heading")
        or gps.get("cog")
    )
    speed_unit = pose.get("speed_unit") or gps.get("speed_unit")
    speed = _speed_to_kn(
        pose.get("speed_kn")
        or pose.get("speedKn")
        or pose.get("speed")
        or gps.get("speed_kn")
        or gps.get("sog"),
        str(speed_unit) if speed_unit else "kn",
    )
    depth_unit = pose.get("depth_unit") or gps.get("depth_unit")
    depth = _depth_to_m(
        pose.get("depth_m")
        or pose.get("depthM")
        or pose.get("depth")
        or gps.get("depth_m"),
        str(depth_unit) if depth_unit else "m",
    )
    lock = _gps_lock_from_payload(payload, gps_lock)
    return {
        "lat": lat_val,
        "lon": lon_val,
        "headingDeg": heading,
        "speedKn": speed,
        "depthM": depth,
        "gpsLock": lock,
    }


def _merge_power_state(payload: Dict[str, Any], raw_telemetry: Dict[str, Any]) -> Dict[str, Any]:
    power = _extract_power_from_registry(raw_telemetry) if raw_telemetry else {
        "solarInputW": None,
        "panelTempC": None,
        "batterySocPct": None,
        "batteryVoltage": None,
        "loadW": None,
        "estRuntimeH": None,
        "sunRepositionSuggested": False,
    }
    block = payload.get("power") if isinstance(payload.get("power"), dict) else {}
    if not block and isinstance(payload.get("solar"), dict):
        block = {"solar_mv": payload["solar"].get("intake_mv"), **payload["solar"]}

    solar_w = _num(block.get("solar_input_w") or block.get("solarInputW") or block.get("solar_w"))
    solar_mv = _num(block.get("solar_mv") or block.get("solarMv"))
    if solar_w is None and solar_mv is not None:
        solar_w = round(solar_mv / 1000.0, 2)

    panel_temp = _temp_c(
        block.get("panel_temp_c") or block.get("panelTempC") or block.get("panel_temp_f"),
        "f" if block.get("panel_temp_f") is not None else "c",
    )

    return {
        "solarInputW": solar_w if solar_w is not None else power["solarInputW"],
        "panelTempC": panel_temp if panel_temp is not None else power["panelTempC"],
        "batterySocPct": _num(block.get("battery_soc_pct") or block.get("batterySocPct")) or power["batterySocPct"],
        "batteryVoltage": _num(block.get("battery_v") or block.get("batteryVoltage")) or power["batteryVoltage"],
        "loadW": _num(block.get("load_w") or block.get("loadW")) or power["loadW"],
        "estRuntimeH": _num(block.get("est_runtime_h") or block.get("estRuntimeH")) or power["estRuntimeH"],
        "sunRepositionSuggested": bool(
            block.get("sun_reposition_suggested", power["sunRepositionSuggested"])
        ),
    }


def _radio_link(kind: str, data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    data = data if isinstance(data, dict) else {}
    return {
        "kind": kind,
        "connected": bool(data.get("connected") or data.get("online") or data.get("link_up")),
        "rssiDbm": _num(data.get("rssi_dbm") or data.get("rssiDbm") or data.get("rssi")),
        "latencyMs": _num(data.get("latency_ms") or data.get("latencyMs")),
        "throughputKbps": _num(data.get("throughput_kbps") or data.get("throughputKbps")),
    }


def _extract_comms(
    payload: Dict[str, Any],
    comms_state: Dict[str, Any],
    last_update_ms: Optional[int],
    *,
    runtime_gain_db: Optional[float] = None,
    satellite_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    comms = payload.get("comms") if isinstance(payload.get("comms"), dict) else {}
    links = comms.get("links") if isinstance(comms.get("links"), dict) else {}
    if not links and isinstance(payload.get("links"), dict):
        links = payload["links"]

    radios = [
        _radio_link("ble", links.get("ble") or comms.get("ble")),
        _radio_link("cellular", links.get("cellular") or links.get("lte") or comms.get("cellular")),
        _radio_link("wifi", links.get("wifi") or comms.get("wifi")),
        _radio_link("lora", links.get("lora") or comms.get("lora")),
    ]

    acoustic_block = comms.get("acoustic") if isinstance(comms.get("acoustic"), dict) else {}
    hydro_block = comms.get("hydrophone") if isinstance(comms.get("hydrophone"), dict) else {}
    if not hydro_block and isinstance(payload.get("hydrophone"), dict):
        hydro_block = payload["hydrophone"]

    carrier_hz = _num(acoustic_block.get("carrier_hz") or acoustic_block.get("carrierHz"))
    carrier_khz = round(carrier_hz / 1000.0, 2) if carrier_hz is not None else _num(acoustic_block.get("carrier_khz"))

    band = hydro_block.get("band_hz") or hydro_block.get("bandHz")
    band_hz = None
    if isinstance(band, dict):
        lo = _num(band.get("lo") or band.get("low"))
        hi = _num(band.get("hi") or band.get("high"))
        if lo is not None and hi is not None:
            band_hz = {"lo": lo, "hi": hi}

    gain_db = _num(hydro_block.get("gain_db") or hydro_block.get("gainDb"))
    if gain_db is None and runtime_gain_db is not None:
        gain_db = runtime_gain_db

    spectrum_raw = hydro_block.get("spectrum")
    spectrum: Optional[List[float]] = None
    if isinstance(spectrum_raw, list) and spectrum_raw:
        spectrum = [_num(v) or 0.0 for v in spectrum_raw]

    sat_block = comms.get("satellite") if isinstance(comms.get("satellite"), dict) else {}
    sat = satellite_state or {}
    satellite = {
        "bearer": sat_block.get("bearer") or sat.get("bearer"),
        "connected": bool(sat_block.get("connected") or sat.get("connected", False)),
        "rssiDbm": _num(sat_block.get("rssi_dbm") or sat_block.get("rssiDbm") or sat.get("rssiDbm")),
        "credits": _num(sat_block.get("credits") or sat.get("credits")),
        "mtQueued": int(sat_block.get("mt_queued") or sat_block.get("mtQueued") or sat.get("mtQueued") or 0),
        "moQueued": int(sat_block.get("mo_queued") or sat_block.get("moQueued") or sat.get("moQueued") or 0),
        "lastContactMsAgo": _num(
            sat_block.get("last_contact_ms_ago")
            or sat_block.get("lastContactMsAgo")
            or sat.get("lastContactMsAgo")
        ),
        "nextPassEtaS": _num(
            sat_block.get("next_pass_eta_s") or sat_block.get("nextPassEtaS") or sat.get("nextPassEtaS")
        ),
    }

    uplink_summary = comms.get("last_uplink_summary") or comms.get("lastUplinkSummary")
    return {
        "radios": radios,
        "acoustic": {
            "connected": bool(
                acoustic_block.get("connected")
                or comms_state.get("bridge_enabled", False)
            ),
            "carrierKhz": carrier_khz,
            "snrDb": _num(acoustic_block.get("snr_db") or acoustic_block.get("snrDb")),
            "rangeM": _num(acoustic_block.get("range_m") or acoustic_block.get("rangeM")),
            "lastPingMsAgo": _num(acoustic_block.get("last_ping_ms_ago") or acoustic_block.get("lastPingMsAgo")),
        },
        "hydrophone": {
            "levelDb": _num(hydro_block.get("level_db") or hydro_block.get("levelDb")),
            "peakBearingDeg": _num(hydro_block.get("peak_bearing_deg") or hydro_block.get("peakBearingDeg")),
            "bandHz": band_hz,
            "gainDb": gain_db,
            "spectrum": spectrum,
        },
        "satellite": satellite,
        "bridgeActive": bool(comms_state.get("bridge_enabled", False)),
        "lastUplink": {
            "atMsAgo": last_update_ms,
            "summary": str(uplink_summary) if uplink_summary else None,
        },
    }


def _parse_contacts(raw: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    contacts: List[Dict[str, Any]] = []
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        entry: Dict[str, Any] = {
            "id": str(item.get("id") or f"contact-{idx}"),
            "bearingDeg": _num(item.get("bearing_deg") or item.get("bearingDeg")) or 0.0,
            "rangeM": _num(item.get("range_m") or item.get("rangeM")) or 0.0,
            "kind": str(item.get("kind") or "unknown"),
            "strength": _num(item.get("strength")) or 0.0,
            "label": item.get("label"),
            "classifiedAs": item.get("classified_as") or item.get("classifiedAs"),
        }
        coc = item.get("chain_of_custody") or item.get("chainOfCustody")
        if isinstance(coc, dict) and coc.get("hash"):
            entry["chainOfCustody"] = {
                "hash": str(coc.get("hash")),
                "merkleRoot": str(coc.get("merkle_root") or coc.get("merkleRoot") or ""),
                "avaniVerified": bool(coc.get("avani_verified") or coc.get("avaniVerified", False)),
            }
        contacts.append(entry)
    return contacts


def _extract_scope(payload: Dict[str, Any], key: str, *, default_range_m: float, stream_active: bool) -> Dict[str, Any]:
    block = payload.get(key) if isinstance(payload.get(key), dict) else {}
    return {
        "sweepDeg": _num(block.get("sweep_deg") or block.get("sweepDeg")),
        "maxRangeM": _num(block.get("max_range_m") or block.get("maxRangeM")) or default_range_m,
        "contacts": _parse_contacts(block.get("contacts")),
        "active": bool(block.get("active")) or stream_active,
    }


def _apply_propulsion_from_payload(runtime, payload: Dict[str, Any]) -> None:
    propulsion = payload.get("propulsion") if isinstance(payload.get("propulsion"), dict) else {}
    thr_list = propulsion.get("thrusters")
    if not isinstance(thr_list, list):
        thr_list = payload.get("thrusters")
    if not isinstance(thr_list, list):
        return
    for entry in thr_list:
        if not isinstance(entry, dict):
            continue
        thr_id = entry.get("id")
        if thr_id is None:
            continue
        try:
            idx = int(thr_id)
        except (TypeError, ValueError):
            continue
        if 0 <= idx < len(runtime.thrusters):
            runtime.thrusters[idx].throttle_pct = _num(entry.get("throttle_pct") or entry.get("throttlePct")) or 0.0
            runtime.thrusters[idx].azimuth_deg = _num(entry.get("azimuth_deg") or entry.get("azimuthDeg")) or 0.0
            runtime.thrusters[idx].current_a = _num(entry.get("current_a") or entry.get("currentA"))
            runtime.thrusters[idx].rpm = _num(entry.get("rpm"))
            runtime.thrusters[idx].faulted = bool(entry.get("faulted", False))


async def _fetch_mycobrain_bundle(
    base_url: str,
    mdp_device_id: str,
    headers: Optional[Dict[str, str]] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[str], bool, Dict[str, Any]]:
    """Return (bme_a, bme_b, timestamp_iso, sensors_ok, merged_payload)."""
    headers = headers or {}
    base = base_url.rstrip("/")
    merged_payload: Dict[str, Any] = {}
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            telemetry_res = await client.get(
                f"{base}/devices/{mdp_device_id}/telemetry",
                headers=headers,
            )
            if telemetry_res.status_code == 200:
                payload = telemetry_res.json()
                telemetry = payload.get("telemetry") if isinstance(payload.get("telemetry"), dict) else {}
                raw = telemetry.get("raw") or payload.get("response") or ""
                merged_payload = _collect_merged_payload(str(raw), telemetry)
                if telemetry.get("bme1") and isinstance(telemetry["bme1"], dict):
                    merged_payload.setdefault("bme688", {})["a"] = telemetry["bme1"]
                if telemetry.get("bme2") and isinstance(telemetry["bme2"], dict):
                    merged_payload.setdefault("bme688", {})["b"] = telemetry["bme2"]
                if isinstance(raw, str) and raw.strip():
                    bme_a, bme_b, sensors_ok = _parse_bme_from_status_text(raw)
                    ts = payload.get("timestamp") or datetime.now(timezone.utc).isoformat()
                    if sensors_ok or bme_a or bme_b or merged_payload:
                        return bme_a, bme_b, ts, sensors_ok, merged_payload

            response = await client.post(
                f"{base}/devices/{mdp_device_id}/command",
                json={"command": "status"},
                headers=headers,
            )
            if response.status_code != 200:
                return None, None, None, False, merged_payload
            payload = response.json()
            raw = payload.get("response") or ""
            if isinstance(raw, dict):
                sensors = raw.get("sensors") or raw.get("bme688") or raw
                merged_payload = _deep_merge(merged_payload, raw if isinstance(raw, dict) else {})
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
                        merged_payload,
                    )
            text = str(raw)
            merged_payload = _collect_merged_payload(text, {})
            bme_a, bme_b, sensors_ok = _parse_bme_from_status_text(text)
            ts = payload.get("timestamp") or datetime.now(timezone.utc).isoformat()
            return bme_a, bme_b, ts, sensors_ok, merged_payload
    except Exception:
        return None, None, None, False, merged_payload


async def _fetch_bme_from_mycobrain(
    base_url: str,
    mdp_device_id: str,
    headers: Optional[Dict[str, str]] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[str], bool]:
    """Return (bme_a, bme_b, timestamp_iso, ok). Back-compat wrapper."""
    bme_a, bme_b, ts, ok, _payload = await _fetch_mycobrain_bundle(base_url, mdp_device_id, headers)
    return bme_a, bme_b, ts, ok


def _extract_power_from_registry(raw_telemetry: Dict[str, Any]) -> Dict[str, Any]:
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

    raw_telemetry: Dict[str, Any] = {}
    if device.get("telemetry") and isinstance(device["telemetry"], dict):
        raw_telemetry = device["telemetry"]
    elif extra.get("last_telemetry") and isinstance(extra["last_telemetry"], dict):
        raw_telemetry = extra["last_telemetry"]

    bme_a, bme_b, sensor_ts, sensors_ok, mycobrain_payload = await _fetch_mycobrain_bundle(
        base_url, mdp_id, headers
    )
    if raw_telemetry:
        mycobrain_payload = _deep_merge(mycobrain_payload, raw_telemetry)

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
    _apply_propulsion_from_payload(runtime, mycobrain_payload)
    waypoints, active_wp = waypoints_for_telemetry(catalog_id)
    bridge = get_psathyrella_comms_bridge()
    comms_state = bridge.get_state(catalog_id)
    satellite_state = bridge.get_satellite_state(catalog_id)
    satellite_state["mtQueued"] = comms_state.get("mt_queued", satellite_state.get("mtQueued", 0))
    satellite_state["moQueued"] = comms_state.get("mo_queued", satellite_state.get("moQueued", 0))
    if runtime.preferred_bearer in {"iridium", "starlink"}:
        satellite_state["bearer"] = runtime.preferred_bearer

    power = _merge_power_state(mycobrain_payload, raw_telemetry)
    camera_url = _vision_url(catalog_id, "camera")
    camera_block = (
        mycobrain_payload.get("camera") if isinstance(mycobrain_payload.get("camera"), dict) else {}
    )

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

    pose = _extract_pose(mycobrain_payload, device, lat, lon, gps_lock)
    comms = _extract_comms(
        mycobrain_payload,
        comms_state,
        last_update_ms,
        runtime_gain_db=runtime.hydrophone_gain_db,
        satellite_state=satellite_state,
    )
    rf_up = any(r.get("connected") for r in comms.get("radios", []) if r.get("kind") in {"ble", "cellular", "wifi", "lora"})
    sat = comms.get("satellite") or {}
    contact_state = derive_contact_state(
        rf_connected=rf_up,
        sat_connected=bool(sat.get("connected")),
        sat_last_contact_ms_ago=_num(sat.get("lastContactMsAgo")),
    )
    contact_ms = last_contact_ms_ago(
        last_update_ms if rf_up else None,
        _num(sat.get("lastContactMsAgo")),
    )
    lidar = _extract_scope(
        mycobrain_payload,
        "lidar",
        default_range_m=500,
        stream_active=bool(_vision_url(catalog_id, "lidar")),
    )
    radar = _extract_scope(
        mycobrain_payload,
        "radar",
        default_range_m=4000,
        stream_active=bool(_vision_url(catalog_id, "radar")),
    )
    bluesight_block = (
        mycobrain_payload.get("bluesight")
        if isinstance(mycobrain_payload.get("bluesight"), dict)
        else {}
    )

    return {
        "deviceId": catalog_id,
        "link": link,
        "lastUpdateMsAgo": last_update_ms,
        "source": "field" if sensors_ok else (device.get("connection_type") or "mas"),
        "simulated": False,
        "contactState": contact_state,
        "lastContactMsAgo": contact_ms,
        "pose": pose,
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
            "commsLossPolicy": runtime.comms_loss_policy,
            "activeMissionId": runtime.active_mission_id,
        },
        "power": power,
        "comms": comms,
        "camera": {
            "active": runtime.camera_active and bool(camera_url or camera_block.get("stream_url")),
            "streamUrl": camera_url or camera_block.get("stream_url") or camera_block.get("streamUrl"),
            "zoom": _num(camera_block.get("zoom")) or runtime.camera_zoom,
            "bearingDeg": _num(camera_block.get("bearing_deg") or camera_block.get("bearingDeg"))
            or runtime.camera_bearing_deg,
            "tiltDeg": _num(camera_block.get("tilt_deg") or camera_block.get("tiltDeg"))
            or runtime.camera_tilt_deg,
        },
        "lidar": lidar,
        "radar": radar,
        "bluesight": {
            "wifi": _parse_contacts(bluesight_block.get("wifi")),
            "active": bool(bluesight_block.get("active")) or bool(_vision_url(catalog_id, "wifi")),
        },
        "peers": [],
        "mesh": {"selfId": catalog_id, "packets": [], "channel": "psathyrella"},
    }
