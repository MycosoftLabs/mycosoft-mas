"""
Culture Vision AI Agent for Mycosoft MAS.

Petri dish image analysis: colony counting, contamination detection, growth rate
estimation, organism classification (bacteria, fungi, virus indicators).
Uses CultureVisionClient (OpenAI Vision and/or local GPU YOLO/SegFormer).
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.enums import AgentStatus

logger = logging.getLogger(__name__)


class CultureVisionAgent(BaseAgent):
    """Agent for petri dish and culture plate image analysis."""

    def __init__(
        self,
        agent_id: str,
        name: str = "Culture Vision Agent",
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(agent_id=agent_id, name=name, config=config or {})
        self.capabilities.update(
            {
                "colony_counting",
                "contamination_detection",
                "growth_estimation",
                "organism_classification",
                "petri_analysis",
            }
        )
        self._vision_client = None

    def _get_vision_client(self):
        if self._vision_client is None:
            try:
                from mycosoft_mas.integrations.culture_vision_client import (
                    CultureVisionClient,
                )

                self._vision_client = CultureVisionClient(self.config)
            except ImportError:
                pass
        return self._vision_client

    async def _initialize_services(self) -> None:
        self.status = AgentStatus.ACTIVE

    async def _check_services_health(self) -> Dict[str, Any]:
        client = self._get_vision_client()
        if client:
            return await client.health_check()
        return {"status": "unconfigured"}

    async def _check_resource_usage(self) -> Dict[str, Any]:
        return {"cpu": 0, "memory": 0}

    async def _handle_error_type(self, error_type: str, error: str) -> Dict[str, Any]:
        return {"status": "error", "type": error_type, "message": error}

    async def _handle_notification(self, notification: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "received", "notification": notification}

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle culture vision tasks: analyze petri dish images."""
        task_type = task.get("type", "")
        if task_type != "analyze_image":
            return {"status": "unhandled", "task_type": task_type}

        client = self._get_vision_client()
        if not client:
            return {"status": "error", "message": "CultureVisionClient not available"}

        image_url = task.get("image_url")
        image_base64 = task.get("image_base64")
        prefer_gpu = task.get("prefer_gpu", False)

        if not image_url and not image_base64:
            return {"status": "error", "message": "Missing image_url or image_base64"}

        try:
            result = await client.analyze_image(
                image_url=image_url,
                image_base64=image_base64,
                prefer_gpu=prefer_gpu,
            )
            if "error" in result:
                return {"status": "error", "message": result["error"]}
            return {"status": "success", "analysis": result}
        except Exception as e:
            logger.exception("Culture Vision analysis failed")
            return {"status": "error", "message": str(e)}

    async def process(self) -> None:
        await asyncio.sleep(0.1)
