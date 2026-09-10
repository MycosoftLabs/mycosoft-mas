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
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
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
        default=QueryType.GENERAL, description="Type of query for specialized handling"
    )
    max_tokens: int = Field(default=1024, ge=1, le=4096, description="Maximum tokens to generate")
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0.0 = deterministic, higher = more random)",
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional context for RAG-style queries"
    )
    include_sources: bool = Field(
        default=True, description="Whether to include source references in response"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "text": "What are the key characteristics of Psilocybe cubensis?",
                    "query_type": "species_id",
                    "max_tokens": 512,
                    "temperature": 0.7,
                }
            ]
        }
    }


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
    model_loaded: bool = Field(..., description="Whether tensors are in-process")
    model_name: str = Field(..., description="Name of the model")
    model_version: str = Field(..., description="Model version")
    uptime_seconds: float = Field(..., ge=0, description="Service uptime")
    forecast_qualified: bool = Field(default=False, description="Calibrated Fusarium forecast ready")
    qualification_status: str = Field(default="unloaded", description="candidate/unqualified/unloaded")
    training_origin: str = Field(default="none", description="synthetic or measured")
    architecture_family: Optional[str] = Field(default=None)
    weights_sha256: Optional[str] = Field(default=None)
    bound_to_ollama: bool = Field(default=False)
    model_dir: Optional[str] = Field(default=None, description="NAS path tensors were loaded from")
    load_reason: Optional[str] = Field(default=None)


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


class NatureEmbeddingRequest(BaseModel):
    packet: Dict[str, Any] = Field(..., description="NaturePacket-like payload")


class NatureEmbeddingResponse(BaseModel):
    vector: List[float]
    anomaly_score: float
    vector_size: int


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
        from mycosoft_mas.nlm.config import get_nlm_config
        from mycosoft_mas.nlm.formspace.scientific_loader import probe_scientific_nlm
        from mycosoft_mas.nlm.inference.service import get_nlm_service

        from mycosoft_mas.nlm.formspace.reference_runtime import load_reference_runtime

        service = get_nlm_service()
        config = get_nlm_config()
        status = service.get_status()
        probe = probe_scientific_nlm()
        runtime = load_reference_runtime()
        runtime_status = runtime.runtime_status()
        loaded = bool(runtime.is_loaded)
        forecast = bool(probe.model_loaded and service.is_ready and not probe.is_legacy_reference)

        return HealthResponse(
            status="healthy" if loaded else "degraded",
            model_loaded=loaded,
            model_name=config.model_name,
            model_version=config.model_version,
            uptime_seconds=status.get("uptime_seconds", 0),
            forecast_qualified=forecast,
            qualification_status=runtime_status.get("qualification_status") or "unloaded",
            training_origin=runtime_status.get("training_origin") or "none",
            architecture_family=runtime_status.get("architecture_family"),
            weights_sha256=runtime_status.get("weights_sha256"),
            bound_to_ollama=False,
            model_dir=runtime_status.get("model_dir") or None,
            load_reason=runtime_status.get("reason"),
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
            PredictionRequest,
        )
        from mycosoft_mas.nlm.inference.service import QueryType as ServiceQueryType
        from mycosoft_mas.nlm.inference.service import (
            get_nlm_service,
        )

        service = get_nlm_service()
        from mycosoft_mas.nlm.formspace.reference_runtime import load_reference_runtime
        from mycosoft_mas.nlm.formspace.scientific_loader import probe_scientific_nlm

        probe = probe_scientific_nlm()
        runtime = load_reference_runtime()
        if not probe.model_loaded and not runtime.is_loaded:
            raise HTTPException(
                status_code=503,
                detail="Scientific NLM not loaded. Waiting for FormSpace forecast artifacts on NAS. Not Ollama.",
            )

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

        if probe.model_loaded:
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

        replay = runtime.replay()
        return PredictResponse(
            text=(
                "Archived FormSpace reference replay completed. "
                "SYNTHETIC_TEST. Fusarium ecology p remains null. Not Ollama."
            ),
            model="formspace-environmental-reference/0.1.0",
            query_type=request.query_type.value,
            confidence=0.0,
            sources=["NAS models/nlm/reference"],
            tokens_used=0,
            latency_ms=0.0,
            metadata={
                "stub": False,
                "confidence_usable": False,
                "forecast_qualified": False,
                "training_origin": "SYNTHETIC_TEST",
                "replay": replay,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@router.post("/embeddings/nature", response_model=NatureEmbeddingResponse)
async def generate_nature_embedding(request: NatureEmbeddingRequest) -> NatureEmbeddingResponse:
    """
    Phase 2.3 Nature embedding endpoint with anomaly scoring.
    """
    try:
        from mycosoft_mas.nlm.embodiment_encoders import NatureEmbeddingEncoder

        encoder = NatureEmbeddingEncoder()
        result = encoder.encode(request.packet)
        return NatureEmbeddingResponse(
            vector=result.vector,
            anomaly_score=result.anomaly_score,
            vector_size=len(result.vector),
        )
    except Exception as e:
        logger.error(f"Nature embedding failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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

        from mycosoft_mas.nlm.formspace.scientific_loader import probe_scientific_nlm

        from mycosoft_mas.nlm.formspace.reference_runtime import load_reference_runtime

        service = get_nlm_service()
        probe = probe_scientific_nlm()
        runtime = load_reference_runtime()
        if probe.model_loaded:
            success = await service.load_model()
            return {
                "status": "success" if success else "waiting",
                "message": "NLM forecast model loaded" if success else probe.reason,
                "model_loaded": bool(success),
                "forecast_qualified": bool(success),
                "is_ready": service.is_ready,
            }
        if runtime.is_loaded:
            return {
                "status": "success",
                "message": runtime.reason,
                "model_loaded": True,
                "forecast_qualified": False,
                "is_ready": False,
                "model_dir": runtime.model_dir,
                "qualification_status": "candidate",
            }
        return {
            "status": "waiting",
            "message": probe.reason,
            "model_loaded": False,
            "forecast_qualified": False,
            "is_ready": False,
            "model_dir": probe.model_dir,
        }

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


# =============================================================================
# NLM Full Endpoints - Translate, NMF, Tokens, Predict/Fruiting, Query/Knowledge
# Extended: February 17, 2026
# =============================================================================


class TranslateRequest(BaseModel):
    """Request for translation layer (raw -> NMF)."""

    raw: Dict[str, Any] = Field(..., description="Raw sensor/environmental data")
    envelopes: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Optional telemetry envelopes"
    )
    source_id: str = Field(default="", description="Source identifier")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Optional context")


class NMFCreateRequest(BaseModel):
    """Request for creating a Nature Message Frame."""

    raw: Dict[str, Any] = Field(..., description="Raw sensor/environmental data")
    envelopes: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Optional telemetry envelopes"
    )
    source_id: str = Field(default="", description="Source identifier")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Optional context")


class FruitingPredictRequest(BaseModel):
    """Request for fruiting prediction."""

    entity_id: str = Field(default="generic", description="Species or entity identifier")
    time_horizon: str = Field(default="30d", description="Prediction horizon (e.g. 7d, 30d)")
    conditions: Optional[Dict[str, Any]] = Field(
        default=None, description="Environmental conditions"
    )
    location: Optional[Dict[str, float]] = Field(default=None, description="Lat/lon/alt")


class KnowledgeQueryRequest(BaseModel):
    """Request for knowledge graph query."""

    query: str = Field(..., min_length=1, description="Query string")
    limit: int = Field(default=10, ge=1, le=100, description="Max results")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Optional context")


class EnvironmentalProcessRequest(BaseModel):
    """Request for environmental data processing."""

    temperature: float = Field(..., description="Temperature in Celsius")
    humidity: float = Field(..., description="Humidity percentage")
    co2: Optional[float] = Field(default=None, description="CO2 ppm")
    pressure: Optional[float] = Field(default=None, description="Pressure hPa")
    timestamp: Optional[str] = Field(default=None, description="ISO timestamp")
    location: Optional[Dict[str, float]] = Field(default=None, description="Lat/lon/alt")


def _parse_envelopes(envelopes: Optional[List[Dict[str, Any]]]) -> Optional[List[Any]]:
    """Convert envelope dicts to TelemetryEnvelope objects when available."""
    if not envelopes:
        return None
    try:
        from mycosoft_mas.nlm.telemetry_envelopes import TelemetryEnvelope

        return [TelemetryEnvelope.from_dict(e) if isinstance(e, dict) else e for e in envelopes]
    except ImportError:
        return envelopes  # Pass through as dicts if module unavailable


@router.post("/translate")
async def api_translate(req: TranslateRequest) -> Dict[str, Any]:
    """
    Translate raw environmental data through the NLM translation layer.

    Raw -> Normalized -> Bio-Tokens -> Nature Message Frame (NMF).
    Uses mycosoft_mas.nlm.translation_layer.
    """
    try:
        from mycosoft_mas.nlm.translation_layer import translate as translate_layer

        parsed = _parse_envelopes(req.envelopes)
        nmf = translate_layer(
            raw=req.raw,
            envelopes=parsed,
            source_id=req.source_id,
            context=req.context,
        )
        return nmf.to_dict()
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/nmf/create")
async def api_nmf_create(req: NMFCreateRequest) -> Dict[str, Any]:
    """
    Create a Nature Message Frame from raw data.
    """
    try:
        from mycosoft_mas.nlm.translation_layer import build_nmf

        parsed = _parse_envelopes(req.envelopes)
        nmf = build_nmf(
            raw=req.raw,
            envelopes=parsed,
            source_id=req.source_id,
            context=req.context,
        )
        return nmf.to_dict()
    except Exception as e:
        logger.error(f"NMF creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tokens/vocabulary")
async def api_tokens_vocabulary() -> Dict[str, Any]:
    """
    Get the Bio-Token vocabulary (micro-speak codes and semantic labels).
    """
    try:
        from mycosoft_mas.nlm.bio_tokens import (
            BIO_TOKEN_VOCABULARY,
            all_semantics,
            all_tokens,
        )

        return {
            "vocabulary": BIO_TOKEN_VOCABULARY,
            "token_codes": all_tokens(),
            "semantic_labels": list(all_semantics()),
            "count": len(BIO_TOKEN_VOCABULARY),
        }
    except Exception as e:
        logger.error(f"Failed to get vocabulary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict/fruiting")
async def api_predict_fruiting(req: FruitingPredictRequest) -> Dict[str, Any]:
    """
    Generate fruiting probability prediction.

    Proxies to NLM API when available, or uses MAS NLM client.
    """
    try:
        import os

        import httpx

        nlm_url = os.getenv("NLM_API_URL", "http://localhost:8200")
        if nlm_url:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{nlm_url.rstrip('/')}/api/predict/fruiting",
                    json={
                        "entity_id": req.entity_id,
                        "time_horizon": req.time_horizon,
                        "conditions": req.conditions,
                        "location": req.location,
                    },
                )
                if resp.status_code == 200:
                    return resp.json()
    except Exception as e:
        logger.debug(f"NLM API fruiting predict proxy failed: {e}")

    try:
        from nlm.client import NLMClient

        client = NLMClient()
        conditions = req.conditions or {}
        if req.location:
            conditions["location"] = req.location
        return await client.predict(
            entity_type="fruiting_conditions",
            entity_id=req.entity_id,
            time_horizon=req.time_horizon,
            conditions=conditions,
        )
    except ImportError:
        return {
            "entity_type": "fruiting_conditions",
            "entity_id": req.entity_id,
            "time_horizon": req.time_horizon,
            "prediction": {"fallback": True, "message": "NLM client not available"},
            "confidence": 0.3,
        }
    except Exception as e:
        logger.error(f"Fruiting predict failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query/knowledge")
async def api_query_knowledge(req: KnowledgeQueryRequest) -> Dict[str, Any]:
    """
    Query the knowledge graph via MINDEX.
    """
    try:
        import os

        import httpx

        nlm_url = os.getenv("NLM_API_URL", "http://localhost:8200")
        if nlm_url:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{nlm_url.rstrip('/')}/api/query/knowledge",
                    json={
                        "query": req.query,
                        "limit": req.limit,
                        "context": req.context,
                    },
                )
                if resp.status_code == 200:
                    return resp.json()
    except Exception as e:
        logger.debug(f"NLM API knowledge query proxy failed: {e}")

    try:
        from nlm.client import NLMClient

        client = NLMClient()
        return await client.query_knowledge_graph(
            query=req.query,
            context=req.context,
            limit=req.limit,
        )
    except ImportError:
        return {
            "query": req.query,
            "results": [],
            "entities": [],
            "relations": [],
            "message": "NLM client not available",
        }
    except Exception as e:
        logger.error(f"Knowledge query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class SensorPredictRequest(BaseModel):
    """Request for next-hour sensor prediction."""

    entity_id: str = Field(default="sporebase", description="Entity/device ID")
    horizon_minutes: int = Field(
        default=60, ge=1, le=1440, description="Prediction horizon in minutes"
    )
    current_conditions: Optional[Dict[str, Any]] = Field(
        default=None, description="Current sensor readings"
    )


@router.post("/predict/sensors")
async def api_predict_sensors(req: SensorPredictRequest) -> Dict[str, Any]:
    """
    Predict next-hour sensor readings for grounding.

    Used by GroundingGate.attach_world_state() to add nlm_prediction.
    Proxies to NLM API when available; returns fallback structure otherwise.
    """
    try:
        import os

        import httpx

        nlm_url = os.getenv("NLM_API_URL", "http://localhost:8200")
        if nlm_url:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    f"{nlm_url.rstrip('/')}/api/predict/sensors",
                    json={
                        "entity_id": req.entity_id,
                        "horizon_minutes": req.horizon_minutes,
                        "current_conditions": req.current_conditions,
                    },
                )
                if resp.status_code == 200:
                    return resp.json()
    except Exception as e:
        logger.debug("NLM sensors predict proxy failed: %s", e)

    return {
        "entity_id": req.entity_id,
        "horizon_minutes": req.horizon_minutes,
        "predictions": [],
        "fallback": True,
        "message": "NLM sensor prediction not available",
    }


@router.post("/environmental/process")
async def api_environmental_process(req: EnvironmentalProcessRequest) -> Dict[str, Any]:
    """
    Process environmental data through NLM.

    Returns insights and predictions based on temperature, humidity, etc.
    """
    try:
        import os
        from datetime import datetime

        import httpx

        nlm_url = os.getenv("NLM_API_URL", "http://localhost:8200")
        if nlm_url:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{nlm_url.rstrip('/')}/api/environmental/process",
                    json={
                        "temperature": req.temperature,
                        "humidity": req.humidity,
                        "co2": req.co2,
                        "pressure": req.pressure,
                        "timestamp": req.timestamp,
                        "location": req.location,
                    },
                )
                if resp.status_code == 200:
                    return resp.json()
    except Exception as e:
        logger.debug(f"NLM API environmental process proxy failed: {e}")

    try:
        from nlm.client import NLMClient

        client = NLMClient()
        ts = None
        if req.timestamp:
            try:
                ts = datetime.fromisoformat(req.timestamp.replace("Z", "+00:00"))
            except Exception:
                pass
        return await client.process_environmental_data(
            temperature=req.temperature,
            humidity=req.humidity,
            co2=req.co2,
            pressure=req.pressure,
            location=req.location,
            timestamp=ts,
        )
    except ImportError:
        return {
            "status": "fallback",
            "temperature": req.temperature,
            "humidity": req.humidity,
            "insights": ["NLM client not available; returning basic acknowledgment"],
            "predictions": [],
            "confidence": 0.3,
        }
    except Exception as e:
        logger.error(f"Environmental process failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ForecastIssueRequest(BaseModel):
    subject_id: str
    episode_id: str
    issued_at: str
    input_cutoff_at: str
    event_definition_id: str
    chart_id: str
    chart_version: str
    forecast_id: Optional[str] = None
    run_id: Optional[str] = None
    horizon_seconds: List[int] = Field(default_factory=list)
    input_observation_ids: List[str] = Field(default_factory=list)
    root_evidence_ids: List[str] = Field(default_factory=list)
    support_status: Optional[str] = None
    reasons: List[str] = Field(default_factory=list)


class ForecastPatchRequest(BaseModel):
    late_label: Optional[Dict[str, Any]] = None
    observation_id: Optional[str] = None


@router.post("/observations")
async def accept_observation(
    envelope: Dict[str, Any],
    cutoff: Optional[str] = None,
) -> Dict[str, Any]:
    """Causal observation ingest. Four times required. No invented scores."""
    from datetime import datetime, timezone

    from mycosoft_mas.nlm.formspace.contracts import ObservationEnvelope
    from mycosoft_mas.nlm.formspace.observation_pipeline import get_observation_pipeline

    parsed = ObservationEnvelope.model_validate(envelope)
    if cutoff:
        cutoff_dt = datetime.fromisoformat(cutoff.replace("Z", "+00:00"))
    else:
        cutoff_dt = parsed.available_at
    if cutoff_dt.tzinfo is None:
        cutoff_dt = cutoff_dt.replace(tzinfo=timezone.utc)
    return get_observation_pipeline().process(parsed, cutoff_dt)


@router.post("/forecasts")
async def issue_forecast(request: ForecastIssueRequest) -> Dict[str, Any]:
    """Issue an immutable forecast. Unsupported until real NLM artifacts load."""
    from mycosoft_mas.nlm.formspace.contracts import ForecastEnvelope
    from mycosoft_mas.nlm.formspace.forecast_ledger import get_forecast_ledger
    from mycosoft_mas.nlm.formspace.scientific_loader import probe_scientific_nlm

    probe = probe_scientific_nlm()
    reasons = list(request.reasons)
    if not probe.model_loaded:
        reasons.append(probe.reason or "Scientific NLM weights absent")
    payload = request.model_dump(exclude_none=True)
    payload["support_status"] = "UNSUPPORTED" if not probe.model_loaded else (
        request.support_status or "UNSUPPORTED"
    )
    payload["reasons"] = reasons
    payload["hazard_probabilities"] = None
    payload["cumulative_probabilities"] = None
    envelope = ForecastEnvelope.model_validate(payload)
    return get_forecast_ledger().persist(envelope)


@router.get("/forecasts/{forecast_id}")
async def get_forecast(forecast_id: str) -> Dict[str, Any]:
    from mycosoft_mas.nlm.formspace.forecast_ledger import get_forecast_ledger

    row = get_forecast_ledger().get(forecast_id)
    if row is None:
        raise HTTPException(status_code=404, detail="forecast not found")
    return row


@router.post("/forecasts/{forecast_id}/patch")
async def refuse_forecast_patch(
    forecast_id: str,
    request: ForecastPatchRequest,
) -> Dict[str, Any]:
    """I03: late labels and observations cannot overwrite an issued forecast."""
    from mycosoft_mas.nlm.formspace.forecast_ledger import get_forecast_ledger

    return get_forecast_ledger().refuse_overwrite(
        forecast_id,
        request.model_dump(exclude_none=True),
    )


@router.get("/runtime")
async def nlm_runtime() -> Dict[str, Any]:
    from mycosoft_mas.nlm.formspace.reference_runtime import load_reference_runtime
    from mycosoft_mas.nlm.formspace.scientific_loader import probe_scientific_nlm

    runtime = load_reference_runtime()
    probe = probe_scientific_nlm()
    status = runtime.runtime_status()
    status["forecast_probe"] = {
        "model_loaded": probe.model_loaded,
        "is_legacy_reference": probe.is_legacy_reference,
        "reason": probe.reason,
        "model_dir": probe.model_dir,
    }
    status["bound_to_ollama"] = False
    return status


@router.post("/decision-path")
async def nlm_decision_path(body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    from mycosoft_mas.nlm.formspace.decision_path import run_decision_path
    from mycosoft_mas.nlm.formspace.persist import persist_decision_bundle

    path = await run_decision_path(body or {})
    try:
        persist = await persist_decision_bundle(path)
    except Exception as exc:
        persist = {"ok": False, "reason": str(exc)}
    path["retain"] = persist
    return path


@router.get("/weka-features")
async def nlm_weka_features() -> Dict[str, Any]:
    from mycosoft_mas.nlm.formspace.reference_runtime import load_reference_runtime

    runtime = load_reference_runtime()
    return runtime.weka_features()


@router.post("/retain")
async def nlm_retain(body: Dict[str, Any]) -> Dict[str, Any]:
    from mycosoft_mas.nlm.formspace.persist import persist_decision_bundle

    return await persist_decision_bundle(body)


@router.get("/retain/{embedding_id}")
async def nlm_retain_get(embedding_id: str) -> Dict[str, Any]:
    from mycosoft_mas.nlm.formspace.persist import get_mindex_record

    return await get_mindex_record(embedding_id)
