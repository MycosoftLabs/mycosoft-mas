"""
Hydrosphere Intelligence Domain — TAC-O Maritime Integration

Core ENVINT domain for underwater acoustic and oceanographic intelligence.
Processes maritime sensor package data, HYCOM ocean models, NOAA NDBC buoy data,
and produces sonar performance predictions, underwater threat classifications, and maritime
traffic pattern assessments.

All outputs are stored in MINDEX with Merkle provenance and pass through AVANI ecological safety gate.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from mycosoft_mas.fusarium.data.schemas import GeoPoint, Assessment, Prediction, IntelligenceProduct
from mycosoft_mas.integrations.zeetachec_client import MaritimeSensorNetworkClient
from mycosoft_mas.fusarium.nlm_bridge import NLMBridge


class HydroacousticObservation(BaseModel):
    """Raw or processed hydroacoustic observation from an underwater sensor."""
    observation_id: UUID = Field(default_factory=uuid4)
    sensor_id: str
    location: GeoPoint
    depth_m: float
    frequency_bands: List[tuple[float, float]] = Field(default_factory=list)
    spectral_energy: List[float] = Field(default_factory=list)
    broadband_level_db: float
    modulation_rate_hz: Optional[float] = None
    cavitation_index: Optional[float] = None
    ambient_noise_level_db: float = 0.0
    merkle_hash: str
    observed_at: datetime


class SonarPerformancePrediction(BaseModel):
    """Sonar detection range prediction for current ocean environment."""
    min_range_m: float
    max_range_m: float
    optimal_depth_m: float
    figure_of_merit_db: float
    confidence: float = Field(ge=0.0, le=1.0)
    environmental_factors: Dict[str, float] = Field(default_factory=dict)  # sound_speed, thermocline_depth, sea_state


class UnderwaterThreatAssessment(BaseModel):
    """Classified underwater contact assessment with AVANI review."""
    assessment_id: UUID = Field(default_factory=uuid4)
    classification: str = Field(..., pattern="^(submarine|surface_vessel|torpedo|uuv|mine|marine_mammal|fish_school|seismic|weather_noise|shipping_noise|ambient|unknown)$")
    confidence: float = Field(ge=0.0, le=1.0)
    avani_marine_mammal_score: float = Field(ge=0.0, le=1.0)
    avani_action: str = Field(..., pattern="^(pass|gate_for_human_review|veto)$")
    correlated_entities: List[UUID] = Field(default_factory=list)  # AIS tracks, satellite passes
    recommendation: str
    merkle_hash: str


class HydrosphereIntelligence:
    """Hydrosphere ENVINT domain module for TAC-O."""

    def __init__(self, nlm_bridge: NLMBridge, sensor_network_client: MaritimeSensorNetworkClient, db_pool=None):
        self.nlm_bridge = nlm_bridge
        self.sensor_network_client = sensor_network_client
        self.db_pool = db_pool

    async def assess(self, observations: List[HydroacousticObservation]) -> List[UnderwaterThreatAssessment]:
        """Run NLM classification on hydroacoustic observations with AVANI gate."""
        assessments = []
        for obs in observations:
            # Call NLM via bridge
            result = await self.nlm_bridge.classify_acoustic(obs)
            
            assessment = UnderwaterThreatAssessment(
                classification=result.get("classification", "unknown"),
                confidence=result.get("confidence", 0.75),
                avani_marine_mammal_score=result.get("marine_mammal_score", 0.0),
                avani_action=result.get("avani_action", "pass"),
                correlated_entities=result.get("correlated_entities", []),
                recommendation=result.get("recommendation", "Monitor contact"),
                merkle_hash=obs.merkle_hash,
            )
            assessments.append(assessment)
        
        return assessments

    async def predict_sonar_performance(self, environment: Dict[str, Any]) -> SonarPerformancePrediction:
        """Predict sonar performance using NLM SonarPerformancePredictionHead."""
        result = await self.nlm_bridge.predict_sonar(environment)
        return SonarPerformancePrediction(**result)

    async def generate_product(self, assessment: UnderwaterThreatAssessment, context: str = "") -> IntelligenceProduct:
        """Generate formatted intelligence product from assessment."""
        product = await self.nlm_bridge.generate_intel_product(assessment, context)
        return IntelligenceProduct(**product.model_dump())
