"""
Gap Agent API - Scan and report cross-repo gaps.

Exposes GapAgent scan results and suggested plans via REST.
"""

from fastapi import APIRouter, Query
from typing import Any, Dict

router = APIRouter(prefix="/agents/gap", tags=["gap-agent"])

_gap_agent_instance: Any = None


def _get_gap_agent():
    global _gap_agent_instance
    if _gap_agent_instance is None:
        try:
            from mycosoft_mas.agents.gap_agent import GapAgent
            _gap_agent_instance = GapAgent(
                agent_id="gap_agent",
                name="GapAgent",
                config={},
            )
        except Exception:
            return None
    return _gap_agent_instance


@router.get("/scan", response_model=Dict[str, Any])
async def gap_scan(full: bool = Query(False, description="Full scan (more TODOs/stubs)")) -> Dict[str, Any]:
    """Run gap scan: TODOs, FIXMEs, stubs, 501 routes, bridge gaps. Returns full report."""
    agent = _get_gap_agent()
    if agent is None:
        return {"status": "error", "message": "GapAgent not available", "result": {}}
    result = await agent.process_task({"type": "full_scan" if full else "scan", "full": full})
    return {"status": result.get("status", "success"), "result": result.get("result", {})}


@router.get("/plans", response_model=Dict[str, Any])
async def gap_plans() -> Dict[str, Any]:
    """Return suggested plans to fill gaps (from last scan or run a quick scan)."""
    agent = _get_gap_agent()
    if agent is None:
        return {"status": "error", "message": "GapAgent not available", "suggested_plans": []}
    result = await agent.process_task({"type": "suggest_plans"})
    plans = (result.get("result") or {}).get("suggested_plans", [])
    return {"status": "success", "suggested_plans": plans}


@router.get("/summary", response_model=Dict[str, Any])
async def gap_summary() -> Dict[str, Any]:
    """Return summary counts from last scan (or run quick scan)."""
    agent = _get_gap_agent()
    if agent is None:
        return {"status": "error", "message": "GapAgent not available", "summary": {}}
    result = await agent.process_task({"type": "scan"})
    report = result.get("result") or {}
    return {"status": "success", "summary": report.get("summary", {}), "workspace_roots": report.get("workspace_roots", [])}
