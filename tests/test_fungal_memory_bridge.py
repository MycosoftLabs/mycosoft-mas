"""
Tests for Fungal Memory Bridge.

Validates:
  - Memristive state tracking and hysteresis computation
  - Biological bookmark creation and querying
  - Pattern consolidation logic
  - Hysteresis reporting
"""

from datetime import datetime, timezone

import pytest

from mycosoft_mas.memory.fungal_memory_bridge import (
    BiologicalBookmark,
    FungalMemoryBridge,
    MemristiveState,
)


class TestMemristiveState:
    """Test memristive state tracking."""

    def test_init(self):
        state = MemristiveState(channel_id="ch0")
        assert state.channel_id == "ch0"
        assert state.resistance_estimate == 1.0
        assert state.hysteresis_score == 0.0

    def test_update(self):
        state = MemristiveState(channel_id="ch0")
        state.update(stimulus=2.0, response=1.0)
        assert state.resistance_estimate == 2.0
        assert len(state.stimulation_history) == 1
        assert len(state.response_history) == 1

    def test_update_zero_response(self):
        """Zero response should not crash resistance calculation."""
        state = MemristiveState(channel_id="ch0")
        state.update(stimulus=2.0, response=0.0)
        # Resistance stays at default when response is zero
        assert state.resistance_estimate == 1.0

    def test_hysteresis_insufficient_data(self):
        """Less than 4 samples should return 0 hysteresis."""
        state = MemristiveState(channel_id="ch0")
        state.update(1.0, 0.5)
        state.update(2.0, 1.0)
        assert state.compute_hysteresis() == 0.0

    def test_hysteresis_with_memory_effect(self):
        """Ascending vs descending should show hysteresis."""
        state = MemristiveState(channel_id="ch0")
        # Ascending stimulus
        for i in range(10):
            state.update(stimulus=float(i), response=float(i) * 0.5)
        # Descending stimulus with different response ratio (hysteresis)
        for i in range(10, 0, -1):
            state.update(stimulus=float(i), response=float(i) * 0.8)

        score = state.compute_hysteresis()
        assert score > 0.0  # Should detect memory effect

    def test_hysteresis_no_memory_effect(self):
        """Identical ascending/descending response should show low hysteresis."""
        state = MemristiveState(channel_id="ch0")
        # Same response ratio in both directions
        for i in range(10):
            state.update(stimulus=float(i), response=float(i) * 0.5)
        for i in range(10, 0, -1):
            state.update(stimulus=float(i), response=float(i) * 0.5)

        score = state.compute_hysteresis()
        assert score < 0.2  # Should be low

    def test_to_dict(self):
        state = MemristiveState(channel_id="ch0")
        state.update(1.0, 0.5)
        d = state.to_dict()
        assert d["channel_id"] == "ch0"
        assert d["sample_count"] == 1


class TestBiologicalBookmark:
    """Test bookmark data class."""

    def test_to_dict(self):
        bm = BiologicalBookmark(
            bookmark_id="bm1",
            timestamp=datetime(2026, 3, 9, tzinfo=timezone.utc),
            channel_id="ch0",
            from_state="baseline",
            to_state="active_growth",
            significance=0.8,
        )
        d = bm.to_dict()
        assert d["bookmark_id"] == "bm1"
        assert d["from_state"] == "baseline"
        assert d["to_state"] == "active_growth"
        assert d["significance"] == 0.8


class TestFungalMemoryBridge:
    """Test the bridge itself."""

    def test_init(self):
        bridge = FungalMemoryBridge()
        assert bridge._memristive_states == {}
        assert bridge._bookmarks == []

    def test_track_memristive_state(self):
        bridge = FungalMemoryBridge()
        state = bridge.track_memristive_state("ch0", 2.0, 1.0)
        assert state.channel_id == "ch0"
        assert state.resistance_estimate == 2.0

    def test_track_memristive_state_multiple(self):
        bridge = FungalMemoryBridge()
        bridge.track_memristive_state("ch0", 1.0, 0.5)
        bridge.track_memristive_state("ch0", 2.0, 1.0)
        assert len(bridge._memristive_states["ch0"].stimulation_history) == 2

    @pytest.mark.asyncio
    async def test_create_bookmark_no_coordinator(self):
        """Create bookmark without memory coordinator (standalone mode)."""
        bridge = FungalMemoryBridge()
        bm = await bridge.create_biological_bookmark(
            channel_id="ch0",
            from_state="baseline",
            to_state="active_growth",
            significance=0.7,
        )
        assert bm.channel_id == "ch0"
        assert bm.from_state == "baseline"
        assert bm.to_state == "active_growth"
        assert bm.digital_memory_ref is None  # No coordinator
        assert len(bridge._bookmarks) == 1

    @pytest.mark.asyncio
    async def test_query_bookmarks(self):
        bridge = FungalMemoryBridge()
        await bridge.create_biological_bookmark("ch0", "a", "b", 0.5)
        await bridge.create_biological_bookmark("ch1", "c", "d", 0.9)
        await bridge.create_biological_bookmark("ch0", "e", "f", 0.3)

        # Query all
        all_bm = bridge.query_biological_memory()
        assert len(all_bm) == 3

        # Filter by channel
        ch0_bm = bridge.query_biological_memory(channel_id="ch0")
        assert len(ch0_bm) == 2

        # Filter by significance
        high_bm = bridge.query_biological_memory(min_significance=0.8)
        assert len(high_bm) == 1
        assert high_bm[0].channel_id == "ch1"

    def test_hysteresis_report(self):
        bridge = FungalMemoryBridge()
        bridge.track_memristive_state("ch0", 1.0, 0.5)
        bridge.track_memristive_state("ch1", 2.0, 1.0)

        report = bridge.get_hysteresis_report()
        assert report["summary"]["total_channels"] == 2
        assert "ch0" in report["channels"]
        assert "ch1" in report["channels"]

    @pytest.mark.asyncio
    async def test_pattern_frequency_tracking(self):
        bridge = FungalMemoryBridge()
        # Same transition multiple times
        for _ in range(3):
            await bridge.create_biological_bookmark("ch0", "baseline", "growth", 0.5)

        assert bridge._pattern_counts["baseline->growth"] == 3

    @pytest.mark.asyncio
    async def test_consolidate_no_coordinator(self):
        """Consolidation without coordinator should consolidate 0 patterns."""
        bridge = FungalMemoryBridge()
        for _ in range(10):
            await bridge.create_biological_bookmark("ch0", "baseline", "growth", 0.5)

        count = await bridge.consolidate_to_semantic()
        assert count == 0  # No coordinator to store in

    def test_get_summary(self):
        bridge = FungalMemoryBridge()
        bridge.track_memristive_state("ch0", 1.0, 0.5)
        summary = bridge.get_summary()
        assert summary["memristive_channels"] == 1
        assert summary["total_bookmarks"] == 0
