"""NatureOS Device Manager - February 3, 2026"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from enum import Enum
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class DeviceClass(str, Enum):
    MUSHROOM1 = "mushroom1"
    MYCONODE = "myconode"
    SPOREBASE = "sporebase"
    PETRAEUS = "petraeus"
    TRUFFLEBOT = "trufflebot"
    ALARM = "alarm"
    MYCOTENNA = "mycotenna"

class DeviceStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    ERROR = "error"

class Device(BaseModel):
    device_id: UUID
    device_type: str
    device_class: str
    hardware_version: Optional[str] = None
    firmware_version: Optional[str] = None
    status: DeviceStatus = DeviceStatus.OFFLINE
    location: Optional[Dict[str, float]] = None
    capabilities: Dict[str, Any] = {}
    config: Dict[str, Any] = {}
    last_telemetry: Optional[datetime] = None
    registered_at: datetime

class DeviceManager:
    def __init__(self, config: Any):
        self.config = config
        self._devices: Dict[UUID, Device] = {}
        self._commands: Dict[UUID, Dict[str, Any]] = {}
        self._running = False
        logger.info("Device Manager initialized")
    
    async def start(self) -> None:
        self._running = True
        asyncio.create_task(self._heartbeat_monitor())
        logger.info("Device Manager started")
    
    async def shutdown(self) -> None:
        self._running = False
        logger.info("Device Manager shutdown")
    
    async def health_check(self) -> bool:
        return self._running
    
    async def register_device(self, device_type: str, config: Dict[str, Any]) -> UUID:
        device_id = uuid4()
        device = Device(
            device_id=device_id, device_type=device_type,
            device_class=config.get("device_class", "unknown"),
            hardware_version=config.get("hardware_version"),
            firmware_version=config.get("firmware_version"),
            location=config.get("location"), capabilities=config.get("capabilities", {}),
            config=config.get("config", {}), registered_at=datetime.now(timezone.utc)
        )
        self._devices[device_id] = device
        logger.info(f"Registered device: {device_id} ({device_type})")
        return device_id
    
    async def get_device_status(self, device_id: UUID) -> Dict[str, Any]:
        if device_id not in self._devices:
            return {"error": "Device not found"}
        return self._devices[device_id].dict()
    
    async def list_devices(self) -> List[Dict[str, Any]]:
        return [d.dict() for d in self._devices.values()]
    
    async def send_command(self, device_id: UUID, command_type: str, payload: Dict[str, Any]) -> UUID:
        if device_id not in self._devices:
            raise ValueError(f"Device not found: {device_id}")
        command_id = uuid4()
        self._commands[command_id] = {
            "command_id": command_id, "device_id": device_id, "command_type": command_type,
            "payload": payload, "status": "pending", "created_at": datetime.now(timezone.utc).isoformat()
        }
        logger.info(f"Command {command_id} sent to device {device_id}")
        return command_id
    
    async def update_device_status(self, device_id: UUID, status: DeviceStatus) -> None:
        if device_id in self._devices:
            self._devices[device_id].status = status
    
    async def update_telemetry_timestamp(self, device_id: UUID) -> None:
        if device_id in self._devices:
            self._devices[device_id].last_telemetry = datetime.now(timezone.utc)
    
    async def _heartbeat_monitor(self) -> None:
        while self._running:
            try:
                now = datetime.now(timezone.utc)
                for device in self._devices.values():
                    if device.last_telemetry:
                        elapsed = (now - device.last_telemetry).total_seconds()
                        if elapsed > 60 and device.status == DeviceStatus.ONLINE:
                            device.status = DeviceStatus.OFFLINE
                            logger.warning(f"Device {device.device_id} went offline")
                await asyncio.sleep(10)
            except asyncio.CancelledError: break
            except Exception as e: logger.error(f"Heartbeat monitor error: {e}")
