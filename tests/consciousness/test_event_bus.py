"""
Tests for AttentionEventBus - Full-Duplex Voice Phase 5.

Created: February 12, 2026
"""

import pytest

from mycosoft_mas.consciousness.event_bus import AttentionEvent, AttentionEventBus


class TestAttentionEventBus:
    @pytest.mark.asyncio
    async def test_publish_and_drain(self):
        bus = AttentionEventBus(max_size=10)
        await bus.publish(AttentionEvent(type="pattern_detected", source="test", data={"count": 1}))
        await bus.publish(AttentionEvent(type="world_update", source="test", data={"ok": True}))
        drained = bus.drain(max_items=10)
        assert len(drained) == 2
        assert drained[0].type == "pattern_detected"
        assert drained[1].type == "world_update"

    @pytest.mark.asyncio
    async def test_queue_drop_when_full(self):
        bus = AttentionEventBus(max_size=1)
        await bus.publish(AttentionEvent(type="a", source="s", data={}))
        await bus.publish(AttentionEvent(type="b", source="s", data={}))
        stats = bus.stats()
        assert stats["queued"] == 1
        assert stats["dropped"] >= 1

