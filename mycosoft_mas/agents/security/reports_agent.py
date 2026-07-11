"""
MYCA Reports Agent — company-wide document generation orchestration.

Assembles structured report context from MAS/MINDEX/soc_ops (and later finance/ops)
and either calls the website report engine or returns JSON context for builders.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.enums import AgentStatus

logger = logging.getLogger(__name__)

WEBSITE_REPORT_PATH = "/api/security/reports/generate"


class ReportsAgent(BaseAgent):
    """Orchestrate government-standard / company reports via MYCA."""

    def __init__(
        self,
        agent_id: str = "reports-agent",
        name: str = "MYCA Reports Agent",
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(agent_id=agent_id, name=name, config=config or {})
        self.capabilities.update(
            {
                "generate_report",
                "schedule_report",
                "assemble_context",
                "compliance_reports",
                "company_reports",
            }
        )
        self.website_base = (
            (config or {}).get("website_base_url")
            or os.getenv("WEBSITE_API_URL")
            or os.getenv("WEBSITE_BASE_URL")
            or "http://192.168.0.187:3000"
        ).rstrip("/")
        self.mas_base = (
            (config or {}).get("mas_base_url")
            or os.getenv("MAS_API_URL")
            or "http://127.0.0.1:8001"
        ).rstrip("/")

    async def _initialize_services(self) -> None:
        self.status = AgentStatus.ACTIVE

    async def _check_services_health(self) -> Dict[str, Any]:
        return {
            "website_base": self.website_base,
            "mas_base": self.mas_base,
            "status": "ok",
        }

    async def _check_resource_usage(self) -> Dict[str, Any]:
        return {"cpu": 0, "memory": 0}

    async def _handle_error_type(self, error_type: str, error: str) -> Dict[str, Any]:
        return {"status": "error", "type": error_type, "message": error}

    async def _handle_notification(self, notification: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "received", "notification": notification}

    async def assemble_compliance_context(self) -> Dict[str, Any]:
        """Pull live soc_ops compliance rows + score from MAS compliance API."""
        controls: List[Dict[str, Any]] = []
        score: Dict[str, Any] = {}
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                r = await client.get(f"{self.mas_base}/api/compliance/controls")
                if r.is_success:
                    controls = (r.json() or {}).get("controls") or []
            except Exception as exc:  # noqa: BLE001
                logger.warning("assemble_compliance_context controls: %s", exc)
            try:
                r = await client.get(f"{self.mas_base}/api/compliance/score")
                if r.is_success:
                    score = r.json() or {}
            except Exception as exc:  # noqa: BLE001
                logger.warning("assemble_compliance_context score: %s", exc)

        implemented = sum(1 for c in controls if c.get("implementation_state") == "implemented")
        partial = sum(1 for c in controls if c.get("implementation_state") == "partial")
        planned = sum(1 for c in controls if c.get("implementation_state") == "planned")
        return {
            "domain": "compliance",
            "as_of": datetime.now(timezone.utc).isoformat(),
            "score": score,
            "counts": {
                "total": len(controls),
                "implemented": implemented,
                "partial": partial,
                "planned": planned,
            },
            "controls": controls,
            "provenance": "mas_soc_ops.compliance_controls",
            "public_mode_note": (
                "Current posture is pre-sprint (honest). Do not publish numeric SPRS "
                "publicly until 2026-07-17 post. Use NEXT_PUBLIC_COMPLIANCE_PUBLIC_MODE."
            ),
        }

    async def generate_via_website(
        self,
        report_type: str,
        fmt: str = "json",
    ) -> Dict[str, Any]:
        """Call website MYCA Reports Agent endpoint (render layer)."""
        url = f"{self.website_base}{WEBSITE_REPORT_PATH}"
        payload = {"reportType": report_type, "format": fmt}
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        api_key = os.getenv("WEBSITE_INTERNAL_API_KEY") or os.getenv("MAS_API_KEY")
        if api_key:
            headers["X-API-Key"] = api_key
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(url, json=payload, headers=headers)
            body: Any
            try:
                body = r.json()
            except Exception:  # noqa: BLE001
                body = {"raw": r.text[:2000]}
            return {
                "status": "ok" if r.is_success else "error",
                "http_status": r.status_code,
                "report_type": report_type,
                "format": fmt,
                "result": body,
            }

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        task_type = (task.get("type") or task.get("action") or "").strip().lower()
        report_type = task.get("report_type") or task.get("reportType") or "cmmc-l2"
        fmt = task.get("format") or "json"

        if task_type in ("assemble_context", "report_context", "context"):
            domain = (task.get("domain") or "compliance").lower()
            if domain == "compliance":
                ctx = await self.assemble_compliance_context()
                return {"status": "success", "result": ctx}
            return {
                "status": "error",
                "error": f"domain '{domain}' report-context not yet wired — define shape with website builders",
            }

        if task_type in ("generate_report", "generate", "report"):
            # Prefer website render engine; always attach MAS context for audit
            context = await self.assemble_compliance_context()
            generated = await self.generate_via_website(str(report_type), str(fmt))
            return {
                "status": "success" if generated.get("status") == "ok" else "error",
                "result": {
                    "context_summary": context.get("counts"),
                    "generation": generated,
                },
            }

        if task_type in ("schedule_report", "schedule"):
            return {
                "status": "accepted",
                "result": {
                    "message": "Schedule via MAS/Cowork cron — weekly compliance snapshot recommended",
                    "suggested_cron": "0 9 * * 1",
                    "report_type": report_type,
                },
            }

        return {
            "status": "error",
            "error": f"unknown task type '{task_type}'",
            "supported": ["generate_report", "assemble_context", "schedule_report"],
        }
