"""
Error Triage API – expose ErrorTriageService via HTTP.

Provides endpoints to submit errors for triage and query triage history.
Created: February 17, 2026
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/errors/triage", tags=["errors", "triage"])


class TriageRequest(BaseModel):
    """Request to triage an error."""

    error_message: str = Field(..., description="Error message or exception text")
    source: str = Field(
        default="api", description="Source: chat, consciousness, api, background_task, vm_health"
    )
    context: Optional[Dict[str, Any]] = Field(None, description="Optional context")
    traceback: Optional[str] = Field(None, description="Optional traceback string")


class TriageResponse(BaseModel):
    """Response from triage."""

    error_id: str
    feasibility: str
    suggested_fix: Optional[str] = None
    file_path: Optional[str] = None
    line_hint: Optional[str] = None
    deploy_target: Optional[str] = None
    dispatched: bool = False


@router.post("", response_model=TriageResponse)
async def triage_error(req: TriageRequest) -> TriageResponse:
    """
    Submit an error for triage.

    Classifies as auto-fixable or requires-human, optionally dispatches
    to n8n autonomous-fix webhook.
    """
    try:
        from mycosoft_mas.services.error_triage_service import (
            FixFeasibility,
            get_error_triage_service,
        )

        svc = get_error_triage_service()
        result = await svc.triage(
            error_message=req.error_message,
            source=req.source,
            context=req.context,
            traceback=req.traceback,
        )
        dispatched = result.feasibility == FixFeasibility.AUTO_FIXABLE and bool(
            svc._n8n_webhook_url
        )
        return TriageResponse(
            error_id=result.error_id,
            feasibility=result.feasibility.value,
            suggested_fix=result.suggested_fix,
            file_path=result.file_path,
            line_hint=result.line_hint,
            deploy_target=result.deploy_target,
            dispatched=dispatched,
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Triage failed")


@router.get("/history")
async def get_triage_history(limit: int = 50) -> Dict[str, Any]:
    """
    Return recent triage history.
    """
    try:
        from mycosoft_mas.services.error_triage_service import get_error_triage_service

        svc = get_error_triage_service()
        items = svc.get_recent_triages(limit=limit)
        return {
            "items": items,
            "count": len(items),
        }
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to get triage history")
