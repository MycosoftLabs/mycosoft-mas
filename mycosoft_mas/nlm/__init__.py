"""
NLM Module - Nature Learning Model - February 10, 2026

The Nature Learning Model (NLM) is a domain-specific language model
for mycology and natural sciences, part of the Mycosoft Multi-Agent System.

Components:
- config: Configuration management for model, training, and inference
- models: Model wrappers for the fine-tuned LLM and embeddings
- training: Training pipeline with data preparation and fine-tuning
- inference: Inference service with specialized query handling
- datasets: Data loading utilities and MINDEX connector
- memory_store: Memory integration for tracking predictions

Quick Start:
    from mycosoft_mas.nlm import get_nlm_service, get_nlm_config
    
    # Get the inference service
    service = get_nlm_service()
    await service.load_model()
    
    # Make a prediction
    from mycosoft_mas.nlm.inference import PredictionRequest
    request = PredictionRequest(text="What is Psilocybe cubensis?")
    result = await service.predict(request)
    print(result.text)

Architecture:
    NLM uses a fine-tuned LLaMA-based model with LoRA adapters
    trained on Mycosoft's mycology knowledge base. It supports:
    - General natural language queries about fungi
    - Species identification and taxonomy
    - Ecological relationship analysis
    - Cultivation protocol guidance
    - Research paper synthesis
    - Genetic sequence interpretation

For training a new model:
    from mycosoft_mas.nlm.training import NLMTrainer
    
    trainer = NLMTrainer()
    await trainer.prepare_data()
    results = await trainer.train()
"""

# Configuration
from .config import (
    NLMConfig,
    ModelArchitectureConfig,
    TrainingConfig,
    DataConfig,
    InferenceConfig,
    get_nlm_config,
    reset_nlm_config,
)

# Models
from .models import NLMBaseModel, NLMEmbeddingModel

# Training
from .training import NLMTrainer, DataCollator, TrainingMetrics

# Inference
from .inference import NLMService, PredictionRequest, PredictionResult
from .inference.service import get_nlm_service, reset_nlm_service

# Data loading
from .datasets import NLMDataLoader, DataProcessor, MINDEXConnector

# Memory integration
from .memory_store import NLMMemoryStore, get_nlm_store

# Legacy exports for backward compatibility
from .data_pipeline import NLMDataPipeline

# NLM-to-workflow bridge (trigger workflows from predictions)
from .workflow_bridge import (
    get_workflow_for_prediction,
    trigger_workflow_from_nlm,
    maybe_trigger_workflow_from_prediction,
    NLM_TO_WORKFLOW_MAP,
    DEFAULT_CONFIDENCE_THRESHOLD,
)

# Alias NLMInference to NLMService for backward compatibility
NLMInference = NLMService

__all__ = [
    # Configuration
    "NLMConfig",
    "ModelArchitectureConfig",
    "TrainingConfig",
    "DataConfig",
    "InferenceConfig",
    "get_nlm_config",
    "reset_nlm_config",
    
    # Models
    "NLMBaseModel",
    "NLMEmbeddingModel",
    
    # Training
    "NLMTrainer",
    "DataCollator",
    "TrainingMetrics",
    
    # Inference
    "NLMService",
    "PredictionRequest",
    "PredictionResult",
    "get_nlm_service",
    "reset_nlm_service",
    
    # Data loading
    "NLMDataLoader",
    "DataProcessor",
    "MINDEXConnector",
    
    # Memory
    "NLMMemoryStore",
    "get_nlm_store",
    
    # Legacy
    "NLMDataPipeline",
    "NLMInference",
    # Workflow bridge
    "get_workflow_for_prediction",
    "trigger_workflow_from_nlm",
    "maybe_trigger_workflow_from_prediction",
    "NLM_TO_WORKFLOW_MAP",
    "DEFAULT_CONFIDENCE_THRESHOLD",
]

__version__ = "0.1.0"
__author__ = "Mycosoft"
__description__ = "Nature Learning Model - Domain-specific LLM for mycology and natural sciences"
