"""Parse NMEA GGA/RMC sentences from MycoBrain serial into GPS contract blocks."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _nmea_degrees(value: str, hemisphere: str) -> Optional[float]:
    if not value:
        return None
    try:
        if "." not in value:
            return None
        dot = value.index(".")
        degrees = float(value[: dot - 2])
        minutes = float(value[dot - 2 :])
        decimal = degrees + minutes / 60.0
    except (TypeError, ValueError):
        return None
    if hemisphere.upper() in {"S", "W"}:
        decimal = -decimal
    return round(decimal, 7)


def _parse_gga(parts: List[str]) -> Dict[str, Any]:
    if len(parts) < 10:
        return {}
    lat = _nmea_degrees(parts[2], parts[3]) if parts[2] else None
    lon = _nmea_degrees(parts[4], parts[5]) if parts[4] else None
    fix_quality = parts[6] if len(parts) > 6 else "0"
    sats_raw = parts[7] if len(parts) > 7 else ""
    try:
        satellites = int(sats_raw) if sats_raw else 0
    except ValueError:
        satellites = 0
    lock = "unavailable"
    if fix_quality in {"1", "2", "4", "5", "6"}:
        lock = "locked" if satellites >= 4 else "drift"
    elif fix_quality == "0":
        lock = "drift" if satellites >= 1 else "unavailable"
    return {
        "lat": lat,
        "lon": lon,
        "satellites": satellites,
        "lock": lock,
    }


def _parse_rmc(parts: List[str]) -> Dict[str, Any]:
    if len(parts) < 10:
        return {}
    status = parts[2] if len(parts) > 2 else ""
    lat = _nmea_degrees(parts[3], parts[4]) if len(parts) > 4 and parts[3] else None
    lon = _nmea_degrees(parts[5], parts[6]) if len(parts) > 6 and parts[5] else None
    sog_raw = parts[7] if len(parts) > 7 else ""
    cog_raw = parts[8] if len(parts) > 8 else ""
    try:
        sog = float(sog_raw) if sog_raw else None
    except ValueError:
        sog = None
    try:
        cog = float(cog_raw) if cog_raw else None
    except ValueError:
        cog = None
    block: Dict[str, Any] = {}
    if status.upper() == "A":
        block["lock"] = "locked"
    if lat is not None:
        block["lat"] = lat
    if lon is not None:
        block["lon"] = lon
    if sog is not None:
        block["speed_kn"] = round(sog, 2)
        block["sog"] = round(sog, 2)
    if cog is not None:
        block["heading_deg"] = round(cog, 1)
        block["cog"] = round(cog, 1)
    return block


def parse_nmea_sentence(line: str) -> Optional[Dict[str, Any]]:
    """Parse a single NMEA line; returns partial gps dict or None."""
    trimmed = line.strip()
    if not trimmed.startswith("$"):
        return None
    if "*" in trimmed:
        trimmed = trimmed.split("*", 1)[0]
    parts = trimmed.split(",")
    if len(parts) < 2:
        return None
    sentence = parts[0].upper()
    if sentence.endswith("GGA"):
        parsed = _parse_gga(parts)
        return {"gps": parsed} if parsed else None
    if sentence.endswith("RMC"):
        parsed = _parse_rmc(parts)
        return {"gps": parsed} if parsed else None
    return None


def merge_nmea_from_text(text: str) -> Dict[str, Any]:
    """Scan multiline serial output for NMEA and merge into one gps block."""
    merged: Dict[str, Any] = {}
    for line in text.splitlines():
        block = parse_nmea_sentence(line)
        if not block or "gps" not in block:
            continue
        gps = block["gps"]
        for key, value in gps.items():
            if value is not None:
                merged[key] = value
    return merged
