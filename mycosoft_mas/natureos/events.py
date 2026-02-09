"""NatureOS Event Manager - February 3, 2026"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from enum import Enum
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class EventSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class EventType(str, Enum):
    DEVICE_OFFLINE = "device_offline"
    SENSOR_ANOMALY = "sensor_anomaly"
    SIGNAL_PATTERN = "signal_pattern"
    ENVIRONMENTAL_ALERT = "environmental_alert"
    SPORE_DETECTION = "spore_detection"
    CONTAMINATION = "contamination"
    NETWORK_ISSUE = "network_issue"
    SYSTEM_ERROR = "system_error"

class EnvironmentalEvent(BaseModel):
    event_id: UUID
    event_type: str
    source_device_id: Optional[UUID] = None
    location: Optional[Dict[str, float]] = None
    severity: EventSeverity = EventSeverity.INFO
    data: Dict[str, Any] = {}
    detected_at: datetime
    resolved_at: Optional[datetime] = None
    notes: Optional[str] = None

class EventManager:
    def __init__(self, config: Any):
        self.config = config
        self._events: Dict[UUID, EnvironmentalEvent] = {}
        self._running = False
        self._event_handlers: Dict[str, List[callable]] = {}
        logger.info("Event Manager initialized")
    
    async def start(self) -> None:
        self._running = True
        logger.info("Event Manager started")
    
    async def shutdown(self) -> None:
        self._running = False
        logger.info("Event Manager shutdown")
    
    async def health_check(self) -> bool:
        return self._running
    
    async def detect_and_register(self, event_type: str, data: Dict[str, Any]) -> Optional[UUID]:
        event_id = uuid4()
        event = EnvironmentalEvent(
            event_id=event_id, event_type=event_type,
            source_device_id=data.get("device_id"),
            location=data.get("location"),
            severity=EventSeverity(data.get("severity", "info")),
            data=data, detected_at=datetime.now(timezone.utc)
        )
        self._events[event_id] = event
        logger.info(f"Registered event: {event_id} ({event_type})")
        await self._notify_handlers(event)
        return event_id
    
    async def get_event(self, event_id: UUID) -> Optional[Dict[str, Any]]:
        if event_id in self._events:
            return self._events[event_id].dict()
        return None
    
    async def get_active_events(self) -> List[Dict[str, Any]]:
        active = [e for e in self._events.values() if e.resolved_at is None]
        return [e.dict() for e in active]
    
    async def get_all_events(self) -> List[Dict[str, Any]]:
        return [e.dict() for e in self._events.values()]
    
    async def resolve_event(self, event_id: UUID, notes: Optional[str] = None) -> bool:
        if event_id in self._events:
            self._events[event_id].resolved_at = datetime.now(timezone.utc)
            if notes:
                self._events[event_id].notes = notes
            logger.info(f"Resolved event: {event_id}")
            return True
        return False
    
    def register_handler(self, event_type: str, handler: callable) -> None:
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
    
    async def _notify_handlers(self, event: EnvironmentalEvent) -> None:
        handlers = self._event_handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Event handler error: {e}")
