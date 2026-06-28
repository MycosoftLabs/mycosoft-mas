"""SINE buoy acoustic ingest — hydrophone (water) + MEMS (air) for Psathyrella."""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

PSATHYRELLA_SOURCE_PREFIX = "psathyrella"
HYDROPHONE_SENSOR_TOKEN = "hydrophone"
MEMS_SENSOR_TOKEN = "mems"


def _mindex_prefix() -> str:
    base = (os.getenv("MINDEX_API_URL") or "http://192.168.0.189:8000").rstrip("/")
    if base.endswith("/api/mindex"):
        return base
    return f"{base}/api/mindex"


def _mindex_headers() -> Dict[str, str]:
    headers: Dict[str, str] = {"Accept": "application/json", "Content-Type": "application/json"}
    api_key = (os.getenv("MINDEX_API_KEY") or "").strip()
    if api_key:
        headers["X-API-Key"] = api_key
    internal = (
        os.getenv("MINDEX_INTERNAL_TOKEN")
        or os.getenv("MINDEX_INTERNAL_TOKENS", "").split(",")[0]
    ).strip()
    if internal:
        headers["X-Internal-Token"] = internal
    return headers


def build_sine_ingest_metadata(
    *,
    device_id: str,
    sensor_type: str,
    recording_group: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Metadata envelope for SINE blob ingest.

    sensor_type must contain ``hydrophone`` (acoustic_domain=water) or ``mems`` (air).
    source_id / recording_group must contain ``psathyrella`` for GCS library filter.
    """
    normalized = sensor_type.lower()
    if HYDROPHONE_SENSOR_TOKEN in normalized:
        domain = "water"
    elif MEMS_SENSOR_TOKEN in normalized:
        domain = "air"
    else:
        domain = "unknown"

    group = recording_group or f"{device_id}:{normalized}"
    return {
        "source_id": f"{PSATHYRELLA_SOURCE_PREFIX}-{device_id}-{normalized}",
        "recording_group": group,
        "sensor_type": normalized,
        "acoustic_domain": domain,
        "device_id": device_id,
        "tags": [PSATHYRELLA_SOURCE_PREFIX, normalized, domain],
    }


async def ingest_acoustic_blob(
    *,
    device_id: str,
    sensor_type: str,
    blob_uri: str,
    duration_s: float,
    recording_group: Optional[str] = None,
    trigger_analyze: bool = True,
) -> Dict[str, Any]:
    """
    Register a buoy-scoped acoustic blob with MINDEX SINE and optionally run analysis.

    ``blob_uri`` must be an absolute path readable by the MINDEX API VM (NAS mount).
    Returns ``pending`` when MINDEX is unreachable or the file is not yet available.
    """
    meta = build_sine_ingest_metadata(
        device_id=device_id,
        sensor_type=sensor_type,
        recording_group=recording_group,
    )
    abs_path = blob_uri.strip()
    if not abs_path:
        return {
            "status": "pending",
            "reason": "missing_blob_uri",
            "metadata": meta,
        }

    register_body = {
        "abs_path": abs_path,
        "source_id": meta["source_id"],
        "sensor_type": meta["sensor_type"],
        "acoustic_domain": meta["acoustic_domain"],
        "device_id": device_id,
        "recording_group": meta["recording_group"],
        "duration_sec": duration_s,
        "metadata": meta,
    }

    url = f"{_mindex_prefix()}/sine/library/register"
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(url, headers=_mindex_headers(), json=register_body)
    except Exception as exc:
        logger.warning("SINE register failed for %s: %s", device_id, exc)
        return {
            "status": "pending",
            "reason": "mindex_unreachable",
            "metadata": meta,
            "blob_uri": abs_path,
            "detail": str(exc),
        }

    if response.status_code == 404:
        return {
            "status": "pending",
            "reason": "register_endpoint_missing",
            "metadata": meta,
            "blob_uri": abs_path,
            "detail": "Deploy MINDEX sine/library/register endpoint",
        }

    if response.status_code >= 400:
        return {
            "status": "pending",
            "reason": "register_rejected",
            "metadata": meta,
            "blob_uri": abs_path,
            "http_status": response.status_code,
            "detail": response.text[:300],
        }

    register_result = response.json()
    blob_id = register_result.get("blob_id") or register_result.get("id")
    result: Dict[str, Any] = {
        "status": register_result.get("status", "ok"),
        "metadata": meta,
        "blob_uri": abs_path,
        "blob_id": blob_id,
        "register": register_result,
    }

    if not trigger_analyze or not blob_id:
        return result

    analyze_url = f"{_mindex_prefix()}/sine/blobs/{blob_id}/analyze"
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            analyze_res = await client.post(analyze_url, headers=_mindex_headers())
        if analyze_res.status_code == 200:
            result["analysis"] = analyze_res.json()
            result["status"] = "ok"
        else:
            result["analysis"] = {
                "status": "pending",
                "reason": "analyze_failed",
                "http_status": analyze_res.status_code,
                "detail": analyze_res.text[:300],
            }
    except Exception as exc:
        result["analysis"] = {"status": "pending", "reason": "analyze_unreachable", "detail": str(exc)}

    return result


async def ingest_acoustic_blob_stub(
    *,
    device_id: str,
    sensor_type: str,
    blob_uri: str,
    duration_s: float,
) -> Dict[str, Any]:
    """Back-compat alias — delegates to :func:`ingest_acoustic_blob`."""
    return await ingest_acoustic_blob(
        device_id=device_id,
        sensor_type=sensor_type,
        blob_uri=blob_uri,
        duration_s=duration_s,
    )


def content_hash_for_path(path: str) -> Optional[str]:
    """SHA-256 of file bytes when path exists locally (MAS-side preflight)."""
    file_path = Path(path)
    if not file_path.is_file():
        return None
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
