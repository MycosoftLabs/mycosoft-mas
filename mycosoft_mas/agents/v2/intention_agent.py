"""
Intention Agent - Wraps IntentionService for agent-based invocation.
Capabilities: decompose_intent, plan_candidates.
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


class IntentionAgent(BaseAgent if BaseAgent is not object else object):  # type: ignore[misc]
    """Agent wrapper for IntentionService - intent decomposition and plan candidates."""

    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        if BaseAgent is not object:
            super().__init__(agent_id=agent_id, name=name, config=config or {})
        else:
            self.agent_id = agent_id
            self.name = name
            self.config = config or {}
        self.capabilities = ["decompose_intent", "plan_candidates"]

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        task_type = task.get("type", "")
        if task_type == "decompose_intent":
            return await self._decompose(task)
        if task_type == "plan_candidates":
            return await self._plan_candidates(task)
        return {"status": "skipped", "result": {"reason": f"unknown task type: {task_type}"}}

    async def _decompose(self, task: Dict[str, Any]) -> Dict[str, Any]:
        try:
            from mycosoft_mas.engines.intention import IntentionService

            directive = task.get("directive", "") or task.get("content", "")
            svc = IntentionService()
            intent_graph = await svc.decompose(directive)
            out = getattr(intent_graph, "__dict__", None) or {}
            if hasattr(intent_graph, "goals"):
                out["goals"] = intent_graph.goals
            if hasattr(intent_graph, "constraints"):
                out["constraints"] = intent_graph.constraints
            return {"status": "success", "result": out}
        except Exception as e:
            logger.warning("IntentionAgent decompose failed: %s", e)
            return {"status": "error", "result": {"error": str(e)}}

    async def _plan_candidates(self, task: Dict[str, Any]) -> Dict[str, Any]:
        try:
            from mycosoft_mas.engines.intention import IntentionService

            intent_graph = task.get("intent_graph") or task.get("intent")
            if not intent_graph:
                directive = task.get("directive", "") or task.get("content", "")
                svc = IntentionService()
                intent_graph = await svc.decompose(directive)
            else:
                svc = IntentionService()
            candidates = await svc.get_plan_candidates(intent_graph)
            out = [
                {"plan": getattr(c, "plan", c), "score": getattr(c, "score", 1.0)}
                for c in (candidates or [])
            ]
            return {"status": "success", "result": {"candidates": out}}
        except Exception as e:
            logger.warning("IntentionAgent plan_candidates failed: %s", e)
            return {"status": "error", "result": {"error": str(e)}}
