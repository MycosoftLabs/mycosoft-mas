"""
Voice v9 Latency Monitor - March 2, 2026.

Tracks latency for voice turns and operations.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

from mycosoft_mas.voice_v9.schemas import LatencyTrace

logger = None  # Lazy init to avoid circular imports


def _log():
    global logger
    if logger is None:
        import logging

        logger = logging.getLogger("voice_v9.latency_monitor")
    return logger


class LatencyMonitor:
    """Tracks and stores latency traces for v9 voice operations."""

    def __init__(self) -> None:
        self._traces: Dict[str, List[LatencyTrace]] = {}

    def record(
        self,
        session_id: str,
        operation: str,
        start_ts: str,
        end_ts: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> LatencyTrace:
        """Record a latency trace. If end_ts is None, uses now."""
        end = end_ts or datetime.now(timezone.utc).isoformat()
        start_dt = datetime.fromisoformat(start_ts.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
        duration_ms = (end_dt - start_dt).total_seconds() * 1000.0

        trace = LatencyTrace(
            session_id=session_id,
            operation=operation,
            start_ts=start_ts,
            end_ts=end,
            duration_ms=duration_ms,
            metadata=metadata or {},
        )

        if session_id not in self._traces:
            self._traces[session_id] = []
        self._traces[session_id].append(trace)
        _log().debug("Latency trace: %s %s %.1fms", session_id, operation, duration_ms)
        return trace

    def get_traces(self, session_id: str, limit: int = 50) -> List[LatencyTrace]:
        """Return recent traces for a session."""
        if session_id not in self._traces:
            return []
        return list(reversed(self._traces[session_id][-limit:]))

    def clear_session(self, session_id: str) -> None:
        """Clear traces for a session."""
        self._traces.pop(session_id, None)


# Singleton for app-wide use
_monitor: Optional[LatencyMonitor] = None


def get_latency_monitor() -> LatencyMonitor:
    global _monitor
    if _monitor is None:
        _monitor = LatencyMonitor()
    return _monitor
