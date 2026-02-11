"""
NLM Models Module - February 10, 2026

Contains model definitions and wrappers for the Nature Learning Model.

Models:
- NLMBaseModel: Base wrapper for the fine-tuned LLM
- NLMEmbeddingModel: Embedding model for semantic search
"""

from .base_model import NLMBaseModel, NLMEmbeddingModel

__all__ = [
    "NLMBaseModel",
    "NLMEmbeddingModel",
]
