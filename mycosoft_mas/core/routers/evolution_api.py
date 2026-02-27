from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field


router = APIRouter(prefix="/api/evolution", tags=["evolution"])


class EvaluationInput(BaseModel):
    improvement_id: str
    score: float = Field(..., ge=0, le=1)
    recommendation: str
    evaluator: Optional[str] = None
    risks: List[str] = Field(default_factory=list)
    benefits: List[str] = Field(default_factory=list)


DATA_DIR = Path("mycosoft_mas/runtime/idea_evolution")
REPORTS_DIR = DATA_DIR / "reports"
IDEAS_DOC = Path("docs/MYCA_Master_Ideas_Concepts_Resources.md")


def _read_json(path: Path) -> Optional[Any]:
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    import json

    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


@router.post("/run-scan")
async def run_full_scan() -> Dict[str, Any]:
    """Run a lightweight evolution scan."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.utcnow()
    ideas_count = 0
    if IDEAS_DOC.exists():
        ideas_count = sum(1 for line in IDEAS_DOC.read_text(encoding="utf-8").splitlines() if line.startswith("- "))

    report = {
        "timestamp": now.isoformat(),
        "ideas_doc_present": IDEAS_DOC.exists(),
        "ideas_line_count": ideas_count,
    }
    report_path = REPORTS_DIR / f"daily_scan_{now.strftime('%Y-%m-%d')}.json"
    _write_json(report_path, report)
    return {"status": "ok", "report": report}


@router.get("/ideas/status")
async def get_ideas_status() -> Dict[str, Any]:
    """Get current ideas implementation status."""
    status_path = DATA_DIR / "ideas_status.json"
    if not status_path.exists():
        return {"status": "empty", "items": []}
    return {"status": "ok", "items": _read_json(status_path)}


@router.get("/discoveries")
async def get_discoveries(limit: int = 50) -> Dict[str, Any]:
    """Get recent discoveries."""
    discoveries_path = DATA_DIR / "discoveries.json"
    if not discoveries_path.exists():
        return {"status": "empty", "items": []}
    data = _read_json(discoveries_path)
    if isinstance(data, list):
        return {"status": "ok", "items": data[:limit]}
    return {"status": "ok", "items": data}


@router.get("/recommendations")
async def get_recommendations() -> Dict[str, Any]:
    """Get prioritized recommendations."""
    recommendations_path = DATA_DIR / "recommendations.json"
    if not recommendations_path.exists():
        return {"status": "empty", "items": []}
    return {"status": "ok", "items": _read_json(recommendations_path)}


@router.post("/evaluate")
async def evaluate_improvement(payload: EvaluationInput) -> Dict[str, Any]:
    """Record a manual evaluation of an improvement."""
    evaluations_path = DATA_DIR / "evaluations.json"
    existing: List[Dict[str, Any]] = []
    if evaluations_path.exists():
        import json

        existing = json.loads(evaluations_path.read_text(encoding="utf-8"))

    entry = payload.dict()
    entry["evaluated_at"] = datetime.utcnow().isoformat()
    existing.append(entry)
    _write_json(evaluations_path, existing)
    return {"status": "ok", "item": entry}
