"""
Temporal Pattern Storage for Long-Term Sensor Patterns.

Stores and retrieves patterns (daily cycles, seasonal, anomalies) from
telemetry streams. Used by drift detector and continuous learner.
Part of MYCA Opposable Thumb Architecture (Phase 1).

Created: February 17, 2026
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TemporalPattern:
    """A stored temporal pattern (e.g. daily mean, anomaly)."""
    stream_key: str
    pattern_type: str
    hour_of_day: Optional[int] = None
    day_of_week: Optional[int] = None
    mean: float = 0.0
    std: float = 0.0
    sample_count: int = 0
    first_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stream_key": self.stream_key,
            "pattern_type": self.pattern_type,
            "hour_of_day": self.hour_of_day,
            "day_of_week": self.day_of_week,
            "mean": self.mean,
            "std": self.std,
            "sample_count": self.sample_count,
            "first_seen": self.first_seen.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "metadata": self.metadata,
        }


class TemporalPatternStore:
    """
    In-memory store for temporal patterns with optional file persistence.
    """

    def __init__(self, persist_path: Optional[Path] = None):
        self._patterns: Dict[str, List[TemporalPattern]] = defaultdict(list)
        self._persist_path = persist_path or Path("data/temporal_patterns.json")

    def add_pattern(self, pattern: TemporalPattern) -> None:
        """Add or update a pattern for a stream."""
        key = pattern.stream_key
        existing = [p for p in self._patterns[key] if self._matches(p, pattern)]
        if existing:
            existing[0].mean = (existing[0].mean * existing[0].sample_count + pattern.mean * pattern.sample_count) / (
                existing[0].sample_count + pattern.sample_count
            )
            existing[0].sample_count += pattern.sample_count
            existing[0].last_updated = datetime.now(timezone.utc)
        else:
            self._patterns[key].append(pattern)

    def _matches(self, a: TemporalPattern, b: TemporalPattern) -> bool:
        return (
            a.pattern_type == b.pattern_type
            and a.hour_of_day == b.hour_of_day
            and a.day_of_week == b.day_of_week
        )

    def get_patterns(
        self,
        stream_key: str,
        pattern_type: Optional[str] = None,
        hour_of_day: Optional[int] = None,
    ) -> List[TemporalPattern]:
        """Retrieve patterns for a stream with optional filters."""
        patterns = self._patterns.get(stream_key, [])
        if pattern_type:
            patterns = [p for p in patterns if p.pattern_type == pattern_type]
        if hour_of_day is not None:
            patterns = [p for p in patterns if p.hour_of_day == hour_of_day]
        return patterns

    def update_from_drift_alerts(self, alerts: List[Any]) -> None:
        """
        Update patterns from drift alerts (e.g. new baseline after drift).
        """
        now = datetime.now(timezone.utc)
        for alert in alerts:
            if hasattr(alert, "stream_key") and hasattr(alert, "current_mean"):
                pattern = TemporalPattern(
                    stream_key=alert.stream_key,
                    pattern_type="post_drift_baseline",
                    mean=alert.current_mean,
                    std=getattr(alert, "current_std", 0.0),
                    sample_count=getattr(alert, "sample_count", 0),
                    last_updated=now,
                    metadata={"device_id": getattr(alert, "device_id", "")},
                )
                self.add_pattern(pattern)

    def save(self) -> None:
        """Persist patterns to file."""
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                k: [p.to_dict() for p in v]
                for k, v in self._patterns.items()
            }
            self._persist_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("Failed to save temporal patterns: %s", e)

    def load(self) -> None:
        """Load patterns from file."""
        if not self._persist_path.exists():
            return
        try:
            data = json.loads(self._persist_path.read_text(encoding="utf-8"))
            for stream_key, pattern_dicts in data.items():
                for d in pattern_dicts:
                    p = TemporalPattern(
                        stream_key=d.get("stream_key", stream_key),
                        pattern_type=d.get("pattern_type", "unknown"),
                        hour_of_day=d.get("hour_of_day"),
                        day_of_week=d.get("day_of_week"),
                        mean=d.get("mean", 0.0),
                        std=d.get("std", 0.0),
                        sample_count=d.get("sample_count", 0),
                        metadata=d.get("metadata", {}),
                    )
                    self._patterns[stream_key].append(p)
        except Exception as e:
            logger.warning("Failed to load temporal patterns: %s", e)
