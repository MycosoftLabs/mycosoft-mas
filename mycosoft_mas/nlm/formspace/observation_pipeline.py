"""Causal observation pipeline: four times, cutoff, one physical reading."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set

from .contracts import ObservationEnvelope


class CausalObservationPipeline:
    def __init__(self) -> None:
        self._consumed: Set[str] = set()
        self._results: Dict[str, Dict[str, Any]] = {}

    def process(
        self,
        envelope: ObservationEnvelope,
        cutoff: datetime,
        recorded_at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        if cutoff.tzinfo is None:
            cutoff = cutoff.replace(tzinfo=timezone.utc)
        if envelope.available_at > cutoff:
            return {
                "status": "excluded_future_available_at",
                "observation_id": envelope.observation_id,
                "root_evidence_id": envelope.root_evidence_id,
                "consumed": False,
                "note": "M07: available_at after cutoff is excluded even if event_time is earlier.",
            }
        if envelope.root_evidence_id in self._consumed:
            original = self._results[envelope.root_evidence_id]
            return {
                "status": "duplicate_root_evidence",
                "observation_id": envelope.observation_id,
                "root_evidence_id": envelope.root_evidence_id,
                "consumed": False,
                "original": original,
                "note": "M06: the same physical reading updates the filter once.",
            }
        stamp = recorded_at or datetime.now(timezone.utc)
        committed = {
            "status": "accepted",
            "observation_id": envelope.observation_id,
            "root_evidence_id": envelope.root_evidence_id,
            "event_time": envelope.event_time.isoformat(),
            "received_at": envelope.received_at.isoformat(),
            "available_at": envelope.available_at.isoformat(),
            "recorded_at": stamp.isoformat(),
            "input_cutoff_at": cutoff.isoformat(),
            "chart_id": envelope.chart_id,
            "chart_version": envelope.chart_version,
            "consumed": True,
            "likelihood_applied": True,
            "scores": None,
            "note": "Accepted into the causal stream. No invented ecology p.",
        }
        self._consumed.add(envelope.root_evidence_id)
        self._results[envelope.root_evidence_id] = committed
        return committed


_PIPELINE: Optional[CausalObservationPipeline] = None


def get_observation_pipeline() -> CausalObservationPipeline:
    global _PIPELINE
    if _PIPELINE is None:
        _PIPELINE = CausalObservationPipeline()
    return _PIPELINE
