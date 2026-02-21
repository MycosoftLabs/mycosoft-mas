"""
NatureOS Digital Twin Agent

Synchronizes device telemetry for digital twin workflows.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.integrations.natureos_client import NATUREOSClient

logger = logging.getLogger(__name__)


class DigitalTwinAgent(BaseAgent):
    """Handles MycoBrain device synchronization for digital twins."""

    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        super().__init__(agent_id=agent_id, name=name, config=config)
        self.capabilities = ["sync_digital_twin", "get_device_telemetry"]
        self.client = NATUREOSClient()

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        task_type = task.get("type", "")
        handlers = {
            "sync_digital_twin": self._handle_sync_digital_twin,
            "get_device_telemetry": self._handle_sync_digital_twin,
        }
        handler = handlers.get(task_type)
        if not handler:
            return {"status": "error", "message": f"Unknown task type: {task_type}"}
        return await handler(task)

    async def _handle_sync_digital_twin(self, task: Dict[str, Any]) -> Dict[str, Any]:
        device_id = task.get("device_id") or task.get("deviceId") or task.get("id")
        if not device_id:
            return {"status": "error", "message": "device_id is required"}

        try:
            result = await self.client.sync_digital_twin(str(device_id))
            return {"status": "success", "result": result}
        except Exception as exc:  # pragma: no cover - network errors
            logger.exception("Digital twin sync failed")
            return {"status": "error", "message": str(exc)}
