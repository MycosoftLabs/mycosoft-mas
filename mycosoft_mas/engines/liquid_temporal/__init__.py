"""
Liquid Temporal Processing Engine — Adaptive Biosignal Processing

Inspired by Liquid Time-Constant (LTC) networks from MIT CSAIL / Liquid AI:
adaptive time constants that respond to signal dynamics, enabling efficient
processing of continuous fungal biosignals on constrained edge hardware.

This is a processing heuristic, not an actual neural ODE implementation.
It can be replaced with a real LTC model when Liquid AI models are available.

Created: March 9, 2026
(c) 2026 Mycosoft Labs
"""

from mycosoft_mas.engines.liquid_temporal.processor import (
    AdaptiveTimeConstant,
    LiquidTemporalProcessor,
    ProcessedStream,
    StateTransition,
)

__all__ = [
    "AdaptiveTimeConstant",
    "LiquidTemporalProcessor",
    "ProcessedStream",
    "StateTransition",
]
