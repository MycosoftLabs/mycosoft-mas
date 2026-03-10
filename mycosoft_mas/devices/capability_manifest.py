"""
MycoBrain Capability Manifest — Canonical contract for device sensors and capabilities.

Defines the mapping from device role (side-a, mushroom1, sporebase, etc.) to sensors
and capabilities. Used by MycoBrain Service when building heartbeat payloads, and by
website/MAS for display. Firmware may report role in hello/status; the service uses
this manifest to derive sensors/capabilities when firmware does not provide them.

Date: 2026-03-07
"""

from typing import List

# Canonical manifest entries: role -> (sensors, capabilities)
_ROLE_MANIFEST: dict[str, tuple[List[str], List[str]]] = {
    "side-a": (
        ["bme688_a", "bme688_b"],  # Dual BME688 (AMB + ENV)
        ["led", "buzzer", "i2c", "neopixel"],
    ),
    "side-a-working": (
        [],  # MycoBrain_Working minimal firmware
        ["led", "buzzer", "i2c"],
    ),
    "mushroom1": (
        ["bme688_a", "bme688_b"],
        ["led", "buzzer", "i2c", "neopixel", "telemetry"],
    ),
    "sporebase": (
        ["bme688", "spore_detection"],
        ["led", "buzzer", "i2c", "telemetry"],
    ),
    "hyphae1": (
        ["bme688", "soil_moisture"],
        ["led", "i2c", "telemetry"],
    ),
    "alarm": (
        ["bme688", "sound"],
        ["led", "buzzer", "telemetry"],
    ),
    "gateway": (
        [],
        ["service", "serial", "lora", "bluetooth", "wifi", "sim", "store_and_forward"],
    ),
    "standalone": (
        ["bme688_a", "bme688_b"],
        ["led", "buzzer", "i2c"],
    ),
}


def get_manifest_for_role(role: str | None) -> tuple[List[str], List[str]]:
    """
    Return (sensors, capabilities) for the given device role.

    Args:
        role: device_role from firmware (e.g. side-a, mushroom1) or None

    Returns:
        (sensors, capabilities) — use empty lists for unknown roles
    """
    if not role:
        return [], []
    key = (role or "").lower().strip()
    return _ROLE_MANIFEST.get(key, ([], []))


def get_default_manifest() -> tuple[List[str], List[str]]:
    """Default manifest when role is unknown (legacy devices)."""
    return _ROLE_MANIFEST["standalone"]
