"""
Earth Search Agent — agent interface for planetary-scale unified search.

Allows any MAS agent or orchestrator to search across all life, environment,
infrastructure, space, and telemetry data via the standard agent task interface.

Capabilities: earth_search, species_search, environment_search, infrastructure_search,
              climate_search, transport_search, space_search, telecom_search, science_search

Created: March 15, 2026
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from mycosoft_mas.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class EarthSearchAgent(BaseAgent):
    """Agent providing planetary-scale search to the MAS orchestrator and other agents."""

    def __init__(
        self,
        agent_id: str = "earth-search-agent",
        name: str = "EarthSearchAgent",
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(agent_id=agent_id, name=name, config=config or {})
        self.capabilities = [
            "earth_search",
            "species_search",
            "environment_search",
            "infrastructure_search",
            "climate_search",
            "transport_search",
            "space_search",
            "telecom_search",
            "science_search",
            "crep_search",
        ]

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process search tasks from orchestrator or other agents."""
        task_type = task.get("type", "earth_search")
        query = task.get("query", "")
        domains = task.get("domains", [])
        domain_groups = task.get("domain_groups", [])
        geo = task.get("geo")
        limit = task.get("limit", 20)
        include_crep = task.get("include_crep", True)
        include_llm = task.get("include_llm", False)

        if not query:
            return {"status": "error", "error": "query is required"}

        # Map task_type to domain_groups if no explicit domains
        if not domains and not domain_groups:
            type_to_group = {
                "species_search": ["life"],
                "environment_search": ["environment"],
                "infrastructure_search": ["infrastructure"],
                "climate_search": ["climate"],
                "transport_search": ["transport"],
                "space_search": ["space"],
                "telecom_search": ["telecom"],
                "science_search": ["science"],
            }
            domain_groups = type_to_group.get(task_type, [])

        try:
            from mycosoft_mas.earth_search.models import EarthSearchQuery, GeoFilter
            from mycosoft_mas.earth_search.orchestrator import run_earth_search

            geo_filter = None
            if geo and isinstance(geo, dict):
                geo_filter = GeoFilter(
                    lat=geo["lat"],
                    lng=geo["lng"],
                    radius_km=geo.get("radius_km", 100),
                )

            search_query = EarthSearchQuery(
                query=query,
                domains=domains,
                domain_groups=domain_groups,
                geo=geo_filter,
                limit=limit,
                include_crep=include_crep,
                include_llm=include_llm,
                user_id=task.get("user_id"),
                session_id=task.get("session_id"),
            )

            response = await run_earth_search(search_query)

            return {
                "status": "success",
                "query": query,
                "total_results": response.total_count,
                "domains_searched": [d.value for d in response.domains_searched],
                "sources_queried": response.sources_queried,
                "results": [r.model_dump(mode="json") for r in response.results],
                "crep_commands": response.crep_commands,
                "llm_answer": response.llm_answer,
                "duration_ms": response.duration_ms,
            }

        except Exception as e:
            logger.error("EarthSearchAgent task failed: %s", e)
            return {"status": "error", "error": str(e)}
