"""
TemporalService - Phase 2 stub for event/episode handling.

TODO: Full implementation with TimescaleDB for temporal queries.
Created: February 17, 2026
"""

import uuid
from datetime import datetime
from typing import Any, Optional


class TemporalService:
    """Stub for temporal indexing and event boundaries."""

    def should_start_episode(
        self,
        session_id: Optional[str],
        last_ep_ts: Optional[datetime],
        current_ts: datetime,
        idle_threshold_seconds: int = 300,
    ) -> bool:
        """V0: Rule-based event boundary. True if we should start a new episode."""
        if session_id is None:
            return True
        if last_ep_ts is None:
            return True
        return (current_ts - last_ep_ts).total_seconds() > idle_threshold_seconds

    def new_episode_id(self) -> str:
        """Generate a new episode ID."""
        return str(uuid.uuid4())
