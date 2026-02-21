"""
NatureOS Simulation Agent

Runs simulation tasks and Earth-2 forecasts via NatureOS/MAS integrations.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.integrations.natureos_client import NATUREOSClient

logger = logging.getLogger(__name__)


class NatureOSSimulationAgent(BaseAgent):
    """Handles NatureOS simulation and Earth-2 forecast tasks."""

    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        super().__init__(agent_id=agent_id, name=name, config=config)
        self.capabilities = ["run_simulation", "earth2_forecast"]
        self.client = NATUREOSClient()

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        task_type = task.get("type", "")
        handlers = {
            "run_simulation": self._handle_run_simulation,
            "earth2_forecast": self._handle_earth2_forecast,
        }
        handler = handlers.get(task_type)
        if not handler:
            return {"status": "error", "message": f"Unknown task type: {task_type}"}
        return await handler(task)

    async def _handle_run_simulation(self, task: Dict[str, Any]) -> Dict[str, Any]:
        simulation_type = (
            task.get("simulation_type")
            or task.get("function_name")
            or task.get("simulation")
            or ""
        )
        params = task.get("params") or task.get("payload") or {}

        if not simulation_type:
            return {"status": "error", "message": "simulation_type is required"}

        try:
            result = await self.client.run_simulation(
                simulation_type=str(simulation_type),
                params=params if isinstance(params, dict) else {"params": params},
            )
            return {"status": "success", "result": result}
        except Exception as exc:  # pragma: no cover - network errors
            logger.exception("NatureOS simulation failed")
            return {"status": "error", "message": str(exc)}

    async def _handle_earth2_forecast(self, task: Dict[str, Any]) -> Dict[str, Any]:
        payload = task.get("payload") or task.get("params") or {}
        if not isinstance(payload, dict) or not payload:
            return {"status": "error", "message": "forecast payload is required"}

        try:
            result = await self.client.get_earth2_forecast(payload)
            return {"status": "success", "result": result}
        except Exception as exc:  # pragma: no cover - network errors
            logger.exception("Earth-2 forecast failed")
            return {"status": "error", "message": str(exc)}
