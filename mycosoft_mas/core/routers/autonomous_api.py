"""
Autonomous Research API Router
REST endpoints for autonomous experiments and hypothesis generation
"""

from fastapi import APIRouter, HTTPException, Body
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

router = APIRouter()

# Import engines
from mycosoft_mas.core.autonomous.experiment_engine import experiment_engine
from mycosoft_mas.core.autonomous.hypothesis_engine import hypothesis_engine


# --- Autonomous Experiments ---

class CreateExperimentRequest(BaseModel):
    hypothesis: str
    parameters: Optional[Dict[str, Any]] = None


class AdaptationRequest(BaseModel):
    reason: str
    change: str
    automated: bool = False


@router.get("/experiments")
async def list_experiments(status: Optional[str] = None):
    experiments = experiment_engine.list_experiments()
    if status:
        from mycosoft_mas.core.autonomous.experiment_engine import AutoExperimentStatus
        experiments = [e for e in experiments if e.status.value == status]
    return {"experiments": [e.dict() for e in experiments]}


@router.post("/experiments")
async def create_experiment(data: CreateExperimentRequest):
    experiment = await experiment_engine.create_experiment(data.hypothesis, data.parameters)
    return experiment.dict()


@router.get("/experiments/{experiment_id}")
async def get_experiment(experiment_id: str):
    experiment = experiment_engine.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return experiment.dict()


@router.post("/experiments/{experiment_id}/start")
async def start_experiment(experiment_id: str):
    try:
        experiment = await experiment_engine.start_experiment(experiment_id)
        return experiment.dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/experiments/{experiment_id}/pause")
async def pause_experiment(experiment_id: str):
    try:
        experiment = await experiment_engine.pause_experiment(experiment_id)
        return experiment.dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/experiments/{experiment_id}/resume")
async def resume_experiment(experiment_id: str):
    try:
        experiment = await experiment_engine.resume_experiment(experiment_id)
        return experiment.dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/experiments/{experiment_id}/abort")
async def abort_experiment(experiment_id: str, reason: str = Body(...)):
    try:
        experiment = await experiment_engine.abort_experiment(experiment_id, reason)
        return experiment.dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/experiments/{experiment_id}/results")
async def get_experiment_results(experiment_id: str):
    try:
        results = await experiment_engine.get_results(experiment_id)
        return results.dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/experiments/{experiment_id}/adaptations")
async def suggest_adaptations(experiment_id: str):
    try:
        adaptations = await experiment_engine.suggest_adaptation(experiment_id)
        return {"adaptations": [a.dict() for a in adaptations]}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/experiments/{experiment_id}/adapt")
async def apply_adaptation(experiment_id: str, data: AdaptationRequest):
    from mycosoft_mas.core.autonomous.experiment_engine import Adaptation
    from datetime import datetime
    adaptation = Adaptation(
        timestamp=datetime.utcnow().timestamp(),
        reason=data.reason,
        change=data.change,
        automated=data.automated
    )
    try:
        experiment = await experiment_engine.apply_adaptation(experiment_id, adaptation)
        return experiment.dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# --- Hypothesis Generation ---

class GenerateHypothesesRequest(BaseModel):
    context: str
    count: int = 5


class RefineHypothesisRequest(BaseModel):
    feedback: str


class CreateAgendaRequest(BaseModel):
    goals: List[str]
    priority: str = "high"


@router.post("/hypotheses/generate")
async def generate_hypotheses(data: GenerateHypothesesRequest):
    hypotheses = await hypothesis_engine.generate_from_context(data.context, data.count)
    return {"hypotheses": [h.dict() for h in hypotheses]}


@router.post("/hypotheses/from-data")
async def generate_from_data(data_id: str = Body(...), analysis_type: str = Body(...)):
    hypotheses = await hypothesis_engine.generate_from_data(data_id, analysis_type)
    return {"hypotheses": [h.dict() for h in hypotheses]}


@router.post("/hypotheses/from-literature")
async def generate_from_literature(query: str = Body(...), sources: Optional[List[str]] = Body(None)):
    hypotheses = await hypothesis_engine.generate_from_literature(query, sources)
    return {"hypotheses": [h.dict() for h in hypotheses]}


@router.post("/hypotheses/{hypothesis_id}/refine")
async def refine_hypothesis(hypothesis_id: str, data: RefineHypothesisRequest):
    try:
        hypothesis = await hypothesis_engine.refine_hypothesis(hypothesis_id, data.feedback)
        return hypothesis.dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/hypotheses/{hypothesis_id}/validate")
async def validate_hypothesis(hypothesis_id: str):
    try:
        validation = await hypothesis_engine.validate_hypothesis(hypothesis_id)
        return validation.dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/hypotheses/{hypothesis_id}/validation")
async def get_validation_status(hypothesis_id: str):
    validation = await hypothesis_engine.get_validation_status(hypothesis_id)
    return validation.dict()


@router.get("/literature/search")
async def search_literature(q: str, limit: int = 20):
    results = await hypothesis_engine.search_literature(q, limit)
    return {"results": [r.dict() for r in results]}


@router.post("/literature/analyze")
async def analyze_paper(doi: str = Body(...)):
    analysis = await hypothesis_engine.analyze_paper(doi)
    return analysis


@router.get("/patterns/discover")
async def discover_patterns(data_ids: str):
    ids = data_ids.split(",")
    patterns = await hypothesis_engine.discover_patterns(ids)
    return patterns


@router.get("/knowledge-gaps")
async def find_knowledge_gaps(domain: str):
    gaps = await hypothesis_engine.find_knowledge_gaps(domain)
    return {"gaps": gaps}


@router.post("/agenda")
async def create_agenda(data: CreateAgendaRequest):
    agenda = await hypothesis_engine.create_agenda(data.goals, data.priority)
    return agenda.dict()


@router.get("/agenda/{agenda_id}")
async def get_agenda(agenda_id: str):
    agenda = await hypothesis_engine.get_agenda(agenda_id)
    if not agenda:
        raise HTTPException(status_code=404, detail="Agenda not found")
    return agenda.dict()
