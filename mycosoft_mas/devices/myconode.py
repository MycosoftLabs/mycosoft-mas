"""MycoNode - In-Situ Fungal Soil Probe"""
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4
from .base import BaseDevice, DeviceConfig, DeviceStatus, TelemetryReading

class MycoNodeDevice(BaseDevice):
    """MycoNode soil probe for in-ground fungal network interface."""
    
    def __init__(self, config: DeviceConfig = None):
        if config is None:
            config = DeviceConfig(device_id=uuid4(), device_type="myconode", capabilities=["soil_moisture", "soil_ph", "bioelectric", "stimulation", "ble"])
        super().__init__(config)
        self.electrode_count = 8
    
    async def connect(self) -> bool:
        self._connected = True
        self.status = DeviceStatus.ONLINE
        return True
    
    async def disconnect(self) -> None:
        self._connected = False
        self.status = DeviceStatus.OFFLINE
    
    async def read_sensors(self) -> List[TelemetryReading]:
        if not self._connected: return []
        now = datetime.now(timezone.utc)
        return [
            TelemetryReading(sensor_type="soil_moisture", value=45.0, unit="percent", timestamp=now),
            TelemetryReading(sensor_type="soil_ph", value=6.5, unit="pH", timestamp=now),
            TelemetryReading(sensor_type="soil_temperature", value=18.0, unit="celsius", timestamp=now),
        ]
    
    async def send_command(self, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if command == "stimulate": return await self._stimulate(params)
        if command == "record": return await self._record(params)
        return {"error": f"Unknown command: {command}"}
    
    async def _stimulate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        voltage_mv = params.get("voltage_mv", 50)
        pattern = params.get("pattern", "pulse")
        return {"stimulated": True, "voltage_mv": voltage_mv, "pattern": pattern}
    
    async def _record(self, params: Dict[str, Any]) -> Dict[str, Any]:
        duration_ms = params.get("duration_ms", 1000)
        return {"recording_id": str(uuid4()), "duration_ms": duration_ms, "channels": self.electrode_count}
