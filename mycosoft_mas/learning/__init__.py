"""
MYCA Learning Module - Opposable Thumb Architecture

Continuous biospheric learning from sensor telemetry:
- Drift detection: identify when sensor distributions shift
- Continuous learner: closed-loop Observe → Process → Learn
- Feeds NLM and world model for grounded AI

Created: February 17, 2026
"""

from mycosoft_mas.learning.continuous_learner import (
    ContinuousLearner,
    LearningCycleResult,
)
from mycosoft_mas.learning.drift_detector import (
    DriftAlert,
    DriftDetector,
    DriftSeverity,
)

__all__ = [
    "DriftDetector",
    "DriftAlert",
    "DriftSeverity",
    "ContinuousLearner",
    "LearningCycleResult",
]
