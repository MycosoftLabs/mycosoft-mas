"""Mushroom1 - Environmental Fungal Computer Device"""
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4
from .base import BaseDevice, DeviceConfig, DeviceStatus, TelemetryReading

class Mushroom1Device(BaseDevice):
    """Mushroom1 environmental sensor and fungal biocomputer device."""
    
    def __init__(self, config: DeviceConfig = None):
        if config is None:
            config = DeviceConfig(device_id=uuid4(), device_type="mushroom1", capabilities=["temperature", "humidity", "pressure", "gas_resistance", "voc", "bioelectric", "lora", "wifi"])
        super().__init__(config)
        self.bme688_available = False
        self.fci_available = False
    
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
        if not self._connected: return []
        now = datetime.now(timezone.utc)
        readings = [
            TelemetryReading(sensor_type="temperature", value=25.0, unit="celsius", timestamp=now),
            TelemetryReading(sensor_type="humidity", value=60.0, unit="percent", timestamp=now),
            TelemetryReading(sensor_type="pressure", value=1013.25, unit="hPa", timestamp=now),
            TelemetryReading(sensor_type="gas_resistance", value=100000.0, unit="ohm", timestamp=now),
        ]
        for r in readings: self.add_telemetry(r)
        return readings
    
    async def send_command(self, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        commands = {"stimulate": self._stimulate, "calibrate_bme": self._calibrate_bme, "set_sample_rate": self._set_sample_rate}
        if command in commands: return await commands[command](params)
        return {"error": f"Unknown command: {command}"}
    
    async def _stimulate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        voltage_mv = params.get("voltage_mv", 100)
        duration_ms = params.get("duration_ms", 100)
        return {"stimulated": True, "voltage_mv": voltage_mv, "duration_ms": duration_ms}
    
    async def _calibrate_bme(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {"calibrated": True, "sensor": "bme688"}
    
    async def _set_sample_rate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        rate_hz = params.get("rate_hz", 1)
        return {"sample_rate_hz": rate_hz}
    
    async def read_bioelectric(self, duration_ms: int = 1000) -> Dict[str, Any]:
        if not self.fci_available: return {"error": "FCI not available"}
        return {"samples": [], "sample_rate_hz": 1000, "duration_ms": duration_ms, "channels": 4}
