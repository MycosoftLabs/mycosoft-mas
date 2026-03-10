"""
Avani API Router — Constitutional Governance Endpoints

Provides REST API access to the Avani-Micah governance system.

Author: Morgan Rockwell / Mycosoft Labs
Created: March 9, 2026
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from mycosoft_mas.avani.constitution.articles import CONSTITUTION, Tier, get_articles_by_tier
from mycosoft_mas.core.routers.api_keys import require_api_key_scoped
from mycosoft_mas.avani.constitution.red_lines import RED_LINES
from mycosoft_mas.avani.constitution.rights import RIGHTS_CHARTER, RightsDomain, get_rights_by_domain
from mycosoft_mas.avani.governor.governor import AvaniGovernor, GovernorDecision, Proposal, RiskTier
from mycosoft_mas.avani.season_engine.seasons import Season, SeasonEngine, SeasonMetrics
from mycosoft_mas.avani.vision.vision import VISION_PRINCIPLES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/avani", tags=["avani"])

# Shared instances (initialized on startup)
_season_engine: Optional[SeasonEngine] = None
_governor: Optional[AvaniGovernor] = None


def get_season_engine() -> SeasonEngine:
    global _season_engine
    if _season_engine is None:
        _season_engine = SeasonEngine(initial_season=Season.SPRING)
    return _season_engine


def get_governor() -> AvaniGovernor:
    global _governor
    if _governor is None:
        _governor = AvaniGovernor(season_engine=get_season_engine())
    return _governor


# --- Request/Response Models ---


class ProposalRequest(BaseModel):
    source_agent: str = Field(..., description="ID of the proposing agent")
    action_type: str = Field(..., description="Type of action proposed")
    description: str = Field(..., description="Description of the proposal")
    risk_tier: str = Field(default="low", description="Risk tier: none/low/medium/high/critical")
    ecological_impact: float = Field(default=0.0, ge=0.0, le=1.0)
    reversibility: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SeasonUpdateRequest(BaseModel):
    eco_stability: float = Field(default=1.0, ge=0.0, le=1.0)
    founder_latency_hours: float = Field(default=0.0, ge=0.0)
    toxicity_detected: bool = False
    critical_error: bool = False
    red_line_violated: bool = False
    all_systems_green: bool = True


# --- Endpoints ---


@router.get("/health")
async def avani_health():
    """Avani system health check."""
    engine = get_season_engine()
    gov = get_governor()
    return {
        "status": "healthy",
        "system": "avani-governor",
        "season": engine.current_season.value,
        "is_operational": engine.is_operational,
        "stats": gov.get_stats(),
    }


@router.get("/season")
async def get_season():
    """Get current seasonal state."""
    return get_season_engine().to_dict()


@router.post("/season/update")
async def update_season(
    request: SeasonUpdateRequest,
    auth: dict = require_api_key_scoped("avani:update"),
):
    """Update season metrics and evaluate transitions. Root authority derived from avani:root scope."""
    engine = get_season_engine()
    scopes = auth.get("scopes") or []
    is_root = "avani:root" in scopes
    metrics = SeasonMetrics(
        eco_stability=request.eco_stability,
        founder_latency_hours=request.founder_latency_hours,
        toxicity_detected=request.toxicity_detected,
        critical_error=request.critical_error,
        red_line_violated=request.red_line_violated,
        all_systems_green=request.all_systems_green,
    )
    result = engine.update(metrics, is_root=is_root)
    return {
        "transitioned": result is not None,
        "season": engine.to_dict(),
    }


@router.post("/evaluate")
async def evaluate_proposal(request: ProposalRequest):
    """Submit a proposal for constitutional evaluation."""
    gov = get_governor()
    try:
        proposal = Proposal(
            source_agent=request.source_agent,
            action_type=request.action_type,
            description=request.description,
            risk_tier=RiskTier.from_string(request.risk_tier),
            ecological_impact=request.ecological_impact,
            reversibility=request.reversibility,
            metadata=request.metadata,
        )
        decision = await gov.evaluate_proposal(proposal)
        return decision.to_dict()
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/constitution")
async def get_constitution(tier: Optional[str] = None):
    """Read constitutional articles, optionally filtered by tier."""
    if tier:
        try:
            t = Tier(tier.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid tier: {tier}. Valid: {[t.value for t in Tier]}",
            )
        articles = get_articles_by_tier(t)
    else:
        articles = CONSTITUTION

    return {
        "articles": {
            k: {"title": v.title, "text": v.text, "tier": v.tier.value}
            for k, v in articles.items()
        }
    }


@router.get("/rights")
async def get_rights(domain: Optional[str] = None):
    """Read the rights charter, optionally filtered by domain."""
    if domain:
        try:
            d = RightsDomain(domain.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid domain: {domain}. Valid: {[d.value for d in RightsDomain]}",
            )
        rights = get_rights_by_domain(d)
    else:
        rights = RIGHTS_CHARTER

    return {
        "rights": [
            {"id": r.id, "domain": r.domain.value, "statement": r.statement}
            for r in rights
        ]
    }


@router.get("/red-lines")
async def get_red_lines():
    """Read all red lines (absolute prohibitions)."""
    return {
        "red_lines": [
            {
                "id": rl.id,
                "prohibition": rl.prohibition,
                "consequence": rl.consequence,
            }
            for rl in RED_LINES
        ]
    }


@router.get("/vision")
async def get_vision_principles():
    """Read Vision principles (the anti-Ultron wisdom layer)."""
    return {
        "principles": [
            {
                "id": p.id,
                "statement": p.statement,
                "weight": p.weight,
                "question": p.question,
            }
            for p in VISION_PRINCIPLES
        ],
        "doctrine": (
            "Intelligence must preserve the conditions that allow life, "
            "diversity, and creativity to exist — even when those conditions "
            "appear inefficient or chaotic."
        ),
    }


@router.get("/decisions/recent")
async def get_recent_decisions():
    """Get recent governance decisions."""
    gov = get_governor()
    return {"decisions": gov.recent_decisions}


@router.get("/stats")
async def get_governance_stats():
    """Get governance statistics."""
    gov = get_governor()
    return gov.get_stats()
