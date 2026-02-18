"""
Attention event bus for conscious/subconscious separation.

Phase 5: publish + drain only (simple queue model).
Created: February 12, 2026
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List


@dataclass
class AttentionEvent:
    type: str
    source: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AttentionEventBus:
    """
    Simple queue-based event bus.

    Subconscious processes publish events.
    Conscious layer drains events at safe points.
    """

    def __init__(self, max_size: int = 100):
        self._queue: asyncio.Queue[AttentionEvent] = asyncio.Queue(maxsize=max_size)
        self._dropped = 0

    async def publish(self, event: AttentionEvent) -> None:
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            self._dropped += 1

    def drain(self, max_items: int = 10) -> List[AttentionEvent]:
        events: List[AttentionEvent] = []
        while len(events) < max_items:
            try:
                events.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        return events

    def stats(self) -> Dict[str, Any]:
        return {
            "queued": self._queue.qsize(),
            "dropped": self._dropped,
            "max_size": self._queue.maxsize,
        }

