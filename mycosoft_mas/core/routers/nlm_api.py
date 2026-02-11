"""
NLM API Router - February 10, 2026

FastAPI router for the Nature Learning Model (NLM).

Provides endpoints for:
- Health checks and service status
- Text generation and prediction
- Model information and capabilities
- Training status (when applicable)

Endpoints:
- GET  /api/nlm/health       - Health check
- POST /api/nlm/predict      - Generate prediction
- GET  /api/nlm/model/info   - Get model information
- GET  /api/nlm/model/status - Get service status
- POST /api/nlm/load         - Load the model
- POST /api/nlm/unload       - Unload the model
"""

import logging
from typing import Any, Dict, List, Optional
from enum import Enum

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/nlm", tags=["nlm"])


# ============================================================================
# Request/Response Models
# ============================================================================

class QueryType(str, Enum):
    """Types of queries the NLM can handle."""
    GENERAL = "general"
    SPECIES_ID = "species_id"
    TAXONOMY = "taxonomy"
    ECOLOGY = "ecology"
    CULTIVATION = "cultivation"
    RESEARCH = "research"
    GENETICS = "genetics"


class PredictRequest(BaseModel):
    """Request body for NLM prediction."""
    text: str = Field(..., min_length=1, description="Input text/query for the model")
    query_type: QueryType = Field(
        default=QueryType.GENERAL,
        description="Type of query for specialized handling"
    )
    max_tokens: int = Field(
        default=1024,
        ge=1,
        le=4096,
        description="Maximum tokens to generate"
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0.0 = deterministic, higher = more random)"
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional context for RAG-style queries"
    )
    include_sources: bool = Field(
        default=True,
        description="Whether to include source references in response"
    )

    model_config = {"json_schema_extra": {
        "examples": [
            {
                "text": "What are the key characteristics of Psilocybe cubensis?",
                "query_type": "species_id",
                "max_tokens": 512,
                "temperature": 0.7
            }
        ]
    }}


class PredictResponse(BaseModel):
    """Response from NLM prediction."""
    text: str = Field(..., description="Generated text response")
    model: str = Field(..., description="Model used for generation")
    query_type: str = Field(..., description="Type of query processed")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    sources: List[str] = Field(default_factory=list, description="Source references")
    tokens_used: int = Field(..., ge=0, description="Number of tokens generated")
    latency_ms: float = Field(..., ge=0, description="Processing time in milliseconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status (healthy, degraded, unhealthy)")
    model_loaded: bool = Field(..., description="Whether model is loaded")
    model_name: str = Field(..., description="Name of the model")
    model_version: str = Field(..., description="Model version")
    uptime_seconds: float = Field(..., ge=0, description="Service uptime")


class ModelInfoResponse(BaseModel):
    """Model information response."""
    name: str = Field(..., description="Model name")
    version: str = Field(..., description="Model version")
    display_name: str = Field(..., description="Human-readable model name")
    description: str = Field(..., description="Model description")
    base_model: str = Field(..., description="Base model architecture")
    capabilities: Dict[str, bool] = Field(..., description="Model capabilities")
    domains: List[str] = Field(..., description="Supported knowledge domains")
    inference_config: Dict[str, Any] = Field(..., description="Default inference settings")


class StatusResponse(BaseModel):
    """Service status response."""
    status: str = Field(..., description="Current status")
    model_name: str = Field(..., description="Model name")
    model_version: str = Field(..., description="Model version")
    rag_enabled: bool = Field(..., description="Whether RAG is enabled")
    memory_enabled: bool = Field(..., description="Whether memory is enabled")
    prediction_count: int = Field(..., ge=0, description="Total predictions made")
    total_tokens: int = Field(..., ge=0, description="Total tokens generated")
    started_at: Optional[str] = Field(None, description="Service start time")
    uptime_seconds: float = Field(..., ge=0, description="Uptime in seconds")


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Check NLM service health.
    
    Returns the current health status of the NLM service,
    including whether the model is loaded and ready for inference.
    """
    try:
        from mycosoft_mas.nlm.inference.service import get_nlm_service
        from mycosoft_mas.nlm.config import get_nlm_config
        
        service = get_nlm_service()
        config = get_nlm_config()
        status = service.get_status()
        
        return HealthResponse(
            status="healthy" if service.is_ready else "degraded",
            model_loaded=service.is_ready,
            model_name=config.model_name,
            model_version=config.model_version,
            uptime_seconds=status.get("uptime_seconds", 0),
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            model_loaded=False,
            model_name="nlm",
            model_version="0.0.0",
            uptime_seconds=0,
        )


@router.post("/predict", response_model=PredictResponse)
async def predict(request: PredictRequest) -> PredictResponse:
    """
    Generate a prediction/response from the NLM.
    
    Accepts natural language queries about mycology, taxonomy,
    ecology, and other natural sciences. The model provides
    domain-specialized responses.
    
    - **text**: The query or prompt
    - **query_type**: Type of query (general, species_id, taxonomy, etc.)
    - **max_tokens**: Maximum response length
    - **temperature**: Creativity level (0.0-2.0)
    - **context**: Optional context for RAG
    - **include_sources**: Whether to include references
    """
    try:
        from mycosoft_mas.nlm.inference.service import (
            get_nlm_service,
            PredictionRequest,
            QueryType as ServiceQueryType
        )
        
        service = get_nlm_service()
        
        # Map to service query type
        query_type_map = {
            QueryType.GENERAL: ServiceQueryType.GENERAL,
            QueryType.SPECIES_ID: ServiceQueryType.SPECIES_ID,
            QueryType.TAXONOMY: ServiceQueryType.TAXONOMY,
            QueryType.ECOLOGY: ServiceQueryType.ECOLOGY,
            QueryType.CULTIVATION: ServiceQueryType.CULTIVATION,
            QueryType.RESEARCH: ServiceQueryType.RESEARCH,
            QueryType.GENETICS: ServiceQueryType.GENETICS,
        }
        
        # Create prediction request
        pred_request = PredictionRequest(
            text=request.text,
            query_type=query_type_map.get(request.query_type, ServiceQueryType.GENERAL),
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            context=request.context,
            include_sources=request.include_sources,
        )
        
        # Get prediction
        result = await service.predict(pred_request)
        
        return PredictResponse(
            text=result.text,
            model=result.model,
            query_type=result.query_type.value,
            confidence=result.confidence,
            sources=result.sources,
            tokens_used=result.tokens_used,
            latency_ms=result.latency_ms,
            metadata=result.metadata,
        )
        
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@router.get("/model/info", response_model=ModelInfoResponse)
async def get_model_info() -> ModelInfoResponse:
    """
    Get detailed information about the NLM model.
    
    Returns model capabilities, supported domains,
    and default inference settings.
    """
    try:
        from mycosoft_mas.nlm.inference.service import get_nlm_service
        
        service = get_nlm_service()
        info = service.get_model_info()
        
        return ModelInfoResponse(**info)
        
    except Exception as e:
        logger.error(f"Failed to get model info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/model/status", response_model=StatusResponse)
async def get_model_status() -> StatusResponse:
    """
    Get current NLM service status.
    
    Returns operational status including prediction counts,
    token usage, and uptime statistics.
    """
    try:
        from mycosoft_mas.nlm.inference.service import get_nlm_service
        
        service = get_nlm_service()
        status = service.get_status()
        
        return StatusResponse(**status)
        
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/load")
async def load_model() -> Dict[str, Any]:
    """
    Load the NLM model into memory.
    
    This endpoint triggers model loading. The model will
    be automatically loaded on first prediction if not
    already loaded.
    """
    try:
        from mycosoft_mas.nlm.inference.service import get_nlm_service
        
        service = get_nlm_service()
        success = await service.load_model()
        
        if success:
            return {
                "status": "success",
                "message": "NLM model loaded successfully",
                "is_ready": service.is_ready,
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to load NLM model"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/unload")
async def unload_model() -> Dict[str, Any]:
    """
    Unload the NLM model from memory.
    
    Frees GPU/CPU memory by unloading the model.
    The model can be reloaded via /load or automatically
    on the next prediction.
    """
    try:
        from mycosoft_mas.nlm.inference.service import get_nlm_service
        
        service = get_nlm_service()
        await service.unload_model()
        
        return {
            "status": "success",
            "message": "NLM model unloaded",
            "is_ready": service.is_ready,
        }
        
    except Exception as e:
        logger.error(f"Failed to unload model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories")
async def list_categories() -> Dict[str, Any]:
    """
    List available knowledge categories.
    
    Returns the categories of knowledge the NLM is trained on,
    which can be used to better formulate queries.
    """
    try:
        from mycosoft_mas.nlm.config import get_nlm_config
        
        config = get_nlm_config()
        
        return {
            "categories": config.data.categories,
            "query_types": [qt.value for qt in QueryType],
            "description": {
                "species_taxonomy": "Species names, classification, taxonomy",
                "mycology_research": "Research papers, findings, experiments",
                "environmental_sensors": "Environmental data and interpretations",
                "genetic_sequences": "DNA/RNA sequences and phenotypes",
                "ecological_interactions": "Species relationships, symbiosis",
                "geographic_distribution": "Where species are found",
                "cultivation_protocols": "How to grow fungi",
                "compound_chemistry": "Chemical compounds in fungi",
                "medical_applications": "Medicinal uses",
                "conservation_status": "Endangered species, conservation",
            },
        }
        
    except Exception as e:
        logger.error(f"Failed to list categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/training/status")
async def get_training_status() -> Dict[str, Any]:
    """
    Get current training status (if training is active).
    
    Returns information about any active training runs,
    including progress and metrics.
    """
    try:
        from mycosoft_mas.nlm.training import NLMTrainer
        
        trainer = NLMTrainer()
        
        return {
            "is_training": trainer.is_training,
            "current_run_id": trainer._current_run_id,
            "metrics": trainer.metrics.to_dict() if trainer.is_training else None,
        }
        
    except Exception as e:
        logger.error(f"Failed to get training status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
