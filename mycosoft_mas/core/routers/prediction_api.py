"""
Prediction API - February 6, 2026

FastAPI router for prediction endpoints.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from mycosoft_mas.prediction import (
    AircraftPredictor,
    VesselPredictor,
    SatellitePredictor,
    WildlifePredictor,
    HazardPredictor,
    Earth2Forecaster,
    EntityState,
    EntityType,
    GeoPoint,
    PredictedPosition,
    PredictionRequest,
    PredictionResult,
    Velocity,
    get_earth2_forecaster,
    get_prediction_store,
)

logger = logging.getLogger("PredictionAPI")
router = APIRouter(prefix="/prediction", tags=["prediction"])


# === Pydantic Models ===

class GeoPointModel(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    altitude: Optional[float] = None


class VelocityModel(BaseModel):
    speed: float = Field(..., ge=0)
    heading: float = Field(..., ge=0, le=360)
    climb_rate: Optional[float] = None


class EntityStateModel(BaseModel):
    entity_id: str
    entity_type: str
    timestamp: Optional[datetime] = None
    position: GeoPointModel
    velocity: Optional[VelocityModel] = None
    metadata: Optional[Dict[str, Any]] = None
    # Type-specific fields
    flight_plan: Optional[Dict] = None
    destination: Optional[str] = None
    tle_line1: Optional[str] = None
    tle_line2: Optional[str] = None
    species: Optional[str] = None


class PredictionRequestModel(BaseModel):
    entity_id: str
    entity_type: str = "aircraft"
    from_time: Optional[datetime] = None
    to_time: Optional[datetime] = None
    hours_ahead: float = Field(default=2, ge=0.1, le=168)
    resolution_seconds: int = Field(default=60, ge=10, le=3600)
    include_uncertainty: bool = True
    # Optional current state (if not available in cache)
    current_state: Optional[EntityStateModel] = None


class PredictedPositionModel(BaseModel):
    entity_id: str
    entity_type: str
    timestamp: datetime
    position: GeoPointModel
    velocity: Optional[VelocityModel] = None
    confidence: float
    uncertainty_radius_m: Optional[float] = None
    prediction_source: str
    metadata: Optional[Dict[str, Any]] = None


class PredictionResponseModel(BaseModel):
    entity_id: str
    entity_type: str
    predictions: List[PredictedPositionModel]
    source: str
    model_version: str
    computation_time_ms: float
    warnings: List[str] = []


class BatchPredictionRequest(BaseModel):
    requests: List[PredictionRequestModel]


class BatchPredictionResponse(BaseModel):
    results: List[PredictionResponseModel]
    total_computation_time_ms: float


class WeatherForecastRequest(BaseModel):
    location: GeoPointModel
    hours_ahead: int = Field(default=24, ge=1, le=240)
    resolution_hours: int = Field(default=1, ge=1, le=6)
    model: str = "fcn"


class WeatherForecastResponse(BaseModel):
    location: GeoPointModel
    forecasts: List[Dict[str, Any]]
    model: str
    generated_at: datetime


# === Helper Functions ===

def _get_predictor(entity_type: str):
    """Get appropriate predictor for entity type."""
    predictors = {
        "aircraft": AircraftPredictor,
        "vessel": VesselPredictor,
        "satellite": SatellitePredictor,
        "wildlife": WildlifePredictor,
        "earthquake": HazardPredictor,
        "wildfire": HazardPredictor,
        "storm": HazardPredictor,
    }
    
    predictor_class = predictors.get(entity_type.lower())
    if not predictor_class:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown entity type: {entity_type}"
        )
    
    return predictor_class()


def _state_model_to_entity(model: EntityStateModel) -> EntityState:
    """Convert Pydantic model to EntityState."""
    return EntityState(
        entity_id=model.entity_id,
        entity_type=EntityType(model.entity_type),
        timestamp=model.timestamp or datetime.now(timezone.utc),
        position=GeoPoint(
            lat=model.position.lat,
            lng=model.position.lng,
            altitude=model.position.altitude,
        ),
        velocity=Velocity(
            speed=model.velocity.speed,
            heading=model.velocity.heading,
            climb_rate=model.velocity.climb_rate,
        ) if model.velocity else None,
        metadata=model.metadata or {},
        flight_plan=model.flight_plan,
        destination=model.destination,
        tle_line1=model.tle_line1,
        tle_line2=model.tle_line2,
        species=model.species,
    )


def _prediction_to_model(pred: PredictedPosition) -> PredictedPositionModel:
    """Convert PredictedPosition to Pydantic model."""
    return PredictedPositionModel(
        entity_id=pred.entity_id,
        entity_type=pred.entity_type.value,
        timestamp=pred.timestamp,
        position=GeoPointModel(
            lat=pred.position.lat,
            lng=pred.position.lng,
            altitude=pred.position.altitude,
        ),
        velocity=VelocityModel(
            speed=pred.velocity.speed,
            heading=pred.velocity.heading,
            climb_rate=pred.velocity.climb_rate,
        ) if pred.velocity else None,
        confidence=pred.confidence,
        uncertainty_radius_m=pred.uncertainty.radius_meters if pred.uncertainty else None,
        prediction_source=pred.prediction_source.value,
        metadata=pred.metadata,
    )


# === Endpoints ===

@router.post("/predict", response_model=PredictionResponseModel)
async def predict_entity(request: PredictionRequestModel):
    """
    Generate predictions for a single entity.
    """
    predictor = _get_predictor(request.entity_type)
    
    # Determine time range
    from_time = request.from_time or datetime.now(timezone.utc)
    to_time = request.to_time or (from_time + timedelta(hours=request.hours_ahead))
    
    # Get or create entity state
    if request.current_state:
        state = _state_model_to_entity(request.current_state)
    else:
        state = await predictor.get_current_state(request.entity_id)
        if state is None:
            raise HTTPException(
                status_code=404,
                detail=f"Entity {request.entity_id} not found and no state provided"
            )
    
    # Create prediction request
    pred_request = PredictionRequest(
        entity_id=request.entity_id,
        entity_type=EntityType(request.entity_type),
        from_time=from_time,
        to_time=to_time,
        resolution_seconds=request.resolution_seconds,
        include_uncertainty=request.include_uncertainty,
    )
    
    # Generate predictions
    result = await predictor.predict(pred_request)
    
    return PredictionResponseModel(
        entity_id=result.entity_id,
        entity_type=result.entity_type.value,
        predictions=[_prediction_to_model(p) for p in result.predictions],
        source=result.source.value,
        model_version=result.model_version,
        computation_time_ms=result.computation_time_ms,
        warnings=result.warnings,
    )


@router.post("/batch", response_model=BatchPredictionResponse)
async def predict_batch(request: BatchPredictionRequest):
    """
    Generate predictions for multiple entities in parallel.
    """
    import time
    start = time.time()
    
    async def process_one(req: PredictionRequestModel) -> PredictionResponseModel:
        try:
            return await predict_entity(req)
        except Exception as e:
            logger.error(f"Prediction failed for {req.entity_id}: {e}")
            return PredictionResponseModel(
                entity_id=req.entity_id,
                entity_type=req.entity_type,
                predictions=[],
                source="error",
                model_version="1.0.0",
                computation_time_ms=0,
                warnings=[str(e)],
            )
    
    results = await asyncio.gather(*[process_one(req) for req in request.requests])
    
    return BatchPredictionResponse(
        results=list(results),
        total_computation_time_ms=(time.time() - start) * 1000,
    )


@router.get("/aircraft/{entity_id}", response_model=PredictionResponseModel)
async def predict_aircraft_endpoint(
    entity_id: str,
    hours: float = Query(default=2, ge=0.1, le=24),
    resolution: int = Query(default=60, ge=10, le=600),
):
    """
    Get aircraft prediction by ID.
    """
    return await predict_entity(PredictionRequestModel(
        entity_id=entity_id,
        entity_type="aircraft",
        hours_ahead=hours,
        resolution_seconds=resolution,
    ))


@router.get("/vessel/{entity_id}", response_model=PredictionResponseModel)
async def predict_vessel_endpoint(
    entity_id: str,
    hours: float = Query(default=24, ge=1, le=72),
    resolution: int = Query(default=300, ge=60, le=3600),
):
    """
    Get vessel prediction by ID.
    """
    return await predict_entity(PredictionRequestModel(
        entity_id=entity_id,
        entity_type="vessel",
        hours_ahead=hours,
        resolution_seconds=resolution,
    ))


@router.get("/satellite/{norad_id}", response_model=PredictionResponseModel)
async def predict_satellite_endpoint(
    norad_id: str,
    hours: float = Query(default=12, ge=1, le=168),
    resolution: int = Query(default=60, ge=10, le=600),
):
    """
    Get satellite prediction by NORAD ID.
    """
    return await predict_entity(PredictionRequestModel(
        entity_id=norad_id,
        entity_type="satellite",
        hours_ahead=hours,
        resolution_seconds=resolution,
    ))


@router.get("/wildlife/{entity_id}", response_model=PredictionResponseModel)
async def predict_wildlife_endpoint(
    entity_id: str,
    hours: float = Query(default=24, ge=1, le=168),
    resolution: int = Query(default=3600, ge=60, le=86400),
    species: Optional[str] = None,
):
    """
    Get wildlife prediction.
    """
    request = PredictionRequestModel(
        entity_id=entity_id,
        entity_type="wildlife",
        hours_ahead=hours,
        resolution_seconds=resolution,
    )
    
    if species:
        # Would need to create state with species
        pass
    
    return await predict_entity(request)


@router.post("/weather", response_model=WeatherForecastResponse)
async def get_weather_forecast(request: WeatherForecastRequest):
    """
    Get weather forecast for a location.
    """
    forecaster = await get_earth2_forecaster()
    
    location = GeoPoint(
        lat=request.location.lat,
        lng=request.location.lng,
    )
    
    from_time = datetime.now(timezone.utc)
    to_time = from_time + timedelta(hours=request.hours_ahead)
    
    forecasts = await forecaster.get_weather_forecast(
        location=location,
        from_time=from_time,
        to_time=to_time,
        resolution_hours=request.resolution_hours,
        model=request.model,
    )
    
    return WeatherForecastResponse(
        location=request.location,
        forecasts=forecasts,
        model=request.model,
        generated_at=datetime.now(timezone.utc),
    )


@router.get("/storms")
async def get_storm_predictions(
    min_lat: float = Query(..., ge=-90, le=90),
    min_lng: float = Query(..., ge=-180, le=180),
    max_lat: float = Query(..., ge=-90, le=90),
    max_lng: float = Query(..., ge=-180, le=180),
    hours: int = Query(default=72, ge=1, le=168),
):
    """
    Get storm track predictions for a region.
    """
    forecaster = await get_earth2_forecaster()
    
    storms = await forecaster.get_storm_tracks(
        region_bounds=(min_lat, min_lng, max_lat, max_lng),
        from_time=datetime.now(timezone.utc),
        to_time=datetime.now(timezone.utc) + timedelta(hours=hours),
    )
    
    return {"storms": storms}


@router.post("/wildfire/spread")
async def predict_wildfire_spread(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    wind_speed: float = Query(default=20, ge=0, le=200),
    wind_direction: float = Query(default=270, ge=0, le=360),
    fuel_moisture: float = Query(default=0.3, ge=0, le=1),
    hours: int = Query(default=24, ge=1, le=72),
):
    """
    Predict wildfire spread from a point.
    """
    forecaster = await get_earth2_forecaster()
    
    predictions = await forecaster.get_wildfire_spread(
        fire_location=GeoPoint(lat=lat, lng=lng),
        wind_speed=wind_speed,
        wind_direction=wind_direction,
        fuel_moisture=fuel_moisture,
        hours_ahead=hours,
    )
    
    return {"predictions": predictions}


@router.get("/health")
async def health_check():
    """
    Prediction engine health check.
    """
    forecaster = await get_earth2_forecaster()
    
    return {
        "status": "healthy",
        "predictors": {
            "aircraft": "available",
            "vessel": "available",
            "satellite": "available",
            "wildlife": "available",
            "hazard": "available",
        },
        "earth2_available": forecaster._earth2_available,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }