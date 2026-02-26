"""
Event boundary detection - Phase 2 stub.

V0: Rule-based. TODO: ML-based boundary detection.
Created: February 17, 2026
"""

import uuid
from datetime import datetime, timezone
from typing import Optional


def detect_event_boundary(
    session_id: Optional[str],
    last_ep_ts: Optional[datetime],
    current_ts: Optional[datetime] = None,
    idle_threshold_seconds: int = 300,
) -> tuple[bool, str]:
    """
    V0: Rule-based event boundary detection.
    Returns (is_boundary, episode_id).
    """
    now = current_ts or datetime.now(timezone.utc)
    if session_id is None or last_ep_ts is None:
        return True, str(uuid.uuid4())
    elapsed = (now - last_ep_ts).total_seconds()
    if elapsed > idle_threshold_seconds:
        return True, str(uuid.uuid4())
    return False, ""
