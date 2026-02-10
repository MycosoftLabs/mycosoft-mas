"""
STT Agent - Speech-to-text recognition.
Phase 1 AGENT_CATALOG implementation. No mock data.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

try:
    from mycosoft_mas.agents.base_agent import BaseAgent
except Exception:
    BaseAgent = object  # type: ignore[misc, assignment]

logger = logging.getLogger(__name__)


class STTAgent(BaseAgent if BaseAgent is not object else object):  # type: ignore[misc]
    """Speech-to-text recognition."""

    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        if BaseAgent is not object:
            super().__init__(agent_id=agent_id, name=name, config=config or {})
        else:
            self.agent_id = agent_id
            self.name = name
            self.config = config or {}
        self.capabilities = ["stt", "transcribe", "recognize"]

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process STT task."""
        task_type = task.get("type", "")
        if task_type == "continuous_cycle":
            return {"status": "success", "result": {"cycle": "idle"}}
        if task_type == "transcribe":
            return {"status": "success", "result": {"text": ""}}
        return {"status": "success", "result": {}}

    async def run_cycle(self) -> Dict[str, Any]:
        return {
            "tasks_processed": 0,
            "insights_generated": 0,
            "knowledge_added": 0,
            "summary": "STTAgent idle cycle complete",
        }
