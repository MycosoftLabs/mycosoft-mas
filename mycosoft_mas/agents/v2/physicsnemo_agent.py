"""
PhysicsNeMo Agent
February 9, 2026

Coordinates PhysicsNeMo service lifecycle and physics inference requests.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List

import httpx

# Import BaseAgentV2 with fallback.
try:
    from .base_agent_v2 import BaseAgentV2
except ImportError:
    class BaseAgentV2:  # type: ignore[override]
        def __init__(self, agent_id: str, config: Any = None):
            self.agent_id = agent_id
            self.config = config
            self._task_handlers: Dict[str, Any] = {}

        @property
        def agent_type(self) -> str:
            return "base"

        @property
        def category(self) -> str:
            return "scientific"

        def get_capabilities(self) -> List[str]:
            return []

        async def execute_task(self, task: Any) -> Dict[str, Any]:
            handler = self._task_handlers.get(task.task_type)
            if not handler:
                return {"status": "error", "message": f"Unknown task type: {task.task_type}"}
            return await handler(task)


class PhysicsNeMoAgent(BaseAgentV2):
    def __init__(self, agent_id: str = "physicsnemo-agent", config: Any = None):
        super().__init__(agent_id, config)
        self.service_url = os.getenv("PHYSICSNEMO_API_URL", "http://localhost:8400").rstrip("/")
        self._task_handlers.update(
            {
                "health_check": self._health_check,
                "get_gpu_status": self._get_gpu_status,
                "list_models": self._list_models,
                "simulate_diffusion": self._simulate_diffusion,
                "simulate_fluid_flow": self._simulate_fluid_flow,
                "simulate_heat_transfer": self._simulate_heat_transfer,
                "simulate_reaction": self._simulate_reaction,
            }
        )

    @property
    def agent_type(self) -> str:
        return "physicsnemo-agent"

    @property
    def category(self) -> str:
        return "scientific"

    def get_capabilities(self) -> List[str]:
        return [
            "physics_simulation",
            "neural_operator",
            "pinn_solver",
            "cfd_surrogate",
            "gpu_status",
        ]

    async def _request(self, method: str, path: str, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.request(method, f"{self.service_url}{path}", json=payload)
            response.raise_for_status()
            return response.json()

    async def _health_check(self, task: Any) -> Dict[str, Any]:
        return await self._request("GET", "/health")

    async def _get_gpu_status(self, task: Any) -> Dict[str, Any]:
        return await self._request("GET", "/gpu/status")

    async def _list_models(self, task: Any) -> Dict[str, Any]:
        return await self._request("GET", "/physics/models")

    async def _simulate_diffusion(self, task: Any) -> Dict[str, Any]:
        payload = task.payload.get("params", {})
        return await self._request("POST", "/physics/diffusion", payload=payload)

    async def _simulate_fluid_flow(self, task: Any) -> Dict[str, Any]:
        payload = task.payload.get("params", {})
        return await self._request("POST", "/physics/fluid-flow", payload=payload)

    async def _simulate_heat_transfer(self, task: Any) -> Dict[str, Any]:
        payload = task.payload.get("params", {})
        return await self._request("POST", "/physics/heat-transfer", payload=payload)

    async def _simulate_reaction(self, task: Any) -> Dict[str, Any]:
        payload = task.payload.get("params", {})
        return await self._request("POST", "/physics/reaction", payload=payload)
