"""
Intention engine - Goal decomposition and plan candidates for Grounded Cognition.

IntentionService: decompose user directive into IntentGraph.
FingerOrchestrator: classify task type and route to frontier LLMs.
Created: February 17, 2026
"""

from mycosoft_mas.engines.intention.intention_service import (
    IntentionService,
    IntentGraph,
    PlanCandidate,
)
from mycosoft_mas.engines.intention.finger_orchestrator import FingerOrchestrator

__all__ = [
    "IntentionService",
    "IntentGraph",
    "PlanCandidate",
    "FingerOrchestrator",
]
