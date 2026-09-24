"""FormSpace Engine API — September 23, 2026.

Product atlas / chart / dynamics / graphing endpoints.
Scientific FormSpace only — never Ollama / GGUF / chat LLM framing.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/formspace", tags=["formspace"])


class AtlasUpsertRequest(BaseModel):
    chart_id: Optional[str] = None
    name: Optional[str] = None
    version: str = "v1"
    modalities: List[str] = Field(default_factory=list)
    axes: List[str] = Field(default_factory=list)
    nlm_model_ids: List[str] = Field(default_factory=list)
    form_state: Dict[str, Any] = Field(default_factory=dict)
    provenance: Optional[str] = None
    public: bool = False


class GraphRequest(BaseModel):
    chart_id: str
    series: Optional[List[float]] = None
    use_demo_fixture: bool = False
    graph_kind: str = "trajectory"
    dt: float = Field(default=0.1, gt=0, le=10)
    a: float = Field(default=-0.5)
    b: float = Field(default=1.0)


class ExperimentRequest(BaseModel):
    chart_id: str
    kind: str = Field(default="recovery", description="recovery | trajectory")
    series: Optional[List[float]] = None
    use_demo_fixture: bool = False
    perturbation_index: int = Field(default=3, ge=0)
    perturbation_delta: float = Field(default=0.3)


class MemoryAppendRequest(BaseModel):
    type: str = "note"
    chart_id: Optional[str] = None
    content: Optional[str] = None
    summary: Dict[str, Any] = Field(default_factory=dict)
    nlm_model_id: Optional[str] = None


def _user_id(
    x_user_id: Optional[str] = None,
    x_mycosoft_user_id: Optional[str] = None,
) -> Optional[str]:
    return (x_user_id or x_mycosoft_user_id or "").strip() or None


@router.get("/health")
async def health() -> Dict[str, Any]:
    from mycosoft_mas.nlm.formspace.engine import get_formspace_engine

    return get_formspace_engine().health()


@router.get("/demo")
async def demo_catalog() -> Dict[str, Any]:
    """Logged-out demo catalog charts (registry rows, not live streams)."""
    from mycosoft_mas.nlm.formspace.engine import get_formspace_engine

    return get_formspace_engine().demo()


@router.get("/atlas")
async def get_atlas(
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
    x_mycosoft_user_id: Optional[str] = Header(
        default=None, alias="X-Mycosoft-User-Id"
    ),
) -> Dict[str, Any]:
    from mycosoft_mas.nlm.formspace.engine import get_formspace_engine

    return get_formspace_engine().atlas_list(user_id=_user_id(x_user_id, x_mycosoft_user_id))


@router.post("/atlas")
async def upsert_atlas(
    body: AtlasUpsertRequest,
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
    x_mycosoft_user_id: Optional[str] = Header(
        default=None, alias="X-Mycosoft-User-Id"
    ),
) -> Dict[str, Any]:
    from mycosoft_mas.nlm.formspace.engine import get_formspace_engine

    user_id = _user_id(x_user_id, x_mycosoft_user_id)
    result = get_formspace_engine().atlas_upsert(body.model_dump(), user_id=user_id)
    if not result.get("ok") and result.get("error") == "auth_required":
        raise HTTPException(status_code=401, detail=result.get("message"))
    if not result.get("ok") and result.get("error") == "forbidden":
        raise HTTPException(status_code=403, detail=result.get("message"))
    return result


@router.post("/graph")
async def graph_job(body: GraphRequest) -> Dict[str, Any]:
    from mycosoft_mas.nlm.formspace.engine import get_formspace_engine

    return get_formspace_engine().graph(
        chart_id=body.chart_id,
        series=body.series,
        use_demo_fixture=body.use_demo_fixture,
        graph_kind=body.graph_kind,
        dt=body.dt,
        a=body.a,
        b=body.b,
    )


@router.post("/experiment")
async def experiment_job(
    body: ExperimentRequest,
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
    x_mycosoft_user_id: Optional[str] = Header(
        default=None, alias="X-Mycosoft-User-Id"
    ),
) -> Dict[str, Any]:
    from mycosoft_mas.nlm.formspace.engine import get_formspace_engine

    return get_formspace_engine().experiment(
        chart_id=body.chart_id,
        kind=body.kind,
        series=body.series,
        use_demo_fixture=body.use_demo_fixture,
        perturbation_index=body.perturbation_index,
        perturbation_delta=body.perturbation_delta,
        user_id=_user_id(x_user_id, x_mycosoft_user_id),
    )


@router.get("/evidence")
async def evidence(limit: int = 50) -> Dict[str, Any]:
    from mycosoft_mas.nlm.formspace.engine import get_formspace_engine

    return get_formspace_engine().evidence_list(limit=max(1, min(limit, 200)))


@router.get("/memory")
async def memory_get(
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
    x_mycosoft_user_id: Optional[str] = Header(
        default=None, alias="X-Mycosoft-User-Id"
    ),
) -> Dict[str, Any]:
    from mycosoft_mas.nlm.formspace.engine import get_formspace_engine

    return get_formspace_engine().memory_list(
        _user_id(x_user_id, x_mycosoft_user_id)
    )


@router.post("/memory")
async def memory_post(
    body: MemoryAppendRequest,
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
    x_mycosoft_user_id: Optional[str] = Header(
        default=None, alias="X-Mycosoft-User-Id"
    ),
) -> Dict[str, Any]:
    from mycosoft_mas.nlm.formspace.engine import get_formspace_engine

    user_id = _user_id(x_user_id, x_mycosoft_user_id)
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Sign in to save FormSpace memory.",
        )
    return get_formspace_engine().memory_append(
        user_id,
        {
            "type": body.type,
            "chart_id": body.chart_id,
            "content": body.content,
            "summary": body.summary,
            "nlm_model_id": body.nlm_model_id,
        },
    )
