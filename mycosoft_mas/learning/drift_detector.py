"""
Concept Drift Detector for Biospheric Telemetry.

Detects when sensor data distributions shift significantly over time,
indicating environment or model assumptions have changed.
Part of MYCA Opposable Thumb Architecture (Phase 1).

Uses sliding-window statistics and threshold-based alerts.
Created: February 17, 2026
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DriftSeverity(str, Enum):
    """Severity of detected drift."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DriftAlert:
    """A detected drift event."""

    stream_key: str
    device_id: str
    severity: DriftSeverity
    metric: str
    baseline_mean: float
    current_mean: float
    baseline_std: float
    current_std: float
    sample_count: int
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stream_key": self.stream_key,
            "device_id": self.device_id,
            "severity": self.severity.value,
            "metric": self.metric,
            "baseline_mean": self.baseline_mean,
            "current_mean": self.current_mean,
            "baseline_std": self.baseline_std,
            "current_std": self.current_std,
            "sample_count": self.sample_count,
            "detected_at": self.detected_at.isoformat(),
            "metadata": self.metadata,
        }


class DriftDetector:
    """
    Detects concept drift in telemetry streams using sliding windows.

    Maintains a baseline window and a current window. When the current
    window's statistics diverge beyond thresholds from the baseline,
    a drift alert is emitted.
    """

    def __init__(
        self,
        baseline_window_size: int = 100,
        current_window_size: int = 50,
        mean_drift_threshold: float = 2.0,
        std_drift_threshold: float = 2.0,
    ):
        self.baseline_window_size = baseline_window_size
        self.current_window_size = current_window_size
        self.mean_drift_threshold = mean_drift_threshold
        self.std_drift_threshold = std_drift_threshold
        self._streams: Dict[str, Dict[str, deque]] = {}
        self._alerts: List[DriftAlert] = []
        self._max_alerts = 100

    def _get_or_create_stream(self, stream_key: str) -> Dict[str, deque]:
        if stream_key not in self._streams:
            self._streams[stream_key] = {
                "baseline": deque(maxlen=self.baseline_window_size),
                "current": deque(maxlen=self.current_window_size),
            }
        return self._streams[stream_key]

    @staticmethod
    def _stats(values: deque) -> tuple[float, float]:
        if not values:
            return 0.0, 0.0
        nums = [v for v in values if isinstance(v, (int, float))]
        if not nums:
            return 0.0, 0.0
        n = len(nums)
        mean = sum(nums) / n
        variance = sum((x - mean) ** 2 for x in nums) / n if n > 0 else 0.0
        std = variance**0.5 if variance > 0 else 0.0
        return mean, std

    def ingest(
        self,
        stream_key: str,
        value: float,
        device_id: str = "",
        metric: str = "",
    ) -> Optional[DriftAlert]:
        """
        Ingest a telemetry sample and optionally emit a drift alert.

        Args:
            stream_key: Unique key for the stream (e.g. "mushroom1_bme1_temperature")
            value: Numeric reading
            device_id: Device identifier
            metric: Metric name (e.g. "temperature")

        Returns:
            DriftAlert if drift detected, else None
        """
        if not isinstance(value, (int, float)):
            return None

        streams = self._get_or_create_stream(stream_key)
        baseline = streams["baseline"]
        current = streams["current"]

        current.append(value)
        if len(baseline) < self.baseline_window_size:
            baseline.append(value)
            return None

        baseline_mean, baseline_std = self._stats(baseline)
        current_mean, current_std = self._stats(current)

        if len(current) < self.current_window_size:
            return None

        mean_diff = abs(current_mean - baseline_mean)
        std_baseline = baseline_std if baseline_std > 0 else 1e-6
        std_diff = abs(current_std - baseline_std) / std_baseline if baseline_std > 0 else 0

        mean_sigma = mean_diff / std_baseline if std_baseline > 0 else 0

        severity = DriftSeverity.LOW
        if mean_sigma >= self.mean_drift_threshold or std_diff >= self.std_drift_threshold:
            if mean_sigma >= 4.0 or std_diff >= 3.0:
                severity = DriftSeverity.CRITICAL
            elif mean_sigma >= 3.0 or std_diff >= 2.5:
                severity = DriftSeverity.HIGH
            elif mean_sigma >= 2.5 or std_diff >= 2.0:
                severity = DriftSeverity.MEDIUM

            alert = DriftAlert(
                stream_key=stream_key,
                device_id=device_id,
                severity=severity,
                metric=metric or stream_key.split("_")[-1] if "_" in stream_key else "value",
                baseline_mean=baseline_mean,
                current_mean=current_mean,
                baseline_std=baseline_std,
                current_std=current_std,
                sample_count=len(current),
            )
            self._alerts.append(alert)
            if len(self._alerts) > self._max_alerts:
                self._alerts.pop(0)
            logger.info("Drift detected: %s %s sigma=%.2f", stream_key, severity.value, mean_sigma)
            return alert

        return None

    def get_recent_alerts(self, limit: int = 20) -> List[DriftAlert]:
        """Return most recent drift alerts."""
        return list(self._alerts[-limit:])

    def reset_baseline(self, stream_key: str) -> None:
        """Reset baseline for a stream (e.g. after model retrain)."""
        if stream_key in self._streams:
            base = self._streams[stream_key]["baseline"]
            current = self._streams[stream_key]["current"]
            base.clear()
            base.extend(current)
            current.clear()
