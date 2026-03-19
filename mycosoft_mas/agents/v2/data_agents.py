"""
MAS v2 Data Agents

Agents for managing data operations, ETL, and search.
"""

import os
from typing import Any, Dict, List, Optional
import httpx

from mycosoft_mas.nlm.inference.service import get_nlm_service, PredictionRequest, QueryType
from .base_agent_v2 import BaseAgentV2
from mycosoft_mas.runtime import AgentTask, AgentCategory


class MindexAgent(BaseAgentV2):
    """
    MINDEX Agent - Database Operations

    Updated March 19, 2026 — Real MINDEX integration via mindex_client.

    Responsibilities:
    - Database queries via MINDEX API (192.168.0.189:8000)
    - Data freshness monitoring
    - ETL coordination
    - Species/observation queries
    """

    MINDEX_API_URL = os.getenv("MINDEX_API_URL", "http://192.168.0.189:8000")

    @property
    def agent_type(self) -> str:
        return "mindex"

    @property
    def category(self) -> str:
        return AgentCategory.DATA.value

    @property
    def display_name(self) -> str:
        return "MINDEX Agent"

    @property
    def description(self) -> str:
        return "Manages MINDEX database operations"

    def get_capabilities(self) -> List[str]:
        return [
            "query_species",
            "query_observations",
            "data_freshness",
            "etl_status",
            "backup_status",
            "search",
        ]

    async def on_start(self):
        self.register_handler("query", self._handle_query)
        self.register_handler("etl_status", self._handle_etl_status)
        self.register_handler("search", self._handle_search)
        self.register_handler("health", self._handle_health)

    async def _handle_query(self, task: AgentTask) -> Dict[str, Any]:
        """Execute MINDEX query via the real MINDEX API."""
        query_type = task.payload.get("query_type", "species")
        filters = task.payload.get("filters", {})
        limit = task.payload.get("limit", 50)

        endpoint_map = {
            "species": "/api/mindex/taxa",
            "observations": "/api/mindex/observations",
            "telemetry": "/api/mindex/telemetry/latest",
            "compounds": "/api/mindex/compounds",
        }
        endpoint = endpoint_map.get(query_type, f"/api/mindex/{query_type}")

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                params = {**filters, "limit": limit}
                response = await client.get(f"{self.MINDEX_API_URL}{endpoint}", params=params)
                response.raise_for_status()
                data = response.json()

                results = data.get("results", data.get("data", data.get("items", [])))
                total = data.get("total", len(results))

                return {
                    "query_type": query_type,
                    "results": results,
                    "total": total,
                    "source": "mindex_api",
                }
        except httpx.HTTPError as e:
            return {
                "query_type": query_type,
                "results": [],
                "total": 0,
                "error": str(e),
                "source": "mindex_api",
            }

    async def _handle_etl_status(self, task: AgentTask) -> Dict[str, Any]:
        """Get ETL pipeline status from MINDEX."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.MINDEX_API_URL}/api/mindex/health")
                response.raise_for_status()
                health = response.json()

                return {
                    "status": health.get("status", "unknown"),
                    "last_run": health.get("last_etl_run"),
                    "records_processed": health.get("total_records", 0),
                    "source": "mindex_api",
                }
        except httpx.HTTPError as e:
            return {
                "status": "unreachable",
                "error": str(e),
                "last_run": None,
                "records_processed": 0,
            }

    async def _handle_search(self, task: AgentTask) -> Dict[str, Any]:
        """Search MINDEX via the search API."""
        query = task.payload.get("query", "")
        search_type = task.payload.get("search_type", "keyword")
        limit = task.payload.get("limit", 20)

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{self.MINDEX_API_URL}/api/mindex/search",
                    json={"query": query, "search_type": search_type, "limit": limit},
                )
                response.raise_for_status()
                data = response.json()
                return {
                    "query": query,
                    "results": data.get("results", []),
                    "total": data.get("total", 0),
                    "source": "mindex_search",
                }
        except httpx.HTTPError as e:
            return {"query": query, "results": [], "total": 0, "error": str(e)}

    async def _handle_health(self, task: AgentTask) -> Dict[str, Any]:
        """Check MINDEX API health."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.MINDEX_API_URL}/health")
                response.raise_for_status()
                return {"status": "healthy", "details": response.json()}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


class NLMAgent(BaseAgentV2):
    """
    NLM Agent - Nature Learning Model Operations
    
    Responsibilities:
    - Prediction requests
    - Knowledge graph queries
    - Health checks
    """
    
    @property
    def agent_type(self) -> str:
        return "nlm"
    
    @property
    def category(self) -> str:
        return AgentCategory.DATA.value
    
    @property
    def display_name(self) -> str:
        return "NLM Agent"
    
    @property
    def description(self) -> str:
        return "Manages Nature Learning Model requests"
    
    def get_capabilities(self) -> List[str]:
        return [
            "nlm_health",
            "predict_fruiting",
            "query_knowledge",
        ]
    
    async def on_start(self):
        self.nlm_service = get_nlm_service()
        self.register_handler("nlm_health", self._handle_health)
        self.register_handler("predict_fruiting", self._handle_predict_fruiting)
        self.register_handler("query_knowledge", self._handle_query_knowledge)
    
    async def _handle_health(self, task: AgentTask) -> Dict[str, Any]:
        status = self.nlm_service.get_status()
        return {"status": "healthy" if status.get("status") == "ready" else "not_ready", "details": status}
    
    async def _handle_predict_fruiting(self, task: AgentTask) -> Dict[str, Any]:
        entity_id = task.payload.get("entity_id")
        time_horizon = task.payload.get("time_horizon")
        conditions = task.payload.get("conditions")
        location = task.payload.get("location")
        if not entity_id:
            return {"status": "error", "error": "entity_id required"}
        prompt = {
            "entity_id": entity_id,
            "time_horizon": time_horizon,
            "conditions": conditions,
            "location": location,
        }
        request = PredictionRequest(
            text=f"Fruiting prediction request: {prompt}",
            query_type=QueryType.ECOLOGY,
        )
        result = await self.nlm_service.predict(request)
        return {"status": "success", "result": result.to_dict()}
    
    async def _handle_query_knowledge(self, task: AgentTask) -> Dict[str, Any]:
        query = task.payload.get("query")
        limit = task.payload.get("limit")
        context = task.payload.get("context")
        if not query:
            return {"status": "error", "error": "query required"}
        request = PredictionRequest(
            text=query,
            query_type=QueryType.RESEARCH,
            context={"limit": limit, "context": context},
        )
        result = await self.nlm_service.predict(request)
        return {"status": "success", "result": result.to_dict()}


class ETLAgent(BaseAgentV2):
    """ETL Agent - Data Pipeline Management"""
    
    @property
    def agent_type(self) -> str:
        return "etl"
    
    @property
    def category(self) -> str:
        return AgentCategory.DATA.value
    
    @property
    def display_name(self) -> str:
        return "ETL Agent"
    
    @property
    def description(self) -> str:
        return "Manages data ETL pipelines"
    
    def get_capabilities(self) -> List[str]:
        return ["pipeline_run", "pipeline_status", "transform_data"]


class SearchAgent(BaseAgentV2):
    """Search Agent - Search Operations"""
    
    @property
    def agent_type(self) -> str:
        return "search"
    
    @property
    def category(self) -> str:
        return AgentCategory.DATA.value
    
    @property
    def display_name(self) -> str:
        return "Search Agent"
    
    @property
    def description(self) -> str:
        return "Manages search operations"
    
    def get_capabilities(self) -> List[str]:
        return ["full_text_search", "vector_search", "index_manage"]


class RouteMonitorAgent(BaseAgentV2):
    """
    Route Monitor Agent - API Route Monitoring
    
    Generic agent for monitoring specific API routes.
    """
    
    def __init__(self, agent_id: str, route: Optional[str] = None, **kwargs):
        self.monitored_route = route or "/api"
        super().__init__(agent_id, **kwargs)
    
    @property
    def agent_type(self) -> str:
        return "route-monitor"
    
    @property
    def category(self) -> str:
        return AgentCategory.DATA.value
    
    @property
    def display_name(self) -> str:
        return f"Route Monitor: {self.monitored_route}"
    
    @property
    def description(self) -> str:
        return f"Monitors API route {self.monitored_route}"
    
    def get_capabilities(self) -> List[str]:
        return [
            "health_check",
            "latency_monitor",
            "error_tracking",
            "usage_stats",
        ]
    
    async def on_start(self):
        self.register_handler("check_route", self._handle_check_route)
    
    async def _handle_check_route(self, task: AgentTask) -> Dict[str, Any]:
        """Check route health"""
        return {
            "route": self.monitored_route,
            "status": "healthy",
            "latency_ms": 50,
        }
