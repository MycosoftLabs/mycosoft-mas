"""
NLM Inference Module - February 10, 2026

Inference service components for the Nature Learning Model.

Components:
- NLMService: Main inference service with FastAPI integration
- NLMInference: Legacy inference engine (backward compatible)
- PredictionRequest: Structured prediction input
- PredictionResult: Structured prediction output
"""

from .service import NLMService, PredictionRequest, PredictionResult

# Legacy import for backward compatibility
try:
    from ..inference_legacy import NLMInference
except ImportError:
    # Create alias to new service if legacy module doesn't exist
    NLMInference = NLMService

__all__ = [
    "NLMService",
    "NLMInference",
    "PredictionRequest",
    "PredictionResult",
]
