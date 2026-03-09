"""Hyphae1 - Portable Field Mycelium Interface Device

Hyphae 1 is the lightweight portable field node running on Jetson Orin Nano (~$275).
Same Side A/B firmware as Mushroom 1 but with a smaller Jetson cortex
focused on NLM embeddings and lightweight inference rather than full
robotics (no arm, no GMSL cameras, battery-viable power profile).

Power profile: 7-15W (Orin Nano), battery-viable for field deployment.

Created: March 9, 2026
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4

from .base import BaseDevice, DeviceConfig, DeviceStatus, TelemetryReading


class Hyphae1Device(BaseDevice):
    """Hyphae 1 portable field mycelium interface device."""

    def __init__(self, config: DeviceConfig = None):
        if config is None:
            config = DeviceConfig(
                device_id=uuid4(),
                device_type="hyphae1",
                capabilities=[
                    "temperature",
                    "humidity",
                    "pressure",
                    "gas_resistance",
                    "voc",
                    "bioelectric",
                    "lora",
                    "wifi",
                    "nlm_edge",
                    "mmp_bridge",
                    "camera_usb",
                    "lightweight_inference",
                    "battery_mode",
                ],
            )
        super().__init__(config)
        self.bme688_available = False
        self.fci_available = False
        self.jetson_present = False
        self.battery_level: float = 100.0

    async def connect(self) -> bool:
        self._connected = True
        self.status = DeviceStatus.ONLINE
        self.bme688_available = True
        self.fci_available = True
        return True

    async def disconnect(self) -> None:
        self._connected = False
        self.status = DeviceStatus.OFFLINE

    async def read_sensors(self) -> List[TelemetryReading]:
        if not self._connected:
            return []
        now = datetime.now(timezone.utc)
        readings = [
            TelemetryReading(
                sensor_type="temperature", value=22.0, unit="celsius", timestamp=now
            ),
            TelemetryReading(
                sensor_type="humidity", value=75.0, unit="percent", timestamp=now
            ),
            TelemetryReading(
                sensor_type="pressure", value=1013.25, unit="hPa", timestamp=now
            ),
            TelemetryReading(
                sensor_type="gas_resistance",
                value=120000.0,
                unit="ohm",
                timestamp=now,
            ),
        ]
        for r in readings:
            self.add_telemetry(r)
        return readings

    async def send_command(
        self, command: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        commands = {
            "stimulate": self._stimulate,
            "calibrate_bme": self._calibrate_bme,
            "set_sample_rate": self._set_sample_rate,
            "get_battery": self._get_battery,
            "sleep": self._enter_sleep,
        }
        if command in commands:
            return await commands[command](params)
        return {"error": f"Unknown command: {command}"}

    async def _stimulate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        voltage_mv = params.get("voltage_mv", 50)
        duration_ms = params.get("duration_ms", 50)
        # Hyphae 1 has lower default stimulation limits for field safety
        if voltage_mv > 200:
            return {"error": "Voltage exceeds Hyphae 1 field safety limit (200mV)"}
        return {
            "stimulated": True,
            "voltage_mv": voltage_mv,
            "duration_ms": duration_ms,
        }

    async def _calibrate_bme(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {"calibrated": True, "sensor": "bme688"}

    async def _set_sample_rate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        rate_hz = params.get("rate_hz", 0.5)  # Lower default for battery life
        return {"sample_rate_hz": rate_hz}

    async def _get_battery(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "battery_level": self.battery_level,
            "charging": False,
            "estimated_hours": self.battery_level * 0.5,
        }

    async def _enter_sleep(self, params: Dict[str, Any]) -> Dict[str, Any]:
        duration_s = params.get("duration_s", 300)
        return {"status": "entering_sleep", "wake_after_s": duration_s}

    async def read_bioelectric(self, duration_ms: int = 500) -> Dict[str, Any]:
        if not self.fci_available:
            return {"error": "FCI not available"}
        return {
            "samples": [],
            "sample_rate_hz": 500,
            "duration_ms": duration_ms,
            "channels": 2,
        }
