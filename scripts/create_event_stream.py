"""Helper script to create event_stream.py"""
import os

content = '''"""
Event Stream for PersonaPlex Integration
Created: February 4, 2026

Real-time event streaming to PersonaPlex for live updates,
background announcements, and system notifications.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import weakref

logger = logging.getLogger(__name__)


class EventPriority(Enum):
    """Priority of events for delivery."""
    CRITICAL = 1    # Immediate delivery, interrupts current speech
    HIGH = 2        # Next in queue, may interrupt
    NORMAL = 3      # Standard queue position
    LOW = 4         # Background, deliver when idle
    BACKGROUND = 5  # Only when nothing else happening


class EventType(Enum):
    """Types of events that can be streamed."""
    VOICE_RESPONSE = "voice_response"
    SYSTEM_ANNOUNCEMENT = "system_announcement"
    TASK_COMPLETE = "task_complete"
    TASK_PROGRESS = "task_progress"
    AGENT_MESSAGE = "agent_message"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    SKILL_LEARNED = "skill_learned"
    MEMORY_UPDATED = "memory_updated"
    CONFIRMATION_REQUIRED = "confirmation_required"
    WORKFLOW_STATUS = "workflow_status"


@dataclass
class StreamEvent:
    """An event to be streamed."""
    event_id: str
    event_type: EventType
    priority: EventPriority
    content: str
    source: str
    target_user: Optional[str] = None
    
    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    
    # Delivery settings
    speak: bool = True
    display: bool = True
    log: bool = True
    
    # Additional data
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at


@dataclass
class StreamSubscription:
    """A subscription to event streams."""
    subscriber_id: str
    event_types: List[EventType]
    callback: Callable[[StreamEvent], Awaitable[None]]
    priority_threshold: EventPriority = EventPriority.BACKGROUND
    active: bool = True


class PersonaPlexEventStream:
    """
    Event streaming to PersonaPlex for real-time updates.
    
    Features:
    - Priority-based event queue
    - WebSocket streaming to PersonaPlex
    - Background announcements
    - Subscription-based delivery
    - Event batching for efficiency
    """
    
    def __init__(
        self,
        personaplex_url: str = "ws://localhost:8999/api/events",
        max_queue_size: int = 1000,
    ):
        self.personaplex_url = personaplex_url
        self.max_queue_size = max_queue_size
        
        # Event queues by priority
        self.queues: Dict[EventPriority, asyncio.Queue] = {
            p: asyncio.Queue(maxsize=max_queue_size // 5)
            for p in EventPriority
        }
        
        # Subscriptions
        self.subscriptions: Dict[str, StreamSubscription] = {}
        
        # WebSocket connection
        self.websocket = None
        self.connected = False
        
        # Processing state
        self.processing = False
        self.current_event: Optional[StreamEvent] = None
        
        # Stats
        self.events_sent = 0
        self.events_dropped = 0
        
        logger.info("PersonaPlexEventStream initialized")
    
    async def connect(self):
        """Connect to PersonaPlex WebSocket."""
        try:
            import websockets
            self.websocket = await websockets.connect(self.personaplex_url)
            self.connected = True
            logger.info(f"Connected to PersonaPlex at {self.personaplex_url}")
            
            # Start processing loop
            asyncio.create_task(self._process_loop())
            
        except Exception as e:
            logger.error(f"Failed to connect to PersonaPlex: {e}")
            self.connected = False
    
    async def disconnect(self):
        """Disconnect from PersonaPlex."""
        self.connected = False
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        logger.info("Disconnected from PersonaPlex")
    
    async def emit(
        self,
        event_type: EventType,
        content: str,
        source: str = "system",
        priority: EventPriority = EventPriority.NORMAL,
        target_user: Optional[str] = None,
        speak: bool = True,
        display: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StreamEvent:
        """
        Emit an event to the stream.
        
        Args:
            event_type: Type of event
            content: Event content/message
            source: Source of the event
            priority: Event priority
            target_user: Optional target user
            speak: Whether to speak the content
            display: Whether to display the content
            metadata: Additional metadata
            
        Returns:
            The created StreamEvent
        """
        import hashlib
        event_id = hashlib.md5(f"{content}{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        
        event = StreamEvent(
            event_id=event_id,
            event_type=event_type,
            priority=priority,
            content=content,
            source=source,
            target_user=target_user,
            speak=speak,
            display=display,
            metadata=metadata or {},
        )
        
        # Add to appropriate queue
        try:
            queue = self.queues[priority]
            if queue.full():
                # Drop oldest from this priority
                try:
                    queue.get_nowait()
                    self.events_dropped += 1
                except asyncio.QueueEmpty:
                    pass
            
            await queue.put(event)
            logger.debug(f"Emitted event: {event_id} ({event_type.value})")
            
        except Exception as e:
            logger.error(f"Failed to emit event: {e}")
        
        return event
    
    def subscribe(
        self,
        subscriber_id: str,
        event_types: List[EventType],
        callback: Callable[[StreamEvent], Awaitable[None]],
        priority_threshold: EventPriority = EventPriority.BACKGROUND,
    ) -> StreamSubscription:
        """Subscribe to events."""
        subscription = StreamSubscription(
            subscriber_id=subscriber_id,
            event_types=event_types,
            callback=callback,
            priority_threshold=priority_threshold,
        )
        
        self.subscriptions[subscriber_id] = subscription
        logger.info(f"Added subscription: {subscriber_id}")
        return subscription
    
    def unsubscribe(self, subscriber_id: str) -> bool:
        """Remove a subscription."""
        if subscriber_id in self.subscriptions:
            del self.subscriptions[subscriber_id]
            logger.info(f"Removed subscription: {subscriber_id}")
            return True
        return False
    
    async def _process_loop(self):
        """Main processing loop for events."""
        self.processing = True
        
        while self.connected:
            try:
                # Process in priority order
                event = await self._get_next_event()
                
                if event:
                    await self._deliver_event(event)
                else:
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
                await asyncio.sleep(1)
        
        self.processing = False
    
    async def _get_next_event(self) -> Optional[StreamEvent]:
        """Get the next event from queues by priority."""
        for priority in EventPriority:
            queue = self.queues[priority]
            try:
                event = queue.get_nowait()
                if not event.is_expired():
                    return event
            except asyncio.QueueEmpty:
                continue
        return None
    
    async def _deliver_event(self, event: StreamEvent):
        """Deliver an event to all subscribers and PersonaPlex."""
        self.current_event = event
        
        try:
            # Send to PersonaPlex WebSocket
            if self.websocket and event.speak:
                message = {
                    "type": "event",
                    "event_id": event.event_id,
                    "event_type": event.event_type.value,
                    "content": event.content,
                    "priority": event.priority.value,
                    "speak": event.speak,
                    "metadata": event.metadata,
                }
                await self.websocket.send(json.dumps(message))
            
            # Notify subscribers
            for subscription in self.subscriptions.values():
                if not subscription.active:
                    continue
                if event.event_type not in subscription.event_types:
                    continue
                if event.priority.value > subscription.priority_threshold.value:
                    continue
                
                try:
                    await subscription.callback(event)
                except Exception as e:
                    logger.error(f"Subscriber callback failed: {e}")
            
            event.delivered_at = datetime.now()
            self.events_sent += 1
            
        except Exception as e:
            logger.error(f"Event delivery failed: {e}")
        
        finally:
            self.current_event = None
    
    async def announce(
        self,
        message: str,
        priority: EventPriority = EventPriority.NORMAL,
        source: str = "system",
    ):
        """Convenience method for announcements."""
        await self.emit(
            event_type=EventType.SYSTEM_ANNOUNCEMENT,
            content=message,
            source=source,
            priority=priority,
        )
    
    async def notify_task_complete(
        self,
        task_name: str,
        result: str,
        source: str = "system",
    ):
        """Notify that a task is complete."""
        await self.emit(
            event_type=EventType.TASK_COMPLETE,
            content=f"Task completed: {task_name}. {result}",
            source=source,
            priority=EventPriority.HIGH,
            metadata={"task_name": task_name, "result": result},
        )
    
    async def notify_skill_learned(
        self,
        skill_name: str,
        skill_description: str,
        source: str = "skill-learning-agent",
    ):
        """Notify that a skill was learned."""
        await self.emit(
            event_type=EventType.SKILL_LEARNED,
            content=f"I learned a new skill: {skill_name}. {skill_description}",
            source=source,
            priority=EventPriority.HIGH,
            metadata={"skill_name": skill_name},
        )
    
    async def request_confirmation(
        self,
        action: str,
        request_id: str,
        source: str = "system",
    ):
        """Request confirmation for an action."""
        await self.emit(
            event_type=EventType.CONFIRMATION_REQUIRED,
            content=f"Please confirm: {action}",
            source=source,
            priority=EventPriority.CRITICAL,
            metadata={"request_id": request_id, "action": action},
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get streaming statistics."""
        queue_sizes = {p.name: self.queues[p].qsize() for p in EventPriority}
        return {
            "connected": self.connected,
            "processing": self.processing,
            "events_sent": self.events_sent,
            "events_dropped": self.events_dropped,
            "queue_sizes": queue_sizes,
            "subscriptions": len(self.subscriptions),
            "current_event": self.current_event.event_id if self.current_event else None,
        }


# Singleton
_stream_instance: Optional[PersonaPlexEventStream] = None


def get_event_stream() -> PersonaPlexEventStream:
    global _stream_instance
    if _stream_instance is None:
        _stream_instance = PersonaPlexEventStream()
    return _stream_instance


__all__ = [
    "PersonaPlexEventStream",
    "StreamEvent",
    "StreamSubscription",
    "EventPriority",
    "EventType",
    "get_event_stream",
]
'''

os.makedirs('mycosoft_mas/voice', exist_ok=True)
with open('mycosoft_mas/voice/event_stream.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Created event_stream.py')
