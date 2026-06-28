"""Psathyrella buoy identity constants — COM3 hardware, COM4 portal alias."""

from __future__ import annotations

import os

PSATHYRELLA_DEVICE_ID = "psathyrella-buoy-com4"
PSATHYRELLA_REGISTRY_ID = "mycobrain-COM4"
PSATHYRELLA_PORTAL_PORT = "COM4"
PSATHYRELLA_SERIAL_PORT = os.getenv("MYCOBRAIN_SERIAL_PORT", "COM3")
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

DEVICE_ID_ALIASES: dict[str, str] = {
    PSATHYRELLA_DEVICE_ID: PSATHYRELLA_REGISTRY_ID,
    PSATHYRELLA_REGISTRY_ID: PSATHYRELLA_REGISTRY_ID,
    PSATHYRELLA_SERIAL_DEVICE_ID: PSATHYRELLA_REGISTRY_ID,
}


def resolve_registry_device_id(device_id: str) -> str:
    """Map catalog or serial ids to MAS registry id (stable portal)."""
    key = (device_id or "").strip()
    return DEVICE_ID_ALIASES.get(key, key)


def resolve_mdp_device_id(registry_id: str, device_extra: dict | None = None) -> str:
    """Resolve serial MDP path id (COM3) from registry row."""
    extra = device_extra or {}
    serial = extra.get("serial_device_id") or extra.get("mdp_device_id")
    if isinstance(serial, str) and serial.strip():
        return serial.strip()
    if registry_id == PSATHYRELLA_REGISTRY_ID:
        return PSATHYRELLA_SERIAL_DEVICE_ID
    return registry_id
