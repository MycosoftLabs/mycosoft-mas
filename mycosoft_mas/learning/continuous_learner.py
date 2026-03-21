"""
Continuous Learner - Closed-Loop Science Pipeline.

Observe (telemetry) → Process (NLM) → Detect drift → Learn (update patterns).
Part of MYCA Opposable Thumb Architecture (Phase 1).

Created: February 17, 2026
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from mycosoft_mas.learning.drift_detector import DriftAlert, DriftDetector

logger = logging.getLogger(__name__)


@dataclass
class LearningCycleResult:
    """Result of a single learning cycle."""

    samples_processed: int = 0
    drift_alerts: List[DriftAlert] = field(default_factory=list)
    nlm_processed: bool = False
    patterns_updated: bool = False
    cycle_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "samples_processed": self.samples_processed,
            "drift_alerts_count": len(self.drift_alerts),
            "drift_alerts": [a.to_dict() for a in self.drift_alerts],
            "nlm_processed": self.nlm_processed,
            "patterns_updated": self.patterns_updated,
            "cycle_at": self.cycle_at.isoformat(),
            "errors": self.errors,
        }


class ContinuousLearner:
    """
    Closed-loop learner: ingests telemetry, runs drift detection,
    and optionally feeds NLM / temporal patterns.
    """

    def __init__(
        self,
        drift_detector: Optional[DriftDetector] = None,
        nlm_process_fn: Optional[Callable[[Dict[str, Any]], Any]] = None,
        patterns_update_fn: Optional[Callable[[List[DriftAlert]], Any]] = None,
    ):
        self._drift = drift_detector or DriftDetector()
        self._nlm_process = nlm_process_fn
        self._patterns_update = patterns_update_fn
        self._last_result: Optional[LearningCycleResult] = None

    def process_telemetry_batch(
        self,
        telemetry: List[Dict[str, Any]],
    ) -> LearningCycleResult:
        """
        Process a batch of telemetry readings through the learning pipeline.

        Each item in telemetry should have: device_id, stream_key or sensor data,
        and numeric values (temperature, humidity, etc.).
        """
        result = LearningCycleResult()

        for item in telemetry:
            if not isinstance(item, dict):
                continue

            device_id = str(item.get("device_id", item.get("device_slug", "")))
            data = item.get("telemetry", item.get("data", item))

            if isinstance(data, dict):
                for sensor_key, sensor_data in data.items():
                    if not isinstance(sensor_data, dict):
                        continue
                    for metric, val in sensor_data.items():
                        if metric == "type":
                            continue
                        if isinstance(val, (int, float)):
                            stream_key = f"{device_id}_{sensor_key}_{metric}".replace(
                                " ", "-"
                            ).lower()
                            alert = self._drift.ingest(
                                stream_key=stream_key,
                                value=val,
                                device_id=device_id,
                                metric=metric,
                            )
                            if alert:
                                result.drift_alerts.append(alert)
                            result.samples_processed += 1

        if result.drift_alerts and self._patterns_update:
            try:
                self._patterns_update(result.drift_alerts)
                result.patterns_updated = True
            except Exception as e:
                result.errors.append(str(e))
                logger.warning("Patterns update failed: %s", e)

        if telemetry and self._nlm_process:
            try:
                self._nlm_process({"batch": telemetry, "result": result.to_dict()})
                result.nlm_processed = True
            except Exception as e:
                result.errors.append(str(e))
                logger.warning("NLM process failed: %s", e)

        self._last_result = result
        return result

    def get_last_result(self) -> Optional[LearningCycleResult]:
        """Return the result of the last learning cycle."""
        return self._last_result

    def get_drift_detector(self) -> DriftDetector:
        """Access the underlying drift detector."""
        return self._drift
