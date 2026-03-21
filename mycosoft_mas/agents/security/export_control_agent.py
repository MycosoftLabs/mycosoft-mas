"""
ITAR/EAR Export Control Agent for Mycosoft MAS.

ITAR classification, EAR ECCN lookup, deemed export screening, license tracking.
"""

import logging
from typing import Any, Dict, Optional

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.enums import AgentStatus

logger = logging.getLogger(__name__)


class ExportControlAgent(BaseAgent):
    """
    Agent for ITAR/EAR export control compliance.
    """

    def __init__(
        self,
        agent_id: str,
        name: str = "Export Control Agent",
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(agent_id=agent_id, name=name, config=config or {})
        self.capabilities.update(
            {
                "itar",
                "ear",
                "eccn",
                "usml",
                "deemed_export",
                "screening",
                "license_tracking",
                "export_compliance",
            }
        )
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from mycosoft_mas.integrations.export_control_client import ExportControlClient

                self._client = ExportControlClient(self.config)
            except ImportError:
                logger.warning("ExportControlClient not available")
        return self._client

    async def _initialize_services(self) -> None:
        self.status = AgentStatus.ACTIVE

    async def _check_services_health(self) -> Dict[str, Any]:
        client = self._get_client()
        if client:
            return await client.health_check()
        return {"status": "unavailable"}

    async def _check_resource_usage(self) -> Dict[str, Any]:
        return {"memory_mb": 0, "cpu_percent": 0}

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process export control tasks."""
        task_type = task.get("type", "")
        payload = task.get("payload", {})

        if task_type == "itar_classify":
            return await self._itar_classify(payload)
        if task_type == "eccn_lookup":
            return await self._eccn_lookup(payload)
        if task_type == "deemed_export_screen":
            return await self._deemed_export_screen(payload)
        if task_type == "license_track":
            return await self._license_track(payload)
        if task_type == "list_usml":
            return await self._list_usml(payload)

        return {
            "status": "error",
            "error": f"Unknown task type: {task_type}",
            "supported": [
                "itar_classify",
                "eccn_lookup",
                "deemed_export_screen",
                "license_track",
                "list_usml",
            ],
        }

    async def _itar_classify(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """ITAR USML category classification guidance."""
        client = self._get_client()
        category = payload.get("category", "").strip().upper()
        if not category:
            return {
                "status": "ok",
                "result": {
                    "usml_categories": client.list_usml_categories() if client else {},
                    "message": "Provide 'category' (e.g., I, VII, XI) for specific lookup",
                },
            }
        if client:
            info = client.get_usml_category(category)
            if info:
                return {"status": "ok", "result": info}
        return {"status": "error", "error": f"Unknown USML category: {category}"}

    async def _eccn_lookup(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """EAR ECCN lookup and parsing."""
        client = self._get_client()
        eccn = payload.get("eccn", "").strip()
        if not eccn:
            cats = client.list_eccn_categories() if client else {}
            return {
                "status": "ok",
                "result": {
                    "eccn_categories": cats,
                    "message": "Provide 'eccn' (e.g., 3A001, 4D994) for parsing",
                },
            }
        if client:
            parsed = client.parse_eccn(eccn)
            if parsed.get("valid"):
                return {"status": "ok", "result": parsed}
            return {"status": "error", "error": parsed.get("error", "Invalid ECCN")}
        return {"status": "error", "error": "Export control client not available"}

    async def _deemed_export_screen(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Screen entity for deemed export (foreign person/entity screening)."""
        client = self._get_client()
        name = payload.get("name", "").strip()
        countries = payload.get("countries")
        if isinstance(countries, str):
            countries = [c.strip() for c in countries.split(",") if c.strip()]
        if not name:
            return {"status": "error", "error": "Provide 'name' to screen"}
        if client:
            result = await client.screen_entity(name, countries)
            return {
                "status": "ok",
                "result": {
                    "screening": result,
                    "note": "Manual verification required for any matches",
                },
            }
        return {
            "status": "ok",
            "result": {
                "message": "Screening API not configured (TRADE_GOV_API_KEY). Screen manually.",
                "screening": {"status": "not_configured", "matches": []},
            },
        }

    async def _license_track(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """License tracking placeholder (BIS DECCS integration when available)."""
        license_id = payload.get("license_id", "")
        return {
            "status": "ok",
            "result": {
                "message": "License tracking requires BIS DECCS or internal system integration",
                "license_id": license_id,
                "tracking": "not_implemented",
            },
        }

    async def _list_usml(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """List all USML categories."""
        client = self._get_client()
        if client:
            cats = client.list_usml_categories()
            return {"status": "ok", "result": {"usml_categories": cats}}
        return {"status": "error", "error": "Client not available"}
