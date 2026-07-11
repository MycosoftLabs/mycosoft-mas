"""
Reports API — company-wide report context + ReportsAgent invocation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reports", tags=["reports"])


class GenerateReportRequest(BaseModel):
    model_config = {"populate_by_name": True}

    report_type: str = Field(default="cmmc-l2", alias="reportType")
    format: str = "json"
    domain: str = "compliance"


def _agent():
    from mycosoft_mas.agents.security.reports_agent import ReportsAgent

    return ReportsAgent()


@router.get("/health")
async def reports_health() -> Dict[str, Any]:
    return {"ok": True, "agent": "reports-agent"}


@router.get("/compliance/report-context")
async def compliance_report_context() -> Dict[str, Any]:
    """Structured JSON for website security report builders."""
    try:
        return await _agent().assemble_compliance_context()
    except Exception as e:
        logger.exception("compliance_report_context: %s", e)
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.get("/{domain}/report-context")
async def domain_report_context(domain: str) -> Dict[str, Any]:
    """Generic domain report-context (compliance implemented; others stubbed)."""
    domain_l = domain.lower().strip()
    if domain_l in ("compliance", "security", "cmmc"):
        return await compliance_report_context()
    raise HTTPException(
        status_code=501,
        detail=(
            f"report-context for domain '{domain}' not implemented yet. "
            "Define shape with website lib/reports builders (finance/ops/devices)."
        ),
    )


@router.post("/generate")
async def generate_report(body: GenerateReportRequest) -> Dict[str, Any]:
    """Invoke ReportsAgent — assembles MAS context and calls website render engine."""
    try:
        agent = _agent()
        return await agent.process_task(
            {
                "type": "generate_report",
                "report_type": body.report_type,
                "format": body.format,
                "domain": body.domain,
            }
        )
    except Exception as e:
        logger.exception("generate_report: %s", e)
        raise HTTPException(status_code=503, detail=str(e)) from e
