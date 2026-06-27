"""SINE buoy acoustic ingest scoping — hydrophone (water) + MEMS (air) for Psathyrella."""

from __future__ import annotations

from typing import Any, Dict, Optional

# Token contract for MINDEX library filter + inferEnvironment (website lib/psathyrella/sineClasses.ts)
PSATHYRELLA_SOURCE_PREFIX = "psathyrella"
HYDROPHONE_SENSOR_TOKEN = "hydrophone"
MEMS_SENSOR_TOKEN = "mems"


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


async def ingest_acoustic_blob_stub(
    *,
    device_id: str,
    sensor_type: str,
    blob_uri: str,
    duration_s: float,
) -> Dict[str, Any]:
    """
    Placeholder until MINDEX SINE ingest pipeline accepts buoy-scoped blobs.

    Wire to POST ``/api/mindex/sine/library/blobs`` (website BFF) or MINDEX VM direct.
    After ingest, trigger analysis so ``detector_events[]`` include event_type, acoustic_domain, confidence.
    """
    meta = build_sine_ingest_metadata(device_id=device_id, sensor_type=sensor_type)
    return {
        "status": "pending",
        "reason": "ingest_not_wired",
        "metadata": meta,
        "blob_uri": blob_uri,
        "duration_s": duration_s,
        "next_steps": [
            "POST blob with source_id/recording_group tokens containing psathyrella + hydrophone|mems",
            "Run SINE analysis job; verify /api/mindex/sine/status and library?q=psathyrella",
        ],
    }
