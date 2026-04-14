"""
Attention event bus for conscious/subconscious separation.

Phase 5: publish + drain only (simple queue model).
Full-Duplex Consciousness OS upgrade (April 2026): subscribe/get_pending added.
Created: February 12, 2026
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Standard event types for subconscious→conscious communication."""

    WORLD_ANOMALY = "world_anomaly"
    PATTERN_DETECTED = "pattern_detected"
    MEMORY_SUGGESTION = "memory_suggestion"
    AGENT_STATUS = "agent_status"
    TOOL_PROGRESS = "tool_progress"
    EMOTION_SHIFT = "emotion_shift"
    DREAM_INSIGHT = "dream_insight"


@dataclass
class AttentionEvent:
    type: str
    source: str
    data: Dict[str, Any]
    priority: int = 5  # 1 (low) to 10 (high)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# Subscriber callback type: async fn(event) -> None
SubscriberCallback = Callable[[AttentionEvent], Coroutine[Any, Any, None]]


class AttentionEventBus:
    """
    Pub/sub event bus for subconscious → conscious communication.

    **Rule enforced by design:** Subconscious processes NEVER call speech or
    yield methods directly — they publish events here; the conscious layer
    decides whether and how to act on them.

    Supports two consumption models:
    1. drain() / get_pending() — polling at safe points (original model)
    2. subscribe() — callback-based notification (new model)
    """

    def __init__(self, max_size: int = 100):
        self._queue: asyncio.Queue[AttentionEvent] = asyncio.Queue(maxsize=max_size)
        self._dropped = 0
        # Subscribers: map event_type → list of async callbacks
        self._subscribers: Dict[str, List[SubscriberCallback]] = {}

    async def publish(self, event: AttentionEvent) -> None:
        """Publish an event. Non-blocking; drops if queue full."""
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            self._dropped += 1
            logger.debug(
                f"EventBus dropped {event.type} from {event.source} (queue full)"
            )

        # Notify inline subscribers
        callbacks = self._subscribers.get(event.type, [])
        if callbacks:
            for cb in callbacks:
                try:
                    asyncio.create_task(cb(event))
                except Exception as exc:
                    logger.warning(f"EventBus subscriber error: {exc}")

    def subscribe(
        self,
        event_types: List[str],
        callback: SubscriberCallback,
    ) -> None:
        """
        Subscribe to one or more event types.

        The callback is called (as a background task) every time a matching
        event is published. Subconscious processes MUST NOT call speech from
        inside these callbacks — only queue further events or update state.

        Args:
            event_types: List of EventType values (strings) to subscribe to
            callback: Async callable(event) → None
        """
        for et in event_types:
            self._subscribers.setdefault(et, []).append(callback)

    def unsubscribe(self, event_types: List[str], callback: SubscriberCallback) -> None:
        """Remove a previously registered subscriber."""
        for et in event_types:
            subs = self._subscribers.get(et, [])
            if callback in subs:
                subs.remove(callback)

    def drain(self, max_items: int = 10) -> List[AttentionEvent]:
        """Synchronously drain pending events (polling model)."""
        events: List[AttentionEvent] = []
        while len(events) < max_items:
            try:
                events.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        return events

    async def get_pending(self, max_items: int = 10) -> List[AttentionEvent]:
        """Async version of drain for use in async contexts."""
        return self.drain(max_items)

    async def wait_for_event(
        self,
        event_type: Optional[str] = None,
        timeout: float = 5.0,
    ) -> Optional[AttentionEvent]:
        """
        Wait for the next event (optionally of a specific type).

        Args:
            event_type: If set, only return events of this type
            timeout: Max seconds to wait

        Returns:
            AttentionEvent or None if timeout
        """
        try:
            if event_type is None:
                return await asyncio.wait_for(self._queue.get(), timeout=timeout)
            # For typed wait we poll briefly
            deadline = asyncio.get_event_loop().time() + timeout
            while asyncio.get_event_loop().time() < deadline:
                try:
                    event = self._queue.get_nowait()
                    if event.type == event_type:
                        return event
                    # Put it back (approximate — may reorder; acceptable for attention)
                    await self.publish(event)
                except asyncio.QueueEmpty:
                    await asyncio.sleep(0.02)
            return None
        except asyncio.TimeoutError:
            return None

    def stats(self) -> Dict[str, Any]:
        return {
            "queued": self._queue.qsize(),
            "dropped": self._dropped,
            "max_size": self._queue.maxsize,
            "subscriber_count": sum(len(v) for v in self._subscribers.values()),
            "subscribed_event_types": list(self._subscribers.keys()),
        }


# Module-level singleton
_event_bus: Optional[AttentionEventBus] = None


def get_event_bus() -> AttentionEventBus:
    """Get the global AttentionEventBus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = AttentionEventBus()
    return _event_bus
