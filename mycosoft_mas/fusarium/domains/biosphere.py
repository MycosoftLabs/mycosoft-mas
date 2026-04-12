"""
Biosphere Intelligence Domain — TAC-O Integration

Processes biological anomaly detection, fungal/pathogen threat assessment, wildlife pattern disruption, marine mammal tracking, and biodiversity baseline monitoring.
Uses FCI bioelectric signals, GBIF, eBird, OBIS, iNaturalist, and MINDEX species data.
All outputs pass through AVANI ecological safety gate.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from mycosoft_mas.fusarium.data.schemas import Assessment, Prediction, IntelligenceProduct
from mycosoft_mas.fusarium.nlm_bridge import NLMBridge
from mycosoft_mas.fusarium.guardian.avani import MarineEcologicalGuard


class BiologicalAnomaly(BaseModel):
    """Biological anomaly detection result."""
    anomaly_id: UUID = Field(default_factory=uuid4)
    species: str
    anomaly_type: str  # "mass_die_off", "invasive_species", "unusual_behavior", "pathogen_outbreak"
    confidence: float
    location: Dict[str, float]
    observed_at: datetime
    avani_review: Dict[str, Any]
    recommendation: str


class BiosphereIntelligence:
    """Biosphere ENVINT domain module."""

    def __init__(self, nlm_bridge: NLMBridge, avani_guard: MarineEcologicalGuard, db_pool=None):
        self.nlm_bridge = nlm_bridge
        self.avani_guard = avani_guard
        self.db_pool = db_pool

    async def assess(self, observations: List[Dict[str, Any]]) -> List[BiologicalAnomaly]:
        """Run biological anomaly detection with AVANI ecological gate."""
        anomalies = []
        for obs in observations:
            result = await self.nlm_bridge.assess_biological(obs)
            avani_review = self.avani_guard.evaluate(result)
            
            anomaly = BiologicalAnomaly(
                species=result.get("species", "unknown"),
                anomaly_type=result.get("anomaly_type", "unknown"),
                confidence=result.get("confidence", 0.75),
                location=obs.get("location", {}),
                observed_at=obs.get("observed_at", datetime.utcnow()),
                avani_review=avani_review,
                recommendation=result.get("recommendation", "Monitor"),
            )
            anomalies.append(anomaly)
        return anomalies

    async def generate_product(self, anomaly: BiologicalAnomaly, context: str = "") -> IntelligenceProduct:
        """Generate formatted intelligence product from biological assessment."""
        product = await self.nlm_bridge.generate_intel_product(anomaly, context)
        return IntelligenceProduct(**product.model_dump())
