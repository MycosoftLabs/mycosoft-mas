"""
NatureOS Platform Orchestration
Core platform orchestration for the NatureOS environmental operating system.
Created: February 3, 2026
"""

import asyncio
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from dataclasses import dataclass
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class PlatformStatus(str, Enum):
    INITIALIZING = "initializing"
    RUNNING = "running"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    SHUTDOWN = "shutdown"
    ERROR = "error"

class ServiceHealth(BaseModel):
    service_name: str
    status: str
    last_check: datetime
    latency_ms: Optional[float] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = {}

@dataclass
class PlatformConfig:
    postgres_url: str = "postgresql://localhost:5432/natureos"
    redis_url: str = "redis://localhost:6379"
    mindex_url: str = "http://localhost:8000"
    mas_url: str = "http://localhost:8001"
    personaplex_url: str = "ws://localhost:8998"
    telemetry_buffer_size: int = 1000
    signal_processing_workers: int = 4
    event_detection_interval_ms: int = 100
    enable_blockchain_logging: bool = True
    enable_edge_sync: bool = True
    enable_mesh_networking: bool = True

class NatureOSPlatform:
    def __init__(self, config: Optional[PlatformConfig] = None):
        self.config = config or PlatformConfig()
        self.platform_id = uuid4()
        self.status = PlatformStatus.INITIALIZING
        self.started_at: Optional[datetime] = None
        self.services: Dict[str, Any] = {}
        self._health_cache: Dict[str, ServiceHealth] = {}
        self._shutdown_event = asyncio.Event()
        logger.info(f"NatureOS Platform initialized: {self.platform_id}")
    
    async def start(self) -> None:
        logger.info("Starting NatureOS Platform...")
        self.started_at = datetime.now(timezone.utc)
        try:
            await self._init_device_manager()
            await self._init_signal_processor()
            await self._init_telemetry_service()
            await self._init_event_manager()
            await self._init_api_gateway()
            asyncio.create_task(self._health_check_loop())
            asyncio.create_task(self._telemetry_processing_loop())
            self.status = PlatformStatus.RUNNING
            logger.info(f"NatureOS Platform started at {self.started_at}")
        except Exception as e:
            self.status = PlatformStatus.ERROR
            logger.error(f"Failed to start NatureOS Platform: {e}")
            raise
    
    async def shutdown(self) -> None:
        logger.info("Shutting down NatureOS Platform...")
        self.status = PlatformStatus.SHUTDOWN
        self._shutdown_event.set()
        for service_name in reversed(list(self.services.keys())):
            try:
                service = self.services[service_name]
                if hasattr(service, "shutdown"):
                    await service.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down {service_name}: {e}")
        logger.info("NatureOS Platform shutdown complete")
    
    async def _init_device_manager(self) -> None:
        from .device_manager import DeviceManager
        self.services["device_manager"] = DeviceManager(self.config)
        await self.services["device_manager"].start()
    
    async def _init_signal_processor(self) -> None:
        from .signal_processor import SignalProcessor
        self.services["signal_processor"] = SignalProcessor(self.config)
        await self.services["signal_processor"].start()
    
    async def _init_telemetry_service(self) -> None:
        from .telemetry import TelemetryService
        self.services["telemetry"] = TelemetryService(self.config)
        await self.services["telemetry"].start()
    
    async def _init_event_manager(self) -> None:
        from .events import EventManager
        self.services["event_manager"] = EventManager(self.config)
        await self.services["event_manager"].start()
    
    async def _init_api_gateway(self) -> None:
        from .api_gateway import NatureOSGateway
        self.services["api_gateway"] = NatureOSGateway(self.config, self.services)
        await self.services["api_gateway"].start()
    
    async def _health_check_loop(self) -> None:
        while not self._shutdown_event.is_set():
            try:
                await self._check_all_services()
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
    
    async def _telemetry_processing_loop(self) -> None:
        while not self._shutdown_event.is_set():
            try:
                if "telemetry" in self.services:
                    await self.services["telemetry"].process_batch()
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Telemetry processing error: {e}")
    
    async def _check_all_services(self) -> None:
        for service_name, service in self.services.items():
            try:
                if hasattr(service, "health_check"):
                    health = await service.health_check()
                    self._health_cache[service_name] = ServiceHealth(
                        service_name=service_name,
                        status="healthy" if health else "unhealthy",
                        last_check=datetime.now(timezone.utc)
                    )
            except Exception as e:
                self._health_cache[service_name] = ServiceHealth(
                    service_name=service_name,
                    status="error",
                    last_check=datetime.now(timezone.utc),
                    error_message=str(e)
                )
    
    def get_health_status(self) -> Dict[str, Any]:
        return {
            "platform_id": str(self.platform_id),
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "uptime_seconds": (datetime.now(timezone.utc) - self.started_at).total_seconds() if self.started_at else 0,
            "services": {name: health.dict() for name, health in self._health_cache.items()}
        }
    
    async def register_device(self, device_type: str, config: Dict[str, Any]) -> UUID:
        return await self.services["device_manager"].register_device(device_type, config)
    
    async def send_command(self, device_id: UUID, command_type: str, payload: Dict[str, Any]) -> UUID:
        return await self.services["device_manager"].send_command(device_id, command_type, payload)
    
    async def get_device_status(self, device_id: UUID) -> Dict[str, Any]:
        return await self.services["device_manager"].get_device_status(device_id)
    
    async def process_signal(self, device_id: UUID, signal_data: bytes, signal_type: str) -> Dict[str, Any]:
        return await self.services["signal_processor"].process(device_id, signal_data, signal_type)
    
    async def classify_pattern(self, signal_data: bytes) -> Dict[str, Any]:
        return await self.services["signal_processor"].classify_pattern(signal_data)
    
    async def ingest_telemetry(self, device_id: UUID, sensor_type: str, reading: Dict[str, Any]) -> None:
        await self.services["telemetry"].ingest(device_id, sensor_type, reading)
    
    async def get_latest_telemetry(self, device_id: UUID) -> Dict[str, Any]:
        return await self.services["telemetry"].get_latest(device_id)
    
    async def detect_event(self, event_type: str, data: Dict[str, Any]) -> Optional[UUID]:
        return await self.services["event_manager"].detect_and_register(event_type, data)
    
    async def get_active_events(self) -> List[Dict[str, Any]]:
        return await self.services["event_manager"].get_active_events()

_platform_instance: Optional[NatureOSPlatform] = None

def get_platform() -> NatureOSPlatform:
    global _platform_instance
    if _platform_instance is None:
        _platform_instance = NatureOSPlatform()
    return _platform_instance

async def init_platform(config: Optional[PlatformConfig] = None) -> NatureOSPlatform:
    global _platform_instance
    _platform_instance = NatureOSPlatform(config)
    await _platform_instance.start()
    return _platform_instance
