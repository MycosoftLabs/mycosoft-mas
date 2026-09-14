"""FlyBrain — pluggable FlyWire whole-brain (Drosophila) LIF module for MYCA.

Wraps the Shiu et al. 2024 connectome-constrained leaky integrate-and-fire
model (FlyWire v783, ~138k neurons, ~15M synapse rows) as a controllable
runtime that can be plugged into Mycosoft systems: Psathyrella droids,
the Earth Simulator / ITDX demonstration inside FUSARIUM, the Nature
Learning Model (FormSpace), and the YOLO26 + SAHI vision stack.

Heavy imports (numpy/scipy/torch/ultralytics) are deferred to the modules
that need them so this package is safe to import under MAS_LIGHT_IMPORT.
"""

from mycosoft_mas.flybrain.config import FlyBrainSettings, get_settings
from mycosoft_mas.flybrain.schemas import (
    SCHEMA_VERSION,
    BrainState,
    Detection,
    DetectionFrame,
    MotorAction,
    NavPath,
    Observation,
    SessionConfig,
    SessionInfo,
    StimulusCommand,
    TickRequest,
    TickResult,
)

__all__ = [
    "SCHEMA_VERSION",
    "BrainState",
    "Detection",
    "DetectionFrame",
    "FlyBrainSettings",
    "MotorAction",
    "NavPath",
    "Observation",
    "SessionConfig",
    "SessionInfo",
    "StimulusCommand",
    "TickRequest",
    "TickResult",
    "get_settings",
]
