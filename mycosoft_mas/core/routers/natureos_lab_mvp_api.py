"""
NatureOS lab MVP — Chemputer + growth instrument summary (May 03, 2026).

BFFs call these with MAS_API_URL; agents read MINDEX only (no mock compounds / no fake telemetry).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/natureos/lab", tags=["natureos-lab-mvp"])

_chemputer: Any = None
_growth: Any = None


def _get_chemputer():
    global _chemputer
    if _chemputer is None:
        from mycosoft_mas.agents.lab.chemputer_agent import ChemputerAgent

        _chemputer = ChemputerAgent(
            agent_id="chemputer_agent",
            name="ChemputerAgent",
            config={},
        )
    return _chemputer


def _get_growth():
    global _growth
    if _growth is None:
        from mycosoft_mas.agents.lab.growth_analytics_agent import GrowthAnalyticsAgent

        _growth = GrowthAnalyticsAgent(
            agent_id="growth_analytics_agent",
            name="GrowthAnalyticsAgent",
            config={},
        )
    return _growth


class ChemputerPlanRequest(BaseModel):
    compound_id: str = Field(..., min_length=1, description="MINDEX bio.compound UUID")
    smiles: Optional[str] = Field(
        None,
        description="Ignored in MVP — plans are MINDEX-ID grounded only.",
    )


@router.post("/chemputer/plan")
async def chemputer_plan(body: ChemputerPlanRequest) -> Dict[str, Any]:
    agent = _get_chemputer()
    out = await agent.process_task(
        {
            "type": "plan_compound",
            "compound_id": body.compound_id,
            "smiles": body.smiles,
        }
    )
    if out.get("status") != "success":
        msg = str(out.get("message") or "")
        code = 404 if "compound_not_found" in msg else 502
        raise HTTPException(status_code=code, detail=out)
    return out


@router.get("/growth/instrument-summary")
async def growth_instrument_summary(limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    agent = _get_growth()
    out = await agent.process_task(
        {"type": "summarize_telemetry", "limit": limit, "offset": offset}
    )
    if out.get("status") != "success":
        raise HTTPException(status_code=502, detail=out)
    return out
