from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from mycosoft_mas.fusarium.data.schemas import Assessment, IntelligenceProduct
from mycosoft_mas.fusarium.nlm_bridge import NLMBridge


class SpaceEnvironmentObservation(BaseModel):
    observation_id: UUID = Field(default_factory=uuid4)
    location: Dict[str, float]
    kp_index: Optional[float] = None
    solar_flux: Optional[float] = None
    gnss_degradation_score: Optional[float] = None
    observed_at: datetime
    merkle_hash: str


class SpaceEnvironmentIntelligence:
    def __init__(self, nlm_bridge: NLMBridge, db_pool=None):
        self.nlm_bridge = nlm_bridge
        self.db_pool = db_pool

    async def assess(self, observations: List[SpaceEnvironmentObservation]) -> List[Assessment]:
        assessments: List[Assessment] = []
        for observation in observations:
            result = await self.nlm_bridge.assess_biological(
                {"domain": "space_environment", "observation": observation.model_dump()}
            )
            assessments.append(
                Assessment(
                    domain="space_environment",
                    classification=result.get("classification", "unknown"),
                    confidence=float(result.get("confidence", 0.5)),
                    summary=result.get("summary", "Space weather impact assessment"),
                    recommendation=result.get("recommendation"),
                    metadata={"source": "fusarium-space", "raw": result},
                    merkle_hash=observation.merkle_hash,
                )
            )
        return assessments

    async def generate_product(self, assessment: Assessment, context: str = "") -> IntelligenceProduct:
        data = await self.nlm_bridge.generate_intel_product(assessment, context)
        return IntelligenceProduct(**data)
