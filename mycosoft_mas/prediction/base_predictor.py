"""
Base Predictor - February 6, 2026

Abstract base class for all prediction engines.
Provides common functionality for confidence decay, caching, and storage.
"""

import asyncio
import logging
import math
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from .prediction_types import (
    EntityState,
    EntityType,
    GeoPoint,
    PredictedPosition,
    PredictionRequest,
    PredictionResult,
    PredictionSource,
    UncertaintyCone,
    Velocity,
)

logger = logging.getLogger("Prediction")


class BasePredictor(ABC):
    """
    Abstract base class for entity prediction.
    
    Subclasses implement domain-specific prediction logic while
    inheriting common functionality like confidence decay and caching.
    """
    
    # Override these in subclasses
    entity_type: EntityType
    prediction_source: PredictionSource = PredictionSource.EXTRAPOLATION
    model_version: str = "1.0.0"
    
    # Confidence decay parameters
    initial_confidence: float = 0.95
    confidence_half_life_seconds: float = 900  # 15 minutes
    minimum_confidence: float = 0.1
    
    # Prediction limits
    max_prediction_horizon: timedelta = timedelta(hours=2)
    min_resolution_seconds: int = 10
    max_resolution_seconds: int = 3600
    
    # Uncertainty growth
    base_uncertainty_meters: float = 100
    uncertainty_growth_rate: float = 0.1  # meters per second
    
    def __init__(self):
        self._cache: Dict[str, PredictionResult] = {}
        self._cache_ttl_seconds = 60
    
    @abstractmethod
    async def get_current_state(self, entity_id: str) -> Optional[EntityState]:
        """
        Get the current state of an entity.
        
        Subclasses implement this to fetch from their data source.
        """
        pass
    
    @abstractmethod
    async def predict_positions(
        self,
        state: EntityState,
        from_time: datetime,
        to_time: datetime,
        resolution_seconds: int
    ) -> List[PredictedPosition]:
        """
        Generate predicted positions for an entity.
        
        Subclasses implement domain-specific prediction logic.
        """
        pass
    
    async def predict(self, request: PredictionRequest) -> PredictionResult:
        """
        Main prediction entry point.
        
        Validates request, gets current state, generates predictions,
        and applies confidence decay.
        """
        start_time = time.time()
        warnings: List[str] = []
        
        # Validate request
        if request.entity_type != self.entity_type:
            raise ValueError(f"Wrong predictor for entity type {request.entity_type}")
        
        # Check cache
        cache_key = self._cache_key(request)
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if self._is_cache_valid(cached):
                return cached
        
        # Clamp prediction horizon
        max_to_time = request.from_time + self.max_prediction_horizon
        to_time = min(request.to_time, max_to_time)
        if to_time < request.to_time:
            warnings.append(
                f"Prediction horizon clamped to {self.max_prediction_horizon}"
            )
        
        # Clamp resolution
        resolution = max(
            self.min_resolution_seconds,
            min(request.resolution_seconds, self.max_resolution_seconds)
        )
        
        # Get current state
        state = await self.get_current_state(request.entity_id)
        if state is None:
            return PredictionResult(
                entity_id=request.entity_id,
                entity_type=request.entity_type,
                predictions=[],
                source=self.prediction_source,
                model_version=self.model_version,
                computation_time_ms=(time.time() - start_time) * 1000,
                warnings=["Entity not found or no current state available"],
            )
        
        # Generate predictions
        predictions = await self.predict_positions(
            state=state,
            from_time=request.from_time,
            to_time=to_time,
            resolution_seconds=resolution,
        )
        
        # Apply confidence decay and uncertainty growth
        predictions = self._apply_confidence_decay(predictions, state.timestamp)
        
        if request.include_uncertainty:
            predictions = self._apply_uncertainty_growth(predictions, state.timestamp)
        
        # Build result
        result = PredictionResult(
            entity_id=request.entity_id,
            entity_type=request.entity_type,
            predictions=predictions,
            source=self.prediction_source,
            model_version=self.model_version,
            computation_time_ms=(time.time() - start_time) * 1000,
            warnings=warnings,
        )
        
        # Cache result
        self._cache[cache_key] = result
        
        return result
    
    def calculate_confidence(self, prediction_age_seconds: float) -> float:
        """
        Calculate confidence based on time since last known position.
        
        Uses exponential decay with configurable half-life.
        """
        if prediction_age_seconds <= 0:
            return self.initial_confidence
        
        # Exponential decay: C(t) = C0 * (0.5)^(t/half_life)
        decay_factor = math.pow(0.5, prediction_age_seconds / self.confidence_half_life_seconds)
        confidence = self.initial_confidence * decay_factor
        
        return max(self.minimum_confidence, confidence)
    
    def calculate_uncertainty(self, prediction_age_seconds: float) -> UncertaintyCone:
        """
        Calculate uncertainty cone based on time since last known position.
        
        Uncertainty grows linearly with time.
        """
        radius = (
            self.base_uncertainty_meters + 
            self.uncertainty_growth_rate * prediction_age_seconds
        )
        
        return UncertaintyCone(radius_meters=radius)
    
    def _apply_confidence_decay(
        self,
        predictions: List[PredictedPosition],
        reference_time: datetime
    ) -> List[PredictedPosition]:
        """Apply confidence decay to all predictions."""
        for pred in predictions:
            age = (pred.timestamp - reference_time).total_seconds()
            pred.confidence = self.calculate_confidence(age)
        return predictions
    
    def _apply_uncertainty_growth(
        self,
        predictions: List[PredictedPosition],
        reference_time: datetime
    ) -> List[PredictedPosition]:
        """Apply uncertainty growth to all predictions."""
        for pred in predictions:
            age = (pred.timestamp - reference_time).total_seconds()
            pred.uncertainty = self.calculate_uncertainty(age)
        return predictions
    
    def _cache_key(self, request: PredictionRequest) -> str:
        """Generate cache key for a request."""
        return f"{request.entity_id}:{request.from_time.timestamp()}:{request.to_time.timestamp()}:{request.resolution_seconds}"
    
    def _is_cache_valid(self, result: PredictionResult) -> bool:
        """Check if cached result is still valid."""
        if not result.predictions:
            return False
        oldest = result.predictions[0]
        age = (datetime.now(timezone.utc) - oldest.created_at).total_seconds()
        return age < self._cache_ttl_seconds
    
    def clear_cache(self):
        """Clear the prediction cache."""
        self._cache.clear()


# === Utility Functions ===

def haversine_distance(p1: GeoPoint, p2: GeoPoint) -> float:
    """
    Calculate distance between two points using Haversine formula.
    
    Returns distance in meters.
    """
    R = 6371000  # Earth radius in meters
    
    lat1 = math.radians(p1.lat)
    lat2 = math.radians(p2.lat)
    dlat = math.radians(p2.lat - p1.lat)
    dlng = math.radians(p2.lng - p1.lng)
    
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c


def bearing_between(p1: GeoPoint, p2: GeoPoint) -> float:
    """
    Calculate initial bearing from p1 to p2.
    
    Returns bearing in degrees (0 = North, 90 = East).
    """
    lat1 = math.radians(p1.lat)
    lat2 = math.radians(p2.lat)
    dlng = math.radians(p2.lng - p1.lng)
    
    x = math.sin(dlng) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlng)
    
    bearing = math.atan2(x, y)
    return (math.degrees(bearing) + 360) % 360


def destination_point(start: GeoPoint, bearing_deg: float, distance_m: float) -> GeoPoint:
    """
    Calculate destination point given start, bearing, and distance.
    
    Uses spherical Earth model.
    """
    R = 6371000  # Earth radius in meters
    
    lat1 = math.radians(start.lat)
    lng1 = math.radians(start.lng)
    bearing = math.radians(bearing_deg)
    d = distance_m / R
    
    lat2 = math.asin(
        math.sin(lat1) * math.cos(d) +
        math.cos(lat1) * math.sin(d) * math.cos(bearing)
    )
    
    lng2 = lng1 + math.atan2(
        math.sin(bearing) * math.sin(d) * math.cos(lat1),
        math.cos(d) - math.sin(lat1) * math.sin(lat2)
    )
    
    return GeoPoint(
        lat=math.degrees(lat2),
        lng=math.degrees(lng2),
        altitude=start.altitude
    )


def interpolate_position(
    p1: GeoPoint,
    p2: GeoPoint,
    fraction: float
) -> GeoPoint:
    """
    Interpolate between two positions.
    
    Fraction of 0.0 returns p1, 1.0 returns p2.
    Uses great circle interpolation.
    """
    if fraction <= 0:
        return p1
    if fraction >= 1:
        return p2
    
    lat1 = math.radians(p1.lat)
    lng1 = math.radians(p1.lng)
    lat2 = math.radians(p2.lat)
    lng2 = math.radians(p2.lng)
    
    d = haversine_distance(p1, p2) / 6371000  # Angular distance
    
    if d < 1e-10:
        return p1
    
    a = math.sin((1-fraction)*d) / math.sin(d)
    b = math.sin(fraction*d) / math.sin(d)
    
    x = a * math.cos(lat1) * math.cos(lng1) + b * math.cos(lat2) * math.cos(lng2)
    y = a * math.cos(lat1) * math.sin(lng1) + b * math.cos(lat2) * math.sin(lng2)
    z = a * math.sin(lat1) + b * math.sin(lat2)
    
    lat3 = math.atan2(z, math.sqrt(x*x + y*y))
    lng3 = math.atan2(y, x)
    
    # Interpolate altitude if available
    alt = None
    if p1.altitude is not None and p2.altitude is not None:
        alt = p1.altitude + fraction * (p2.altitude - p1.altitude)
    
    return GeoPoint(
        lat=math.degrees(lat3),
        lng=math.degrees(lng3),
        altitude=alt
    )