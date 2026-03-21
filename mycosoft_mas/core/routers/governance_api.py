"""
Governance API for multi-stakeholder impact checks.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from mycosoft_mas.governance import StakeholderGateEngine

router = APIRouter(prefix="/api/governance", tags=["governance"])
engine = StakeholderGateEngine()


class ImpactRequest(BaseModel):
    action: str = Field(..., min_length=1)
    context: Dict[str, Any] = Field(default_factory=dict)


class StakeholdersResponse(BaseModel):
    stakeholders: List[str]


@router.post("/assess-impact")
async def assess_impact(req: ImpactRequest) -> Dict[str, Any]:
    assessment = engine.assess(req.action, req.context)
    return assessment.to_dict()


@router.get("/stakeholders", response_model=StakeholdersResponse)
async def list_stakeholders(custom: Optional[str] = None) -> StakeholdersResponse:
    stakeholders = list(StakeholderGateEngine.DEFAULT_STAKEHOLDERS)
    if custom:
        for item in custom.split(","):
            name = item.strip()
            if name and name not in stakeholders:
                stakeholders.append(name)
    return StakeholdersResponse(stakeholders=stakeholders)
