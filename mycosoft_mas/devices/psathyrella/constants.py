"""Psathyrella buoy identity and alias resolution helpers."""

from __future__ import annotations

import os

# Canonical public identity (Mushroom 1 on Jetson MQTT/HTTP agent).
PSATHYRELLA_CANONICAL_DEVICE_ID = "psathyrella-1"
PSATHYRELLA_DEVICE_ID = PSATHYRELLA_CANONICAL_DEVICE_ID
PSATHYRELLA_LEGACY_DEVICE_ID = "psathyrella-buoy-com4"
PSATHYRELLA_REGISTRY_ID = "mycobrain-COM4"
PSATHYRELLA_PORTAL_PORT = "COM4"
# Primary sensor path: Mushroom 1 MycoBrain agent on Jetson (not dev-desk COM3 / local :8003).
PSATHYRELLA_MUSHROOM1_AGENT_URL = (
    os.getenv("PSATHYRELLA_MUSHROOM1_AGENT_URL")
    or os.getenv("PSATHYRELLA_SENSOR_AGENT_URL")
    or os.getenv("JETSON_AGENT_URL")
    or "http://192.168.0.123:8787"
).rstrip("/")
PSATHYRELLA_MQTT_TOPIC_PREFIX = os.getenv(
    "PSATHYRELLA_MQTT_TOPIC_PREFIX",
    f"mycosoft/devices/{PSATHYRELLA_CANONICAL_DEVICE_ID}",
)
# Propulsion MDP agent (split-port Option B — do not use :8787 Mushroom 1 lane).
PSATHYRELLA_PROPULSION_AGENT_URL = (
    os.getenv("PSATHYRELLA_PROPULSION_AGENT_URL")
    or os.getenv("PSATHYRELLA_JETSON_PROPULSION_URL")
    or "http://192.168.0.123:8788"
).rstrip("/")
# Bench default: unset preferred_bearer => contactState "dark" and nav.thrust_vector queues to MT.
PSATHYRELLA_DEFAULT_BEARER = (os.getenv("PSATHYRELLA_DEFAULT_BEARER") or "wifi").strip().lower()
# Legacy dev-desk serial — NOT the Psathyrella production sensor lane (Jul 01, 2026 correction).
PSATHYRELLA_SERIAL_PORT = os.getenv("PSATHYRELLA_SERIAL_PORT") or os.getenv("MYCOBRAIN_SERIAL_PORT", "COM3")
PSATHYRELLA_SERIAL_DEVICE_ID = f"mycobrain-{PSATHYRELLA_SERIAL_PORT.upper()}"
PROJECT_OYSTER_ANCHOR = {"lat": 32.56289, "lon": -117.1357}

# Bench: Morgan wires one propeller (thruster id 0) + 360° azimuth servo on Jetson today.
PSATHYRELLA_BENCH_SINGLE_MOTOR = os.getenv("PSATHYRELLA_BENCH_SINGLE_MOTOR", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
PSATHYRELLA_BENCH_ACTIVE_THRUSTER_ID = int(os.getenv("PSATHYRELLA_BENCH_ACTIVE_THRUSTER_ID", "0") or "0")

PSATHYRELLA_DEVICE_ALIASES = frozenset(
    {
        PSATHYRELLA_CANONICAL_DEVICE_ID,
        PSATHYRELLA_LEGACY_DEVICE_ID,
        PSATHYRELLA_REGISTRY_ID,
        PSATHYRELLA_SERIAL_DEVICE_ID,
    }
)


def _normalize_device_id(device_id: str) -> str:
    return (device_id or "").strip()


def is_psathyrella_device_id(device_id: str) -> bool:
    return _normalize_device_id(device_id) in PSATHYRELLA_DEVICE_ALIASES


def resolve_public_device_id(device_id: str) -> str:
    """Return the canonical public device id used by the GCS/API."""
    key = _normalize_device_id(device_id)
    if is_psathyrella_device_id(key):
        return PSATHYRELLA_CANONICAL_DEVICE_ID
    return key


def registry_device_id_candidates(device_id: str) -> list[str]:
    """Ordered registry lookup candidates for psathyrella aliases."""
    key = _normalize_device_id(device_id)
    if not is_psathyrella_device_id(key):
        return [key]
    return [
        PSATHYRELLA_CANONICAL_DEVICE_ID,
        PSATHYRELLA_REGISTRY_ID,
        PSATHYRELLA_LEGACY_DEVICE_ID,
        PSATHYRELLA_SERIAL_DEVICE_ID,
    ]


def resolve_registry_device_id(device_id: str, registry_keys: set[str] | None = None) -> str:
    """Resolve a public/catalog id to the active MAS registry key."""
    candidates = registry_device_id_candidates(device_id)
    if registry_keys:
        for candidate in candidates:
            if candidate in registry_keys:
                return candidate
    return candidates[0] if len(candidates) == 1 else PSATHYRELLA_REGISTRY_ID


def resolve_mdp_device_id(registry_id: str, device_extra: dict | None = None) -> str:
    """Resolve MDP device id from registry row (prefer Mushroom 1 / psathyrella-1)."""
    extra = device_extra or {}
    serial = extra.get("serial_device_id") or extra.get("mdp_device_id")
    if isinstance(serial, str) and serial.strip():
        return serial.strip()
    if is_psathyrella_device_id(registry_id):
        return PSATHYRELLA_CANONICAL_DEVICE_ID
    return registry_id
