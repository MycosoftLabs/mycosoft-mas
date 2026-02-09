"""
Prediction Module - February 6, 2026

Prediction engine for CREP dashboard.
Provides future position predictions for aircraft, vessels, satellites,
wildlife, and environmental hazards.
"""

from .prediction_types import (
    EntityType,
    GeoPoint,
    PredictedPosition,
    PredictionRequest,
    PredictionResult,
    PredictionSource,
    UncertaintyCone,
    Velocity,
    EntityState,
    Waypoint,
    Route,
)

from .base_predictor import (
    BasePredictor,
    haversine_distance,
    bearing_between,
    destination_point,
    interpolate_position,
)

from .prediction_store import (
    PredictionStore,
    get_prediction_store,
)

from .aircraft_predictor import AircraftPredictor, predict_aircraft
from .vessel_predictor import VesselPredictor
from .satellite_predictor import SatellitePredictor
from .wildlife_predictor import WildlifePredictor
from .hazard_predictor import HazardPredictor
from .earth2_forecaster import Earth2Forecaster, get_earth2_forecaster


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