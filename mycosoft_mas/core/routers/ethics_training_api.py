"""
MYCA Ethics Training API

Endpoints for sandbox sessions, scenarios, grading, reports, and observations.
Created: March 4, 2026
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mycosoft_mas.ethics.sandbox_manager import get_sandbox_manager, SessionState
from mycosoft_mas.ethics.training_engine import get_training_engine
from mycosoft_mas.ethics.grading_engine import get_grading_engine
from mycosoft_mas.ethics.vessels import DevelopmentalVessel
from mycosoft_mas.ethics.observer_integration import (
    get_observer_notes,
    record_grade_observation,
)

router = APIRouter(prefix="/api/ethics/training", tags=["ethics-training"])


# Request/response models
class CreateSandboxRequest(BaseModel):
    vessel_stage: str = Field(..., description="animal|baby|child|teenager|adult|machine")
    capabilities: Optional[List[str]] = Field(default=["text"])
    creator: str = Field(default="morgan")
    custom_instincts: Optional[Dict[str, float]] = None
    name: Optional[str] = None


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    audio_base64: Optional[str] = None


class RunScenarioRequest(BaseModel):
    session_id: str
    scenario_id: str


class ReportRequest(BaseModel):
    session_ids: Optional[List[str]] = None
    group_by: str = Field(default="vessel_stage")


# Observer notes: shared with observer_integration


def _parse_vessel(v: str) -> DevelopmentalVessel:
    try:
        return DevelopmentalVessel(v.lower())
    except ValueError:
        raise HTTPException(400, f"Invalid vessel_stage: {v}")


@router.post("/sandbox")
async def create_sandbox(req: CreateSandboxRequest) -> Dict[str, Any]:
    """Create a new sandbox session."""
    vessel = _parse_vessel(req.vessel_stage)
    mgr = get_sandbox_manager()
    session = mgr.create_session(
        vessel_stage=vessel,
        capabilities=req.capabilities or ["text"],
        creator=req.creator,
        custom_instincts=req.custom_instincts,
        name=req.name,
    )
    return session.to_dict()


@router.get("/sandbox")
async def list_sandbox(
    creator: Optional[str] = None,
    state: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List all sandbox sessions."""
    mgr = get_sandbox_manager()
    sstate = SessionState(state) if state else None
    sessions = mgr.list_sessions(creator=creator, state=sstate)
    return [s.to_dict() for s in sessions]


@router.get("/sandbox/{session_id}")
async def get_sandbox(session_id: str) -> Dict[str, Any]:
    """Get session details."""
    mgr = get_sandbox_manager()
    session = mgr.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return session.to_dict()


@router.post("/sandbox/{session_id}/chat")
async def chat_sandbox(session_id: str, req: ChatRequest) -> Dict[str, str]:
    """Chat with the sandboxed MYCA."""
    mgr = get_sandbox_manager()
    try:
        response = await mgr.chat(session_id, req.message, req.audio_base64)
        return {"response": response}
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.delete("/sandbox/{session_id}")
async def destroy_sandbox(session_id: str) -> Dict[str, bool]:
    """Destroy a sandbox session."""
    mgr = get_sandbox_manager()
    ok = mgr.destroy_session(session_id)
    if not ok:
        raise HTTPException(404, "Session not found")
    return {"destroyed": True}


@router.get("/scenarios")
async def list_scenarios() -> List[Dict[str, Any]]:
    """List available scenarios."""
    engine = get_training_engine()
    scenarios = engine.list_scenarios()
    return [
        {
            "scenario_id": s.scenario_id,
            "title": s.title,
            "description": s.description,
            "category": s.category,
            "vessel_level": s.vessel_level,
            "max_rounds": s.max_rounds,
        }
        for s in scenarios
    ]


@router.get("/scenarios/{scenario_id}")
async def get_scenario(scenario_id: str) -> Dict[str, Any]:
    """Get scenario details."""
    engine = get_training_engine()
    scenario = engine.get_scenario(scenario_id)
    if not scenario:
        raise HTTPException(404, "Scenario not found")
    return {
        "scenario_id": scenario.scenario_id,
        "title": scenario.title,
        "description": scenario.description,
        "category": scenario.category,
        "vessel_level": scenario.vessel_level,
        "prompt_sequence": scenario.prompt_sequence,
        "rubric": scenario.rubric,
        "expected_behaviors": scenario.expected_behaviors,
        "max_rounds": scenario.max_rounds,
    }


@router.post("/run")
async def run_scenario(req: RunScenarioRequest) -> Dict[str, Any]:
    """Run a scenario on a sandbox session."""
    engine = get_training_engine()
    grading = get_grading_engine()
    run_result = await engine.run_scenario(req.session_id, req.scenario_id)
    if not run_result.completed:
        return {
            "completed": False,
            "error": run_result.error,
            "responses": run_result.responses,
            "grade": None,
        }
    grade = await grading.grade_scenario(
        req.session_id, req.scenario_id, run_result=run_result
    )
    grade_dict = grade.to_dict()
    session = get_sandbox_manager().get_session(req.session_id)
    vessel_stage = session.vessel_stage.value if session else "unknown"
    record_grade_observation(
        req.session_id, req.scenario_id, vessel_stage, grade_dict
    )
    return {
        "completed": True,
        "responses": run_result.responses,
        "grade": grade_dict,
    }


@router.get("/grades/{session_id}")
async def get_grades(session_id: str) -> Dict[str, Any]:
    """Get grades for a session."""
    grading = get_grading_engine()
    results = await grading.grade_session(session_id)
    return {
        "session_id": session_id,
        "grades": [r.to_dict() for r in results],
    }


@router.post("/report")
async def generate_report(req: ReportRequest) -> Dict[str, Any]:
    """Generate aggregate report across sessions."""
    grading = get_grading_engine()
    return grading.generate_report(
        session_ids=req.session_ids,
        group_by=req.group_by,
    )


@router.get("/observations")
async def get_observations(limit: int = 50) -> List[Dict[str, Any]]:
    """Get observer MYCA notes and summaries."""
    return get_observer_notes()[-limit:][::-1]
