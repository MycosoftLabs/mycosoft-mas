from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class SelfSupervisedBatchResult:
    prediction_loss: float
    contrastive_loss: float
    segmentation_loss: float
    total_loss: float


class SelfSupervisedTasks:
    """
    Phase 2.2 baseline self-supervised objectives.
    These are deterministic placeholders for pipeline wiring.
    """

    def run_batch(self, vectors: List[List[float]]) -> SelfSupervisedBatchResult:
        if not vectors:
            return SelfSupervisedBatchResult(0.0, 0.0, 0.0, 0.0)
        mean_energy = sum(sum(v) for v in vectors) / max(len(vectors), 1)
        prediction_loss = max(0.0, 1.0 - min(mean_energy / 16.0, 1.0))
        contrastive_loss = 0.5 * prediction_loss
        segmentation_loss = 0.25 * prediction_loss
        total = prediction_loss + contrastive_loss + segmentation_loss
        return SelfSupervisedBatchResult(
            prediction_loss=prediction_loss,
            contrastive_loss=contrastive_loss,
            segmentation_loss=segmentation_loss,
            total_loss=total,
        )

    def to_dict(self, result: SelfSupervisedBatchResult) -> Dict[str, float]:
        return {
            "prediction_loss": result.prediction_loss,
            "contrastive_loss": result.contrastive_loss,
            "segmentation_loss": result.segmentation_loss,
            "total_loss": result.total_loss,
        }
