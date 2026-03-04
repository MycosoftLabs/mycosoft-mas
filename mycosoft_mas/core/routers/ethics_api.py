"""
MYCA Ethics API - Three-Gate Pipeline and Ethics Evaluation

Endpoints for evaluate, audit, attention-budget, simulate, constitution, health.

Created: March 3, 2026
"""

from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/ethics", tags=["ethics"])

# Lazy singletons
_engine = None
_auditor = None
_attention_budget = None
_simulator = None


def _get_engine():
    global _engine
    if _engine is None:
        from mycosoft_mas.ethics import EthicsEngine
        _engine = EthicsEngine()
    return _engine


def _get_auditor():
    global _auditor
    if _auditor is None:
        from mycosoft_mas.agents.incentive_auditor_agent import IncentiveAuditorAgent
        _auditor = IncentiveAuditorAgent()
    return _auditor


def _get_attention_budget():
    global _attention_budget
    if _attention_budget is None:
        from mycosoft_mas.ethics.attention_budget import AttentionBudget
        _attention_budget = AttentionBudget()
    return _attention_budget


def _get_simulator():
    global _simulator
    if _simulator is None:
        from mycosoft_mas.ethics.simulator import SecondOrderSimulator
        _simulator = SecondOrderSimulator()
    return _simulator


# Request models
class EvaluateInput(BaseModel):
    content: str = Field(..., min_length=1)
    context: Optional[Dict[str, Any]] = None


class AuditInput(BaseModel):
    content: str = Field(..., min_length=1)
    task_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class SimulateInput(BaseModel):
    action: str = Field(..., min_length=1)
    context: Optional[Dict[str, Any]] = None


@router.post("/evaluate")
async def evaluate(payload: EvaluateInput) -> Dict[str, Any]:
    """Run input through three-gate pipeline; return EthicsResult."""
    engine = _get_engine()
    result = await engine.evaluate(payload.content, payload.context)
    return result.to_dict()


@router.post("/audit")
async def audit(payload: AuditInput) -> Dict[str, Any]:
    """Run incentive gate audit; returns manipulation score, certainty theater, beneficiaries."""
    auditor = _get_auditor()
    record = await auditor.audit(
        payload.content,
        task_id=payload.task_id,
        context=payload.context,
    )
    return record


@router.get("/audit/{task_id}")
async def get_audit(task_id: str) -> Dict[str, Any]:
    """Get ethics audit record for a specific task."""
    auditor = _get_auditor()
    record = auditor.get_audit(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Audit not found for task_id={task_id}")
    return record


@router.get("/attention-budget/{channel}")
async def attention_budget_status(channel: str) -> Dict[str, Any]:
    """Check attention budget status for a channel."""
    budget = _get_attention_budget()
    return budget.get_status(channel)


@router.post("/simulate")
async def simulate(payload: SimulateInput) -> Dict[str, Any]:
    """Run second-order simulation on a proposed action."""
    sim = _get_simulator()
    result = await sim.simulate(payload.action, payload.context)
    return {
        "action": result.action,
        "causal_chain": [
            {"description": n.description, "order": n.order, "risk_flag": n.risk_flag, "confidence": n.confidence}
            for n in result.causal_chain
        ],
        "risk_flags": result.risk_flags,
        "overall_confidence": result.overall_confidence,
    }


@router.get("/constitution")
async def get_constitution() -> Dict[str, Any]:
    """Return the System Constitution for transparency."""
    path = Path(__file__).resolve().parent.parent.parent / "myca" / "constitution" / "SYSTEM_CONSTITUTION.md"
    if not path.exists():
        raise HTTPException(status_code=404, detail="System Constitution not found")
    text = path.read_text(encoding="utf-8")
    return {"constitution": text, "path": str(path)}


@router.get("/health")
async def ethics_health() -> Dict[str, Any]:
    """Ethics engine health check."""
    try:
        engine = _get_engine()
        auditor = _get_auditor()
        budget = _get_attention_budget()
        sim = _get_simulator()
        return {
            "status": "healthy",
            "components": {
                "ethics_engine": "ok",
                "incentive_auditor": "ok",
                "attention_budget": "ok",
                "simulator": "ok",
            },
        }
    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e),
        }
