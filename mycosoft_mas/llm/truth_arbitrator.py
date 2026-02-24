"""
Sensor-grounded truth arbitrator for ensemble disagreements.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class ArbitrationCandidate:
    """One candidate answer from a finger/provider."""

    source: str
    content: str
    confidence: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ArbitrationResult:
    """Final arbitration output."""

    winner: ArbitrationCandidate
    rationale: str
    score: float
    considered: int
    decided_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "winner": {
                "source": self.winner.source,
                "content": self.winner.content,
                "confidence": self.winner.confidence,
                "metadata": self.winner.metadata,
            },
            "rationale": self.rationale,
            "score": self.score,
            "considered": self.considered,
            "decided_at": self.decided_at.isoformat(),
        }


class TruthArbitrator:
    """
    Tiebreaking using sensor-grounded confidence and evidence weighting.
    """

    def __init__(self, sensor_weight: float = 0.6, model_weight: float = 0.4) -> None:
        total = sensor_weight + model_weight
        self.sensor_weight = sensor_weight / total if total > 0 else 0.6
        self.model_weight = model_weight / total if total > 0 else 0.4

    @staticmethod
    def _evidence_score(candidate: ArbitrationCandidate, evidence: Dict[str, Any]) -> float:
        """
        Compute lightweight evidence alignment.

        If explicit per-source confidence exists in evidence, use it.
        Otherwise, fall back to neutral score.
        """
        source_scores = evidence.get("source_confidence", {}) if isinstance(evidence, dict) else {}
        if isinstance(source_scores, dict) and candidate.source in source_scores:
            try:
                return max(0.0, min(1.0, float(source_scores[candidate.source])))
            except (TypeError, ValueError):
                return 0.5
        return 0.5

    def arbitrate(
        self,
        candidates: List[ArbitrationCandidate],
        sensor_evidence: Optional[Dict[str, Any]] = None,
    ) -> ArbitrationResult:
        if not candidates:
            raise ValueError("At least one candidate is required")

        evidence = sensor_evidence or {}
        best: Optional[ArbitrationCandidate] = None
        best_score = -1.0

        for c in candidates:
            model_conf = max(0.0, min(1.0, c.confidence))
            sensor_conf = self._evidence_score(c, evidence)
            score = (self.sensor_weight * sensor_conf) + (self.model_weight * model_conf)
            if score > best_score:
                best_score = score
                best = c

        assert best is not None
        rationale = (
            f"Selected '{best.source}' using weighted arbitration "
            f"(sensor_weight={self.sensor_weight:.2f}, model_weight={self.model_weight:.2f})."
        )
        return ArbitrationResult(
            winner=best,
            rationale=rationale,
            score=best_score,
            considered=len(candidates),
        )

