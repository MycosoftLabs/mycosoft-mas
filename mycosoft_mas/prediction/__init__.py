"""
Prediction Module - February 6, 2026

Prediction engine for CREP dashboard.
Provides future position predictions for aircraft, vessels, satellites,
wildlife, and environmental hazards.
"""

from .aircraft_predictor import AircraftPredictor, predict_aircraft
from .base_predictor import (
    BasePredictor,
    bearing_between,
    destination_point,
    haversine_distance,
    interpolate_position,
)
from .earth2_forecaster import Earth2Forecaster, get_earth2_forecaster
from .hazard_predictor import HazardPredictor
from .prediction_store import (
    PredictionStore,
    get_prediction_store,
)
from .prediction_types import (
    EntityState,
    EntityType,
    GeoPoint,
    PredictedPosition,
    PredictionRequest,
    PredictionResult,
    PredictionSource,
    Route,
    UncertaintyCone,
    Velocity,
    Waypoint,
)
from .satellite_predictor import SatellitePredictor
from .vessel_predictor import VesselPredictor
from .wildlife_predictor import WildlifePredictor

__all__ = [
    # Types
    "EntityType",
    "GeoPoint",
    "PredictedPosition",
    "PredictionRequest",
    "PredictionResult",
    "PredictionSource",
    "UncertaintyCone",
    "Velocity",
    "EntityState",
    "Waypoint",
    "Route",
    # Base
    "BasePredictor",
    "haversine_distance",
    "bearing_between",
    "destination_point",
    "interpolate_position",
    # Store
    "PredictionStore",
    "get_prediction_store",
    # Predictors
    "AircraftPredictor",
    "predict_aircraft",
    "VesselPredictor",
    "SatellitePredictor",
    "WildlifePredictor",
    "HazardPredictor",
    "Earth2Forecaster",
    "get_earth2_forecaster",
]
