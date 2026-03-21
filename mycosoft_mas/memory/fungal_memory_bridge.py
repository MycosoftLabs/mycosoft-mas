"""
Fungal Memory Bridge — Biological ↔ Digital Memory Integration

Connects biological memory phenomena (memristive behavior, hysteresis,
state-dependent recall) with MYCA's 6-layer digital memory system.

Key concepts:
  * Memristive state tracking: fungal channels whose response depends on
    their stimulation history (resistance = f(voltage history)).
  * Biological bookmarks: significant state-change moments in the fungal
    network, stored as episodic memories in MYCA's memory system.
  * Pattern consolidation: recurring biological patterns promoted from
    episodic to semantic memory (transient → permanent knowledge).

Uses existing MemoryCoordinator — does NOT create a 7th memory layer.

Created: March 9, 2026
(c) 2026 Mycosoft Labs
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class MemristiveState:
    """
    Tracks memristive (history-dependent) state of a fungal channel.

    Fungal memristors: biological circuits whose resistance depends on
    prior voltage history. This class tracks the stimulus/response
    relationship and computes a hysteresis score indicating how much
    the current response depends on stimulation history.
    """

    channel_id: str
    stimulation_history: deque = field(default_factory=lambda: deque(maxlen=200))
    response_history: deque = field(default_factory=lambda: deque(maxlen=200))
    resistance_estimate: float = 1.0
    hysteresis_score: float = 0.0
    _last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def update(self, stimulus: float, response: float) -> None:
        """Record a stimulus-response pair and update resistance estimate."""
        self.stimulation_history.append(stimulus)
        self.response_history.append(response)
        self._last_updated = datetime.now(timezone.utc)

        # Update resistance estimate (R = stimulus / response, avoiding div/0)
        if abs(response) > 1e-10:
            self.resistance_estimate = abs(stimulus / response)
        # Recompute hysteresis
        self.hysteresis_score = self.compute_hysteresis()

    def compute_hysteresis(self) -> float:
        """
        Compute hysteresis score: how much the current response differs
        from what a memoryless system would produce.

        Returns 0.0 (no memory effect) to 1.0 (strong history dependence).
        """
        stims = list(self.stimulation_history)
        resps = list(self.response_history)
        n = min(len(stims), len(resps))
        if n < 4:
            return 0.0

        # Compare ascending vs descending response for similar stimuli
        # A true memristor shows different R for same stimulus depending
        # on whether stimulus is increasing or decreasing.
        ascending_resps: List[float] = []
        descending_resps: List[float] = []

        for i in range(1, n):
            if stims[i] > stims[i - 1]:
                ascending_resps.append(resps[i])
            elif stims[i] < stims[i - 1]:
                descending_resps.append(resps[i])

        if not ascending_resps or not descending_resps:
            return 0.0

        asc_mean = sum(ascending_resps) / len(ascending_resps)
        desc_mean = sum(descending_resps) / len(descending_resps)
        overall_mean = sum(resps) / n

        if abs(overall_mean) < 1e-10:
            return 0.0

        # Hysteresis = normalized difference between ascending and descending
        raw = abs(asc_mean - desc_mean) / (abs(overall_mean) + 1e-10)
        return min(1.0, raw)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "resistance_estimate": self.resistance_estimate,
            "hysteresis_score": self.hysteresis_score,
            "sample_count": len(self.stimulation_history),
            "last_updated": self._last_updated.isoformat(),
        }


@dataclass
class BiologicalBookmark:
    """
    A moment when fungal signals indicate a significant state change.

    Bookmarks are the bridge between biological events and MYCA's
    episodic memory. Each bookmark stores:
      - The biological state at the moment of transition
      - A reference to the digital memory entry it was stored as
      - A significance score for memory consolidation decisions
    """

    bookmark_id: str
    timestamp: datetime
    channel_id: str
    from_state: str
    to_state: str
    fungal_state_snapshot: Dict[str, Any] = field(default_factory=dict)
    digital_memory_ref: Optional[str] = None
    significance: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bookmark_id": self.bookmark_id,
            "timestamp": self.timestamp.isoformat(),
            "channel_id": self.channel_id,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "fungal_state_snapshot": self.fungal_state_snapshot,
            "digital_memory_ref": self.digital_memory_ref,
            "significance": self.significance,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Fungal Memory Bridge
# ---------------------------------------------------------------------------


class FungalMemoryBridge:
    """
    Bridges biological memory traces with MYCA's 6-layer digital memory.

    Responsibilities:
      1. Track memristive state for each FCI channel
      2. Create biological bookmarks on state transitions
      3. Store bookmarks as episodic memories via MemoryCoordinator
      4. Consolidate recurring patterns to semantic memory
      5. Provide hysteresis reports for research / benchmarking

    Integration points:
      - MemoryCoordinator.record_episode() for bookmark → episodic
      - MemoryCoordinator.agent_remember() for pattern → semantic
      - StateTransition from LiquidTemporalProcessor triggers bookmarks
    """

    AGENT_ID = "fungal_memory_bridge"

    def __init__(self, memory_coordinator=None, mindex_url: Optional[str] = None):
        self._coordinator = memory_coordinator
        self._mindex_url = mindex_url
        self._memristive_states: Dict[str, MemristiveState] = {}
        self._bookmarks: List[BiologicalBookmark] = []
        # Pattern frequency tracking for consolidation
        self._pattern_counts: Dict[str, int] = {}
        self._consolidation_threshold = 5  # times seen before promoting to semantic

    # ----- memristive tracking --------------------------------------------

    def track_memristive_state(
        self,
        channel_id: str,
        stimulus: float,
        response: float,
    ) -> MemristiveState:
        """
        Update memristive tracking for a channel.

        Args:
            channel_id: FCI electrode / channel identifier.
            stimulus: Applied stimulus value (mV).
            response: Measured response value (mV).

        Returns:
            Updated MemristiveState with hysteresis score.
        """
        if channel_id not in self._memristive_states:
            self._memristive_states[channel_id] = MemristiveState(channel_id=channel_id)

        state = self._memristive_states[channel_id]
        state.update(stimulus, response)
        return state

    # ----- biological bookmarks -------------------------------------------

    async def create_biological_bookmark(
        self,
        channel_id: str,
        from_state: str,
        to_state: str,
        significance: float = 0.5,
        fungal_state_snapshot: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BiologicalBookmark:
        """
        Create a bookmark when a significant biological state change occurs.

        Stores the bookmark both locally and in MYCA's episodic memory via
        MemoryCoordinator (if available).

        Args:
            channel_id: Channel where transition occurred.
            from_state: GFST state before transition.
            to_state: GFST state after transition.
            significance: 0.0-1.0 importance score.
            fungal_state_snapshot: Current sensor / memristive state.
            metadata: Additional context.

        Returns:
            BiologicalBookmark with optional digital memory reference.
        """
        bookmark = BiologicalBookmark(
            bookmark_id=uuid4().hex[:12],
            timestamp=datetime.now(timezone.utc),
            channel_id=channel_id,
            from_state=from_state,
            to_state=to_state,
            fungal_state_snapshot=fungal_state_snapshot or {},
            significance=significance,
            metadata=metadata or {},
        )

        # Store in digital episodic memory if coordinator available
        if self._coordinator:
            try:
                mem_id = await self._coordinator.record_episode(
                    agent_id=self.AGENT_ID,
                    event_type="observation",
                    description=(
                        f"Fungal state transition on {channel_id}: "
                        f"{from_state} -> {to_state} "
                        f"(significance={significance:.2f})"
                    ),
                    context={
                        "bookmark": bookmark.to_dict(),
                        "memristive_state": (
                            self._memristive_states[channel_id].to_dict()
                            if channel_id in self._memristive_states
                            else None
                        ),
                    },
                    importance=significance,
                )
                bookmark.digital_memory_ref = str(mem_id)
            except Exception as exc:
                logger.warning("Failed to store bookmark in episodic memory: %s", exc)

        self._bookmarks.append(bookmark)

        # Track pattern frequency for consolidation
        pattern_key = f"{from_state}->{to_state}"
        self._pattern_counts[pattern_key] = self._pattern_counts.get(pattern_key, 0) + 1

        logger.info(
            "Biological bookmark created: %s on %s (sig=%.2f)",
            pattern_key,
            channel_id,
            significance,
        )
        return bookmark

    def query_biological_memory(
        self,
        channel_id: Optional[str] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        min_significance: float = 0.0,
    ) -> List[BiologicalBookmark]:
        """Query past biological bookmarks with optional filters."""
        results = self._bookmarks

        if channel_id:
            results = [b for b in results if b.channel_id == channel_id]

        if time_range:
            start, end = time_range
            results = [b for b in results if start <= b.timestamp <= end]

        if min_significance > 0:
            results = [b for b in results if b.significance >= min_significance]

        return sorted(results, key=lambda b: b.timestamp, reverse=True)

    # ----- hysteresis reporting -------------------------------------------

    def get_hysteresis_report(self) -> Dict[str, Any]:
        """Report on memristive behavior across all tracked channels."""
        channel_reports = {}
        for cid, state in self._memristive_states.items():
            channel_reports[cid] = state.to_dict()

        # Summary statistics
        scores = [s.hysteresis_score for s in self._memristive_states.values()]
        avg_hysteresis = sum(scores) / len(scores) if scores else 0.0
        max_hysteresis = max(scores) if scores else 0.0
        channels_with_memory = sum(1 for s in scores if s > 0.1)

        return {
            "channels": channel_reports,
            "summary": {
                "total_channels": len(self._memristive_states),
                "avg_hysteresis": avg_hysteresis,
                "max_hysteresis": max_hysteresis,
                "channels_with_memory_effect": channels_with_memory,
            },
            "bookmarks_total": len(self._bookmarks),
            "pattern_frequencies": dict(self._pattern_counts),
        }

    # ----- pattern consolidation ------------------------------------------

    async def consolidate_to_semantic(self) -> int:
        """
        Promote recurring biological patterns to semantic memory.

        When a state transition pattern (e.g., "baseline->active_growth")
        has been observed at least N times, it becomes permanent knowledge
        in MYCA's semantic memory layer.

        Returns:
            Number of patterns consolidated.
        """
        consolidated = 0

        for pattern_key, count in self._pattern_counts.items():
            if count < self._consolidation_threshold:
                continue

            if self._coordinator:
                try:
                    await self._coordinator.agent_remember(
                        agent_id=self.AGENT_ID,
                        content={
                            "type": "learned_biological_pattern",
                            "pattern": pattern_key,
                            "observation_count": count,
                            "description": (
                                f"Fungal state transition '{pattern_key}' "
                                f"observed {count} times. Consolidated as "
                                f"reliable biological behavior pattern."
                            ),
                        },
                        layer="semantic",
                        importance=0.7,
                        tags=[
                            "fungal_pattern",
                            "biological_memory",
                            "consolidated",
                            pattern_key,
                        ],
                    )
                    consolidated += 1
                    logger.info(
                        "Consolidated pattern '%s' (%d observations) to semantic memory",
                        pattern_key,
                        count,
                    )
                except Exception as exc:
                    logger.warning(
                        "Failed to consolidate pattern '%s': %s",
                        pattern_key,
                        exc,
                    )

        return consolidated

    # ----- summary --------------------------------------------------------

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the fungal memory bridge state."""
        return {
            "memristive_channels": len(self._memristive_states),
            "total_bookmarks": len(self._bookmarks),
            "pattern_counts": dict(self._pattern_counts),
            "consolidation_threshold": self._consolidation_threshold,
            "patterns_ready_for_consolidation": sum(
                1 for c in self._pattern_counts.values() if c >= self._consolidation_threshold
            ),
        }
