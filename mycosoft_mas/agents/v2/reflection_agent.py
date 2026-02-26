"""
Reflection Agent - Wraps ReflectionService for agent-based invocation.
Capabilities: log_response, analyze_outcome, create_learning_task.
Created: February 17, 2026
"""

from __future__ import annotations

import logging
from typing import Any, Dict

try:
    from mycosoft_mas.agents.base_agent import BaseAgent
except Exception:
    BaseAgent = object  # type: ignore[misc, assignment]

logger = logging.getLogger(__name__)


class ReflectionAgent(BaseAgent if BaseAgent is not object else object):  # type: ignore[misc]
    """Agent wrapper for ReflectionService - outcome logging and learning tasks."""

    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        if BaseAgent is not object:
            super().__init__(agent_id=agent_id, name=name, config=config or {})
        else:
            self.agent_id = agent_id
            self.name = name
            self.config = config or {}
        self.capabilities = ["log_response", "analyze_outcome", "create_learning_task"]

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        task_type = task.get("type", "")
        if task_type == "log_response":
            return await self._log_response(task)
        if task_type == "analyze_outcome":
            return await self._analyze_outcome(task)
        if task_type == "create_learning_task":
            return await self._create_learning_task(task)
        return {"status": "skipped", "result": {"reason": f"unknown task type: {task_type}"}}

    async def _log_response(self, task: Dict[str, Any]) -> Dict[str, Any]:
        try:
            from mycosoft_mas.engines.reflection import ReflectionService

            ep_id = task.get("ep_id", "")
            response = task.get("response", "")
            session_id = task.get("session_id", "")
            svc = ReflectionService()
            log_id = await svc.log_response(ep_id, response, session_id)
            return {"status": "success", "result": {"log_id": log_id}}
        except Exception as e:
            logger.warning("ReflectionAgent log_response failed: %s", e)
            return {"status": "error", "result": {"error": str(e)}}

    async def _analyze_outcome(self, task: Dict[str, Any]) -> Dict[str, Any]:
        try:
            from mycosoft_mas.engines.reflection import ReflectionService

            prediction = task.get("prediction", "")
            actual = task.get("actual", "")
            svc = ReflectionService()
            result = await svc.compare_outcome(prediction, actual)
            return {"status": "success", "result": result}
        except Exception as e:
            logger.warning("ReflectionAgent analyze_outcome failed: %s", e)
            return {"status": "error", "result": {"error": str(e)}}

    async def _create_learning_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        try:
            from mycosoft_mas.engines.reflection import ReflectionService

            gap = task.get("gap", "") or task.get("description", "")
            svc = ReflectionService()
            task_id = await svc.create_learning_task(gap)
            return {"status": "success", "result": {"task_id": task_id}}
        except Exception as e:
            logger.warning("ReflectionAgent create_learning_task failed: %s", e)
            return {"status": "error", "result": {"error": str(e)}}
