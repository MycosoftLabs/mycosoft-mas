"""Base Device Class for all NatureOS hardware devices."""
import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from enum import Enum
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class DeviceStatus(str, Enum):
    OFFLINE = "offline"
    ONLINE = "online"
    BUSY = "busy"
    ERROR = "error"
    MAINTENANCE = "maintenance"
    CALIBRATING = "calibrating"

class DeviceConfig(BaseModel):
    device_id: UUID
    device_type: str
    hardware_version: str = "1.0"
    firmware_version: str = "1.0"
    location: Optional[Dict[str, float]] = None
    capabilities: List[str] = []
    settings: Dict[str, Any] = {}

class TelemetryReading(BaseModel):
    sensor_type: str
    value: Any
    unit: str
    quality: float = 1.0
    timestamp: datetime

class BaseDevice(ABC):
    """Abstract base class for all NatureOS devices."""
    
    def __init__(self, config: DeviceConfig):
        self.config = config
        self.device_id = config.device_id
        self.status = DeviceStatus.OFFLINE
        self._connected = False
        self._telemetry_buffer: List[TelemetryReading] = []
        self._command_queue: asyncio.Queue = asyncio.Queue()
        logger.info(f"Device {config.device_type} initialized: {self.device_id}")
    
    @abstractmethod
    async def connect(self) -> bool:
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        pass
    
    @abstractmethod
    async def read_sensors(self) -> List[TelemetryReading]:
        pass
    
    @abstractmethod
    async def send_command(self, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    async def get_status(self) -> Dict[str, Any]:
        return {"device_id": str(self.device_id), "type": self.config.device_type, "status": self.status.value, "connected": self._connected, "firmware": self.config.firmware_version}
    
    async def calibrate(self) -> bool:
        self.status = DeviceStatus.CALIBRATING
        await asyncio.sleep(1)
        self.status = DeviceStatus.ONLINE if self._connected else DeviceStatus.OFFLINE
        return True
    
    def add_telemetry(self, reading: TelemetryReading) -> None:
        self._telemetry_buffer.append(reading)
        if len(self._telemetry_buffer) > 1000:
            self._telemetry_buffer = self._telemetry_buffer[-1000:]
    
    def get_telemetry(self, limit: int = 100) -> List[Dict[str, Any]]:
        return [r.dict() for r in self._telemetry_buffer[-limit:]]
