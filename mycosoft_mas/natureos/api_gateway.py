"""NatureOS API Gateway - February 3, 2026"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class DeviceRegistration(BaseModel):
    device_type: str
    device_class: str
    location: Optional[Dict[str, float]] = None
    config: Dict[str, Any] = {}

class CommandRequest(BaseModel):
    command_type: str
    payload: Dict[str, Any] = {}
    priority: int = 5

class TelemetryReading(BaseModel):
    sensor_type: str
    reading: Dict[str, Any]
    timestamp: Optional[datetime] = None

class NatureOSGateway:
    def __init__(self, config: Any, services: Dict[str, Any]):
        self.config = config
        self.services = services
        self.app = FastAPI(title="NatureOS API Gateway", version="1.0.0", description="Unified API for NatureOS platform")
        self._setup_middleware()
        self._setup_routes()
        logger.info("NatureOS API Gateway initialized")
    
    def _setup_middleware(self) -> None:
        self.app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
        @self.app.middleware("http")
        async def log_requests(request: Request, call_next):
            start = datetime.now(timezone.utc)
            response = await call_next(request)
            latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            logger.info(f"{request.method} {request.url.path} - {response.status_code} - {latency:.2f}ms")
            return response
    
    def _setup_routes(self) -> None:
        @self.app.get("/health")
        async def health():
            return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}
        
        @self.app.get("/devices")
        async def list_devices():
            return await self.services["device_manager"].list_devices()
        
        @self.app.get("/devices/{device_id}")
        async def get_device(device_id: UUID):
            return await self.services["device_manager"].get_device_status(device_id)
        
        @self.app.post("/devices/register")
        async def register_device(reg: DeviceRegistration):
            device_id = await self.services["device_manager"].register_device(reg.device_type, reg.dict())
            return {"device_id": str(device_id), "status": "registered"}
        
        @self.app.post("/devices/{device_id}/commands")
        async def send_command(device_id: UUID, cmd: CommandRequest):
            cmd_id = await self.services["device_manager"].send_command(device_id, cmd.command_type, cmd.payload)
            return {"command_id": str(cmd_id), "status": "pending"}
        
        @self.app.get("/devices/{device_id}/telemetry")
        async def get_telemetry(device_id: UUID, limit: int = 100):
            return await self.services["telemetry"].get_history(device_id, limit)
        
        @self.app.get("/devices/{device_id}/telemetry/latest")
        async def get_latest_telemetry(device_id: UUID):
            return await self.services["telemetry"].get_latest(device_id)
        
        @self.app.post("/devices/{device_id}/telemetry")
        async def ingest_telemetry(device_id: UUID, reading: TelemetryReading):
            await self.services["telemetry"].ingest(device_id, reading.sensor_type, reading.reading)
            return {"status": "ingested"}
        
        @self.app.get("/events")
        async def list_events(active_only: bool = True):
            if active_only:
                return await self.services["event_manager"].get_active_events()
            return await self.services["event_manager"].get_all_events()
        
        @self.app.get("/events/{event_id}")
        async def get_event(event_id: UUID):
            return await self.services["event_manager"].get_event(event_id)
        
        @self.app.post("/signals/process")
        async def process_signal(device_id: UUID, signal_type: str, request: Request):
            data = await request.body()
            return await self.services["signal_processor"].process(device_id, data, signal_type)
        
        @self.app.post("/signals/classify")
        async def classify_signal(request: Request):
            data = await request.body()
            return await self.services["signal_processor"].classify_pattern(data)
    
    async def start(self) -> None:
        logger.info("NatureOS API Gateway started")
    
    async def shutdown(self) -> None:
        logger.info("NatureOS API Gateway shutdown")
    
    async def health_check(self) -> bool:
        return True
