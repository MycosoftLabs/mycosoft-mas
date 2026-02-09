"""TruffleBot - Autonomous Fungal Sampling Robot"""
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4
from .base import BaseDevice, DeviceConfig, DeviceStatus, TelemetryReading

class TruffleBotDevice(BaseDevice):
    """TruffleBot autonomous rover for field sampling."""
    
    def __init__(self, config: DeviceConfig = None):
        if config is None:
            config = DeviceConfig(device_id=uuid4(), device_type="trufflebot", capabilities=["navigation", "sample_collection", "probe_deployment", "camera", "lidar"])
        super().__init__(config)
        self.position = {"x": 0.0, "y": 0.0, "z": 0.0}
        self.battery_percent = 100.0
    
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
            TelemetryReading(sensor_type="battery", value=self.battery_percent, unit="percent", timestamp=now),
            TelemetryReading(sensor_type="position", value=self.position, unit="meters", timestamp=now),
        ]
    
    async def send_command(self, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if command == "navigate": return await self._navigate(params)
        if command == "collect_sample": return await self._collect_sample(params)
        if command == "deploy_probe": return await self._deploy_probe(params)
        return {"error": f"Unknown command: {command}"}
    
    async def _navigate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        target = params.get("target", {"x": 0, "y": 0})
        self.position = {"x": target.get("x", 0), "y": target.get("y", 0), "z": 0}
        return {"navigated": True, "position": self.position}
    
    async def _collect_sample(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {"sample_id": str(uuid4()), "position": self.position}
    
    async def _deploy_probe(self, params: Dict[str, Any]) -> Dict[str, Any]:
        depth_cm = params.get("depth_cm", 10)
        return {"probe_deployed": True, "depth_cm": depth_cm}
