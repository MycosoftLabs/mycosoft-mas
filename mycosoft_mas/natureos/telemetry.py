"""NatureOS Telemetry Service - February 3, 2026"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID
from collections import deque
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class TelemetryReading(BaseModel):
    device_id: UUID
    sensor_type: str
    reading: Dict[str, Any]
    quality_score: float = 1.0
    timestamp: datetime

class TelemetryService:
    def __init__(self, config: Any):
        self.config = config
        self.buffer_size = getattr(config, "telemetry_buffer_size", 1000)
        self._buffers: Dict[UUID, deque] = {}
        self._latest: Dict[UUID, Dict[str, TelemetryReading]] = {}
        self._running = False
        self._batch_queue: asyncio.Queue = asyncio.Queue()
        logger.info("Telemetry Service initialized")
    
    async def start(self) -> None:
        self._running = True
        logger.info("Telemetry Service started")
    
    async def shutdown(self) -> None:
        self._running = False
        logger.info("Telemetry Service shutdown")
    
    async def health_check(self) -> bool:
        return self._running
    
    async def ingest(self, device_id: UUID, sensor_type: str, reading: Dict[str, Any]) -> None:
        telemetry = TelemetryReading(
            device_id=device_id, sensor_type=sensor_type,
            reading=reading, timestamp=datetime.now(timezone.utc)
        )
        if device_id not in self._buffers:
            self._buffers[device_id] = deque(maxlen=self.buffer_size)
            self._latest[device_id] = {}
        self._buffers[device_id].append(telemetry)
        self._latest[device_id][sensor_type] = telemetry
        await self._batch_queue.put(telemetry)
    
    async def get_latest(self, device_id: UUID) -> Dict[str, Any]:
        if device_id not in self._latest:
            return {"error": "No telemetry available"}
        return {sensor: t.dict() for sensor, t in self._latest[device_id].items()}
    
    async def get_history(self, device_id: UUID, limit: int = 100) -> List[Dict[str, Any]]:
        if device_id not in self._buffers:
            return []
        readings = list(self._buffers[device_id])[-limit:]
        return [r.dict() for r in readings]
    
    async def process_batch(self) -> None:
        batch = []
        while not self._batch_queue.empty() and len(batch) < 100:
            try:
                item = self._batch_queue.get_nowait()
                batch.append(item)
            except asyncio.QueueEmpty:
                break
        if batch:
            logger.debug(f"Processed batch of {len(batch)} telemetry readings")
    
    async def get_stats(self) -> Dict[str, Any]:
        total_devices = len(self._buffers)
        total_readings = sum(len(b) for b in self._buffers.values())
        return {"total_devices": total_devices, "total_readings": total_readings, "buffer_size": self.buffer_size}
