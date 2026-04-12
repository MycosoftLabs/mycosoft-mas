from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from mycosoft_mas.fusarium.data.schemas import Assessment, IntelligenceProduct
from mycosoft_mas.fusarium.nlm_bridge import NLMBridge


class InfrastructureObservation(BaseModel):
    observation_id: UUID = Field(default_factory=uuid4)
    asset_id: str
    location: Dict[str, float]
    power_stability_score: Optional[float] = None
    comms_integrity_score: Optional[float] = None
    anomaly_score: float = Field(default=0.0, ge=0.0, le=1.0)
    observed_at: datetime
    merkle_hash: str


class InfrastructureIntelligence:
    def __init__(self, nlm_bridge: NLMBridge, db_pool=None):
        self.nlm_bridge = nlm_bridge
        self.db_pool = db_pool

    async def assess(self, observations: List[InfrastructureObservation]) -> List[Assessment]:
        assessments: List[Assessment] = []
        for observation in observations:
            result = await self.nlm_bridge.assess_biological(
                {"domain": "infrastructure", "observation": observation.model_dump()}
            )
            assessments.append(
                Assessment(
                    domain="infrastructure",
                    classification=result.get("classification", "degraded"),
                    confidence=float(result.get("confidence", max(0.35, observation.anomaly_score))),
                    summary=result.get("summary", "Infrastructure resilience assessment"),
                    recommendation=result.get("recommendation"),
                    metadata={"asset_id": observation.asset_id, "raw": result},
                    merkle_hash=observation.merkle_hash,
                )
            )
        return assessments

    async def generate_product(self, assessment: Assessment, context: str = "") -> IntelligenceProduct:
        data = await self.nlm_bridge.generate_intel_product(assessment, context)
        return IntelligenceProduct(**data)
