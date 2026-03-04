"""
SBIR/STTR Grant Agent for Mycosoft MAS.

SBIR.gov opportunity search, deadline tracking, eligibility matching,
proposal template generation. Uses SAM.gov, Grants.gov, and SBIR.gov clients.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.enums import AgentStatus

logger = logging.getLogger(__name__)


class GrantAgent(BaseAgent):
    """Agent for SBIR/STTR grant opportunities and federal funding."""

    def __init__(
        self,
        agent_id: str,
        name: str = "Grant Agent",
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(agent_id=agent_id, name=name, config=config or {})
        self.capabilities.update({"sbir", "sttr", "grants", "sam_gov", "grants_gov"})
        self._sbir = None
        self._grants_gov = None
        self._sam_gov = None

    def _get_sbir(self):
        if self._sbir is None:
            try:
                from mycosoft_mas.integrations.sbir_client import SbirClient
                self._sbir = SbirClient(self.config)
            except ImportError:
                pass
        return self._sbir

    def _get_grants_gov(self):
        if self._grants_gov is None:
            try:
                from mycosoft_mas.integrations.grants_gov_client import GrantsGovClient
                self._grants_gov = GrantsGovClient(self.config)
            except ImportError:
                pass
        return self._grants_gov

    def _get_sam_gov(self):
        if self._sam_gov is None:
            try:
                from mycosoft_mas.integrations.sam_gov_client import SamGovClient
                self._sam_gov = SamGovClient(self.config)
            except ImportError:
                pass
        return self._sam_gov

    async def _initialize_services(self) -> None:
        self.status = AgentStatus.ACTIVE

    async def _check_services_health(self) -> Dict[str, Any]:
        sbir = self._get_sbir()
        grants = self._get_grants_gov()
        sam = self._get_sam_gov()
        return {
            "sbir": await sbir.health_check() if sbir else {"status": "unavailable"},
            "grants_gov": await grants.health_check() if grants else {"status": "unavailable"},
            "sam_gov": await sam.health_check() if sam else {"status": "unavailable"},
        }

    async def _check_resource_usage(self) -> Dict[str, Any]:
        return {"cpu": 0, "memory": 0}

    async def _handle_error_type(self, error_type: str, error: str) -> Dict[str, Any]:
        return {"status": "error", "type": error_type, "message": error}

    async def _handle_notification(self, notification: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "received", "notification": notification}

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle grant tasks: search_sbir, search_grants, search_sam, fetch_opportunity."""
        task_type = task.get("type", "")
        if task_type == "search_sbir":
            sbir = self._get_sbir()
            if sbir:
                result = await sbir.search_solicitations(
                    keyword=task.get("keyword"),
                    agency=task.get("agency"),
                    open_only=task.get("open_only", False),
                    closed_only=task.get("closed_only", False),
                    rows=task.get("rows", 25),
                    start=task.get("start", 0),
                )
                return {"status": "success", "result": result}
        elif task_type == "search_sbir_awards":
            sbir = self._get_sbir()
            if sbir:
                year_val = task.get("year")
                if year_val is not None and not isinstance(year_val, int):
                    try:
                        year_val = int(year_val)
                    except (TypeError, ValueError):
                        year_val = None
                result = await sbir.search_awards(
                    agency=task.get("agency"),
                    company=task.get("company"),
                    year=year_val,
                    limit=task.get("limit", 25),
                )
                return {"status": "success", "result": result}
        elif task_type == "search_grants":
            grants = self._get_grants_gov()
            if grants:
                result = await grants.search(
                    keyword=task.get("keyword"),
                    opp_statuses=task.get("opp_statuses"),
                    agencies=task.get("agencies"),
                    rows=task.get("rows", 10),
                    offset=task.get("offset", 0),
                )
                return {"status": "success", "result": result}
        elif task_type == "fetch_grants_opportunity":
            grants = self._get_grants_gov()
            if grants:
                opp_id = task.get("opportunity_id")
                if not opp_id:
                    return {"status": "error", "message": "opportunity_id required"}
                result = await grants.fetch_opportunity(opp_id)
                return {"status": "success", "result": result}
        elif task_type == "search_sam_opportunities":
            sam = self._get_sam_gov()
            if sam:
                result = await sam.search_opportunities(
                    keyword=task.get("keyword"),
                    posted_from=task.get("posted_from"),
                    posted_to=task.get("posted_to"),
                    limit=task.get("limit", 25),
                    offset=task.get("offset", 0),
                )
                return {"status": "success", "result": result}
        return {"status": "unhandled", "task_type": task_type}

    async def process(self) -> None:
        await asyncio.sleep(0.1)
