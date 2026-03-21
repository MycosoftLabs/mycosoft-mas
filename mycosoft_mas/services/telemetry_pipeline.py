"""
MycoBrain → MAS → MINDEX Telemetry Pipeline

Polls MycoBrain service for device telemetry and forwards to MINDEX.
Part of the MYCA Opposable Thumb Architecture (biospheric telemetry stack).
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

MYCOBRAIN_URL = os.getenv("MYCOBRAIN_SERVICE_URL", "http://localhost:8003")
MINDEX_API_URL = os.getenv("MINDEX_API_URL", "http://192.168.0.189:8000").rstrip("/")
MINDEX_API_KEY = os.getenv("MINDEX_API_KEY", "")
MINDEX_API_PREFIX = "/api/mindex"
TELEMETRY_FORWARD_INTERVAL = int(os.getenv("TELEMETRY_FORWARD_INTERVAL", "60"))


def _mycobrain_to_envelope(
    device_id: str, telemetry: Dict[str, Any], ts: datetime
) -> Dict[str, Any]:
    """Transform MycoBrain telemetry to MINDEX envelope format."""
    pack: List[Dict[str, Any]] = []
    for sensor_key, sensor_data in [
        ("bme1", telemetry.get("bme1")),
        ("bme2", telemetry.get("bme2")),
    ]:
        if not isinstance(sensor_data, dict):
            continue
        for key, val in sensor_data.items():
            if key == "type":
                continue
            if isinstance(val, (int, float)):
                pack.append({"id": f"{sensor_key}_{key}", "v": val, "u": _unit_for(key)})
    if not pack:
        return {}
    device_slug = device_id.replace(" ", "-").lower()
    envelope = {
        "hdr": {"deviceId": device_slug, "msgId": str(uuid.uuid4())[:8]},
        "ts": {"utc": ts.isoformat()},
        "seq": int(ts.timestamp() * 1000) % 65536,
        "pack": pack,
    }
    return envelope


def _unit_for(key: str) -> str:
    units = {
        "temperature": "°C",
        "humidity": "%",
        "pressure": "hPa",
        "gas_resistance": "Ω",
        "iaq": "",
    }
    return units.get(key, "")


def _mycobrain_to_mycobrain_payload(telemetry: Dict[str, Any]) -> Dict[str, Any]:
    """Build MINDEX MycoBrain TelemetryPayload from MycoBrain standalone response."""
    payload: Dict[str, Any] = {}
    bme = None
    for k in ("bme1", "bme2"):
        d = telemetry.get(k)
        if isinstance(d, dict) and (
            d.get("temperature") is not None or d.get("humidity") is not None
        ):
            bme = {
                "temperature_c": d.get("temperature"),
                "humidity_percent": d.get("humidity"),
                "pressure_hpa": d.get("pressure"),
                "gas_resistance_ohms": d.get("gas_resistance"),
                "iaq_index": d.get("iaq"),
            }
            break
    if bme:
        payload["bme688"] = bme
    return payload


async def forward_mycobrain_to_mindex() -> Dict[str, Any]:
    """
    Poll MycoBrain service, fetch telemetry for each device, forward to MINDEX.
    Uses MINDEX envelope ingest (auto-creates devices) and MycoBrain ingest when device exists.
    """
    global _last_result, _last_run_at
    result = {"devices_polled": 0, "forwarded": 0, "errors": []}
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            r = await client.get(f"{MYCOBRAIN_URL}/devices")
            r.raise_for_status()
            devices = r.json()
        except Exception as e:
            logger.warning("MycoBrain devices unavailable: %s", e)
            result["errors"].append(str(e))
            return result

        device_list = (
            devices.get("devices", devices)
            if isinstance(devices, dict)
            else (devices if isinstance(devices, list) else [])
        )
        if not isinstance(device_list, list):
            device_list = []

        for dev in device_list:
            if not isinstance(dev, dict):
                continue
            device_id = dev.get("device_id") or dev.get("id") or dev.get("port") or str(dev)
            result["devices_polled"] += 1

            try:
                tr = await client.get(f"{MYCOBRAIN_URL}/devices/{device_id}/telemetry")
                tr.raise_for_status()
                data = tr.json()
            except Exception as e:
                result["errors"].append(f"{device_id}: {e}")
                continue

            telemetry = data.get("telemetry", data) if isinstance(data, dict) else {}
            ts_str = data.get("timestamp") if isinstance(data, dict) else None
            ts = (
                datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if ts_str
                else datetime.now(timezone.utc)
            )

            # Forward via envelope ingest (creates device by slug, works without pre-registration)
            envelope = _mycobrain_to_envelope(device_id, telemetry, ts)
            if envelope:
                headers = {"Content-Type": "application/json"}
                if MINDEX_API_KEY:
                    headers["X-API-Key"] = MINDEX_API_KEY
                try:
                    er = await client.post(
                        f"{MINDEX_API_URL}{MINDEX_API_PREFIX}/telemetry/envelope",
                        json={"envelope": envelope},
                        headers=headers,
                    )
                    if er.status_code in (200, 201):
                        result["forwarded"] += 1
                        logger.debug("Forwarded telemetry for %s", device_id)
                    else:
                        result["errors"].append(
                            f"{device_id} envelope: {er.status_code} {er.text[:100]}"
                        )
                except Exception as e:
                    result["errors"].append(f"{device_id} envelope: {e}")

            # Also try MycoBrain-specific ingest if device may be registered
            payload_dict = _mycobrain_to_mycobrain_payload(telemetry)
            if payload_dict and payload_dict.get("bme688"):
                serial = str(device_id).replace("mycobrain-", "").replace(" ", "-").lower()
                try:
                    mr = await client.post(
                        f"{MINDEX_API_URL}{MINDEX_API_PREFIX}/mycobrain/telemetry/ingest",
                        json={
                            "serial_number": serial,
                            "payload": payload_dict,
                            "recorded_at": ts.isoformat(),
                        },
                        headers={
                            "Content-Type": "application/json",
                            **({"X-API-Key": MINDEX_API_KEY} if MINDEX_API_KEY else {}),
                        },
                    )
                    if mr.status_code in (200, 201):
                        result["forwarded"] += 1
                    # 404 = device not in mycobrain.device, that's OK - envelope path covers it
                except Exception:
                    pass

    _last_result = result
    _last_run_at = datetime.now(timezone.utc)
    return result


_pipeline_task: Optional[asyncio.Task] = None
_pipeline_running = False
_last_result: Dict[str, Any] = {}
_last_run_at: Optional[datetime] = None


def get_pipeline_status() -> Dict[str, Any]:
    """Return pipeline status for API and monitoring."""
    return {
        "running": _pipeline_running,
        "interval_seconds": TELEMETRY_FORWARD_INTERVAL,
        "mycobrain_url": MYCOBRAIN_URL,
        "mindex_url": f"{MINDEX_API_URL}{MINDEX_API_PREFIX}",
        "last_result": _last_result,
        "last_run_at": _last_run_at.isoformat() if _last_run_at else None,
    }


async def _pipeline_loop() -> None:
    global _pipeline_running
    _pipeline_running = True
    logger.info("Telemetry pipeline started (interval=%ds)", TELEMETRY_FORWARD_INTERVAL)
    while _pipeline_running:
        try:
            await forward_mycobrain_to_mindex()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.exception("Telemetry pipeline error: %s", e)
        await asyncio.sleep(TELEMETRY_FORWARD_INTERVAL)
    _pipeline_running = False
    logger.info("Telemetry pipeline stopped")


def start_telemetry_pipeline() -> None:
    """Start the background telemetry forward loop."""
    global _pipeline_task
    if _pipeline_task is None or _pipeline_task.done():
        _pipeline_task = asyncio.create_task(_pipeline_loop())
        logger.info("Telemetry pipeline task started")


def stop_telemetry_pipeline() -> None:
    """Stop the background telemetry forward loop."""
    global _pipeline_task, _pipeline_running
    _pipeline_running = False
    if _pipeline_task and not _pipeline_task.done():
        _pipeline_task.cancel()
        _pipeline_task = None
