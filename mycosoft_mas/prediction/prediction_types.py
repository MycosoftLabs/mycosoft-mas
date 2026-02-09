"""
Prediction Types - February 6, 2026

Type definitions for the prediction engine.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class PredictionSource(str, Enum):
    """Source/method of prediction."""
    EXTRAPOLATION = "extrapolation"      # Simple vector projection
    FLIGHT_PLAN = "flight_plan"          # From filed flight plan
    ORBIT_PROPAGATION = "orbit_propagation"  # SGP4/SDP4
    ROUTE_PLAN = "route_plan"            # Ship destination routing
    MIGRATION_MODEL = "migration_model"  # Wildlife migration
    EARTH2_FORECAST = "earth2_forecast"  # Earth-2 model output
    STATISTICAL = "statistical"          # Statistical/ML model
    HAZARD_MODEL = "hazard_model"        # Hazard-specific model


class EntityType(str, Enum):
    """Types of entities that can be predicted."""
    AIRCRAFT = "aircraft"
    VESSEL = "vessel"
    SATELLITE = "satellite"
    WILDLIFE = "wildlife"
    STORM = "storm"
    WILDFIRE = "wildfire"
    EARTHQUAKE = "earthquake"
    WEATHER = "weather"


@dataclass
class GeoPoint:
    """Geographic point with optional altitude."""
    lat: float
    lng: float
    altitude: Optional[float] = None  # meters
    
    def to_dict(self) -> Dict[str, float]:
        d = {"lat": self.lat, "lng": self.lng}
        if self.altitude is not None:
            d["altitude"] = self.altitude
        return d
    
    @classmethod
    def from_dict(cls, d: Dict) -> "GeoPoint":
        return cls(
            lat=d["lat"],
            lng=d["lng"],
            altitude=d.get("altitude"),
        )


@dataclass
class Velocity:
    """Velocity vector."""
    speed: float  # m/s or knots depending on context
    heading: float  # degrees, 0 = north
    climb_rate: Optional[float] = None  # m/s, positive = ascending
    
    def to_dict(self) -> Dict[str, float]:
        d = {"speed": self.speed, "heading": self.heading}
        if self.climb_rate is not None:
            d["climb_rate"] = self.climb_rate
        return d


@dataclass
class UncertaintyCone:
    """Uncertainty region for predictions."""
    radius_meters: float  # Lateral uncertainty
    altitude_meters: Optional[float] = None  # Vertical uncertainty
    
    def to_dict(self) -> Dict[str, float]:
        d = {"radius_meters": self.radius_meters}
        if self.altitude_meters is not None:
            d["altitude_meters"] = self.altitude_meters
        return d


@dataclass
class PredictedPosition:
    """A single predicted position at a future time."""
    entity_id: str
    entity_type: EntityType
    timestamp: datetime
    position: GeoPoint
    velocity: Optional[Velocity] = None
    confidence: float = 1.0  # 0.0 to 1.0
    uncertainty: Optional[UncertaintyCone] = None
    prediction_source: PredictionSource = PredictionSource.EXTRAPOLATION
    model_version: str = "1.0"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type.value,
            "timestamp": self.timestamp.isoformat(),
            "position": self.position.to_dict(),
            "velocity": self.velocity.to_dict() if self.velocity else None,
            "confidence": self.confidence,
            "uncertainty": self.uncertainty.to_dict() if self.uncertainty else None,
            "prediction_source": self.prediction_source.value,
            "model_version": self.model_version,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, d: Dict) -> "PredictedPosition":
        return cls(
            entity_id=d["entity_id"],
            entity_type=EntityType(d["entity_type"]),
            timestamp=datetime.fromisoformat(d["timestamp"]),
            position=GeoPoint.from_dict(d["position"]),
            velocity=Velocity(**d["velocity"]) if d.get("velocity") else None,
            confidence=d.get("confidence", 1.0),
            uncertainty=UncertaintyCone(**d["uncertainty"]) if d.get("uncertainty") else None,
            prediction_source=PredictionSource(d.get("prediction_source", "extrapolation")),
            model_version=d.get("model_version", "1.0"),
            metadata=d.get("metadata", {}),
            created_at=datetime.fromisoformat(d["created_at"]) if d.get("created_at") else datetime.now(timezone.utc),
        )


@dataclass
class PredictionRequest:
    """Request for entity prediction."""
    entity_id: str
    entity_type: EntityType
    from_time: datetime
    to_time: datetime
    resolution_seconds: int = 60  # Time between predicted points
    include_uncertainty: bool = True
    
    @property
    def duration_seconds(self) -> float:
        return (self.to_time - self.from_time).total_seconds()
    
    @property
    def num_points(self) -> int:
        return max(1, int(self.duration_seconds / self.resolution_seconds))


@dataclass
class PredictionResult:
    """Result of a prediction request."""
    entity_id: str
    entity_type: EntityType
    predictions: List[PredictedPosition]
    source: PredictionSource
    model_version: str
    computation_time_ms: float
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type.value,
            "predictions": [p.to_dict() for p in self.predictions],
            "source": self.source.value,
            "model_version": self.model_version,
            "computation_time_ms": self.computation_time_ms,
            "warnings": self.warnings,
        }


@dataclass
class EntityState:
    """Current state of an entity (input to prediction)."""
    entity_id: str
    entity_type: EntityType
    timestamp: datetime
    position: GeoPoint
    velocity: Optional[Velocity] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Entity-specific fields
    flight_plan: Optional[Dict] = None  # For aircraft
    destination: Optional[str] = None   # For vessels
    tle_line1: Optional[str] = None     # For satellites
    tle_line2: Optional[str] = None     # For satellites
    species: Optional[str] = None       # For wildlife


@dataclass
class Waypoint:
    """A waypoint in a route or flight plan."""
    position: GeoPoint
    name: Optional[str] = None
    expected_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        d = {"position": self.position.to_dict()}
        if self.name:
            d["name"] = self.name
        if self.expected_time:
            d["expected_time"] = self.expected_time.isoformat()
        return d


@dataclass
class Route:
    """A planned route (flight plan, shipping route, etc.)."""
    waypoints: List[Waypoint]
    departure_time: Optional[datetime] = None
    arrival_time: Optional[datetime] = None
    route_type: str = "direct"  # direct, great_circle, shipping_lane, etc.