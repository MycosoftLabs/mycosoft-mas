"""SporeBase - Airborne Spore Collector"""
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4
from .base import BaseDevice, DeviceConfig, DeviceStatus, TelemetryReading

class SporeBaseDevice(BaseDevice):
    """SporeBase airborne spore collector with VOC sensing."""
    
    def __init__(self, config: DeviceConfig = None):
        if config is None:
            config = DeviceConfig(device_id=uuid4(), device_type="sporebase", capabilities=["spore_collection", "voc_sensing", "particle_count", "tape_imaging"])
        super().__init__(config)
        self.tape_position = 0
        self.collection_active = False
    
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
            TelemetryReading(sensor_type="particle_count_pm25", value=15.0, unit="ug/m3", timestamp=now),
            TelemetryReading(sensor_type="voc_index", value=100.0, unit="index", timestamp=now),
            TelemetryReading(sensor_type="spore_density", value=50.0, unit="spores/m3", timestamp=now),
        ]
    
    async def send_command(self, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if command == "start_collection": return await self._start_collection(params)
        if command == "stop_collection": return await self._stop_collection(params)
        if command == "advance_tape": return await self._advance_tape(params)
        return {"error": f"Unknown command: {command}"}
    
    async def _start_collection(self, params: Dict[str, Any]) -> Dict[str, Any]:
        self.collection_active = True
        return {"collection": "started"}
    
    async def _stop_collection(self, params: Dict[str, Any]) -> Dict[str, Any]:
        self.collection_active = False
        return {"collection": "stopped"}
    
    async def _advance_tape(self, params: Dict[str, Any]) -> Dict[str, Any]:
        steps = params.get("steps", 1)
        self.tape_position += steps
        return {"tape_position": self.tape_position}
