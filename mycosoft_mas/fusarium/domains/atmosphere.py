"""
Atmosphere Intelligence Domain — TAC-O Integration

Processes weather, air quality, dispersion, and atmospheric data to produce
operational impact assessments and dispersion predictions for chemical/biological events.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from mycosoft_mas.fusarium.data.schemas import Assessment, Prediction, IntelligenceProduct
from mycosoft_mas.fusarium.nlm_bridge import NLMBridge


class AtmosphericObservation(BaseModel):
    observation_id: UUID = Field(default_factory=uuid4)
    location: Dict[str, float]
    temperature_c: float
    humidity_pct: float
    wind_speed_ms: float
    wind_direction_deg: float
    visibility_km: Optional[float] = None
    pressure_hpa: Optional[float] = None
    observed_at: datetime
    merkle_hash: str


class DispersionPrediction(BaseModel):
    """Atmospheric dispersion prediction for chemical or biological events."""
    plume_model: Dict[str, Any]
    affected_area_km2: float
    max_concentration_ppm: float
    time_to_peak_hours: float
    confidence: float = Field(ge=0.0, le=1.0)


class AtmosphericIntelligence:
    """Atmosphere ENVINT domain module."""

    def __init__(self, nlm_bridge: NLMBridge, db_pool=None):
        self.nlm_bridge = nlm_bridge
        self.db_pool = db_pool

    async def assess(self, observations: List[AtmosphericObservation]) -> List[Assessment]:
        """Assess atmospheric conditions for operational impact."""
        assessments = []
        for obs in observations:
            result = await self.nlm_bridge.assess_atmospheric(obs)
            assessments.append(Assessment(**result))
        return assessments

    async def predict_dispersion(self, release: Dict[str, Any]) -> DispersionPrediction:
        """Predict atmospheric dispersion using NLM and Earth-2 models."""
        result = await self.nlm_bridge.predict_dispersion(release)
        return DispersionPrediction(**result)

    async def generate_product(self, assessment: Assessment, context: str = "") -> IntelligenceProduct:
        """Generate formatted intelligence product."""
        product = await self.nlm_bridge.generate_intel_product(assessment, context)
        return IntelligenceProduct(**product.model_dump())
