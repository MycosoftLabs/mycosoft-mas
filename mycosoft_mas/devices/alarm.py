"""ALARM - Indoor Environmental Monitor"""
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4
from .base import BaseDevice, DeviceConfig, DeviceStatus, TelemetryReading

class AlarmDevice(BaseDevice):
    """ALARM indoor air quality and safety monitor."""
    
    def __init__(self, config: DeviceConfig = None):
        if config is None:
            config = DeviceConfig(device_id=uuid4(), device_type="alarm", capabilities=["air_quality", "co2", "voc", "particulate", "pathogen_detection"])
        super().__init__(config)
        self.alert_active = False
    
    async def connect(self) -> bool:
        self._connected = True
        self.status = DeviceStatus.ONLINE
        return True
    
    async def disconnect(self) -> None:
        self._connected = False
        self.status = DeviceStatus.OFFLINE
    
    async def read_sensors(self) -> List[TelemetryReading]:
        now = datetime.now(timezone.utc)
        return [
            TelemetryReading(sensor_type="co2", value=800.0, unit="ppm", timestamp=now),
            TelemetryReading(sensor_type="voc_index", value=50.0, unit="index", timestamp=now),
            TelemetryReading(sensor_type="pm25", value=10.0, unit="ug/m3", timestamp=now),
        ]
    
    async def send_command(self, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if command == "trigger_alert": return {"alert": "triggered", "type": params.get("type", "general")}
        if command == "clear_alert": self.alert_active = False; return {"alert": "cleared"}
        return {"error": f"Unknown command: {command}"}
