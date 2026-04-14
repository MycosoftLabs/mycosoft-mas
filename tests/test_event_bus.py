"""
Tests for AttentionEventBus.

Key invariant tested: subconscious processes MUST NOT call speech methods
directly — they must publish events; the conscious layer decides how to act.

Tests cover:
- publish() puts events in the queue
- drain() / get_pending() retrieves events
- subscribe() callbacks are called on publish
- Backpressure: queue full drops events gracefully
- wait_for_event() returns correct event or times out
- EventType enum covers all expected types
- Singleton get_event_bus()

Author: MYCA / Consciousness OS
Created: April 2026
"""

import asyncio
from datetime import datetime
from typing import List

import pytest

from mycosoft_mas.consciousness.event_bus import (
    AttentionEvent,
    AttentionEventBus,
    EventType,
    get_event_bus,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _event(
    event_type: str = EventType.WORLD_ANOMALY,
    source: str = "test",
    data: dict = None,
    priority: int = 5,
) -> AttentionEvent:
    return AttentionEvent(
        type=event_type,
        source=source,
        data=data or {"value": 42},
        priority=priority,
    )


# ---------------------------------------------------------------------------
# Basic publish / drain
# ---------------------------------------------------------------------------


class TestAttentionEventBus:
    @pytest.mark.asyncio
    async def test_publish_and_drain(self):
        """Published events should be retrievable via drain()."""
        bus = AttentionEventBus(max_size=10)
        await bus.publish(_event("world_anomaly"))
        await bus.publish(_event("agent_status"))

        events = bus.drain(max_items=10)
        assert len(events) == 2
        assert events[0].type == "world_anomaly"
        assert events[1].type == "agent_status"

    @pytest.mark.asyncio
    async def test_drain_empty_returns_empty(self):
        bus = AttentionEventBus()
        events = bus.drain()
        assert events == []

    @pytest.mark.asyncio
    async def test_get_pending_async(self):
        """get_pending() (async) should behave identically to drain()."""
        bus = AttentionEventBus()
        await bus.publish(_event())
        events = await bus.get_pending()
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_drain_respects_max_items(self):
        """drain(max_items=2) should return at most 2 events."""
        bus = AttentionEventBus(max_size=20)
        for _ in range(5):
            await bus.publish(_event())
        events = bus.drain(max_items=2)
        assert len(events) == 2
        # Remaining 3 should still be in queue
        remaining = bus.drain(max_items=10)
        assert len(remaining) == 3

    # ---------------------------------------------------------------------------
    # Backpressure
    # ---------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_queue_full_drops_gracefully(self):
        """When the queue is full, publish() should drop without raising."""
        bus = AttentionEventBus(max_size=3)
        for _ in range(10):
            await bus.publish(_event())  # Must not raise

        stats = bus.stats()
        assert stats["dropped"] >= 7
        assert stats["queued"] == 3

    # ---------------------------------------------------------------------------
    # Subscribe / callback invariant
    # ---------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_subscribe_callback_called(self):
        """A subscriber callback should be called when a matching event is published."""
        bus = AttentionEventBus()
        received: List[AttentionEvent] = []

        async def handler(event: AttentionEvent):
            received.append(event)

        bus.subscribe([EventType.WORLD_ANOMALY], handler)
        await bus.publish(_event(EventType.WORLD_ANOMALY))
        await asyncio.sleep(0.05)  # Allow task to execute
        assert len(received) == 1
        assert received[0].type == EventType.WORLD_ANOMALY

    @pytest.mark.asyncio
    async def test_subscribe_callback_not_called_for_other_type(self):
        """Callback should NOT be called for non-subscribed event types."""
        bus = AttentionEventBus()
        received: List[AttentionEvent] = []

        async def handler(event: AttentionEvent):
            received.append(event)

        bus.subscribe([EventType.WORLD_ANOMALY], handler)
        await bus.publish(_event(EventType.AGENT_STATUS))  # Different type
        await asyncio.sleep(0.05)
        assert received == []

    @pytest.mark.asyncio
    async def test_unsubscribe_stops_callbacks(self):
        """After unsubscribe, callback should no longer be called."""
        bus = AttentionEventBus()
        received: List[AttentionEvent] = []

        async def handler(event: AttentionEvent):
            received.append(event)

        bus.subscribe([EventType.PATTERN_DETECTED], handler)
        bus.unsubscribe([EventType.PATTERN_DETECTED], handler)
        await bus.publish(_event(EventType.PATTERN_DETECTED))
        await asyncio.sleep(0.05)
        assert received == []

    # ---------------------------------------------------------------------------
    # Subconscious invariant: no direct speech
    # ---------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_subconscious_cannot_speak_directly(self):
        """
        INVARIANT: Subconscious processes must publish events, not speak.

        This test verifies the design contract: if a subconscious process
        tries to access a speech method through the event bus, it should
        not find one (the bus has no speak/yield methods).
        """
        bus = AttentionEventBus()
        # The bus must NOT have speech methods
        assert not hasattr(bus, "speak")
        assert not hasattr(bus, "say")
        assert not hasattr(bus, "yield_speech")
        assert not hasattr(bus, "tts")

    # ---------------------------------------------------------------------------
    # wait_for_event
    # ---------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_wait_for_event_returns_on_match(self):
        """wait_for_event() should return when a matching event is published."""
        bus = AttentionEventBus()

        async def delayed_publish():
            await asyncio.sleep(0.05)
            await bus.publish(_event(EventType.MEMORY_SUGGESTION))

        asyncio.create_task(delayed_publish())
        event = await bus.wait_for_event(
            event_type=EventType.MEMORY_SUGGESTION, timeout=1.0
        )
        assert event is not None
        assert event.type == EventType.MEMORY_SUGGESTION

    @pytest.mark.asyncio
    async def test_wait_for_event_times_out(self):
        """wait_for_event() should return None if no event arrives in time."""
        bus = AttentionEventBus()
        result = await bus.wait_for_event(event_type="nonexistent_type", timeout=0.05)
        assert result is None

    # ---------------------------------------------------------------------------
    # Stats
    # ---------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_stats_reflect_state(self):
        bus = AttentionEventBus(max_size=5)
        await bus.publish(_event())
        stats = bus.stats()
        assert stats["queued"] == 1
        assert stats["dropped"] == 0
        assert stats["max_size"] == 5

    # ---------------------------------------------------------------------------
    # EventType enum
    # ---------------------------------------------------------------------------

    def test_event_types_exist(self):
        """All expected event types should be defined."""
        expected = [
            "world_anomaly",
            "pattern_detected",
            "memory_suggestion",
            "agent_status",
            "tool_progress",
        ]
        for et in expected:
            assert et in [e.value for e in EventType], f"Missing EventType: {et}"

    # ---------------------------------------------------------------------------
    # Singleton
    # ---------------------------------------------------------------------------

    def test_singleton(self):
        a = get_event_bus()
        b = get_event_bus()
        assert a is b
