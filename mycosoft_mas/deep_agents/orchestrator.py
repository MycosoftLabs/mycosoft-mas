"""
Deep Agent orchestrator wrapper for MAS.

Feature-flagged and additive:
- Uses LangChain Deep Agents when available and enabled.
- Falls back to existing MAS subagent runner when unavailable.
"""

from __future__ import annotations

import asyncio
import importlib
import logging
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from mycosoft_mas.deep_agents.config import get_deep_agents_config
from mycosoft_mas.deep_agents.filesystem_bridge import build_multimodal_context
from mycosoft_mas.deep_agents.observability_middleware import (
    increment_task_counter,
    observe_task_duration,
)
from mycosoft_mas.deep_agents.permission_middleware import PermissionGate
from mycosoft_mas.deep_agents.redis_events import DeepAgentRedisEvents
from mycosoft_mas.deep_agents.status_mapper import DeepAgentTaskState
from mycosoft_mas.orchestration.langgraph.subagent_runner import SubagentRunner

logger = logging.getLogger(__name__)


@dataclass
class DeepAgentTaskRecord:
    task_id: str
    agent_name: str
    task: str
    state: DeepAgentTaskState = DeepAgentTaskState.PENDING
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "agent_name": self.agent_name,
            "task": self.task,
            "state": self.state.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "result": self.result,
            "error": self.error,
            "context": self.context,
        }


class DeepAgentOrchestrator:
    def __init__(self) -> None:
        self._config = get_deep_agents_config()
        self._deep_agent_runtime: Any = None
        self._runner = SubagentRunner()
        self._tasks: Dict[str, DeepAgentTaskRecord] = {}
        self._redis_events = DeepAgentRedisEvents()
        self._permission_gate = PermissionGate()
        self._lock = asyncio.Lock()
        self._initialized = False
        self._deepagents_available = False

    async def initialize(self) -> None:
        if self._initialized:
            return

        if self._config.redis_events_enabled:
            try:
                await self._redis_events.initialize()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Deep agent redis event stream unavailable: %s", exc)

        try:
            module = importlib.import_module("deepagents")
            self._deepagents_available = True
            create_deep_agent = getattr(module, "create_deep_agent", None)
            if self._config.enabled and callable(create_deep_agent):
                self._deep_agent_runtime = create_deep_agent(model=self._config.model, tools=[])
        except Exception:
            self._deepagents_available = False

        self._initialized = True

    async def shutdown(self) -> None:
        await self._redis_events.shutdown()

    def health(self) -> Dict[str, Any]:
        return {
            "enabled": self._config.enabled,
            "protocol_enabled": self._config.protocol_enabled,
            "deepagents_available": self._deepagents_available,
            "runtime_initialized": self._deep_agent_runtime is not None,
            "queued_tasks": len(self._tasks),
        }

    async def submit_task(
        self,
        agent_name: str,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> DeepAgentTaskRecord:
        await self.initialize()

        task_id = str(uuid4())
        merged_context = dict(context or {})
        if self._config.filesystem_enabled:
            merged_context["multimodal"] = build_multimodal_context()

        record = DeepAgentTaskRecord(
            task_id=task_id,
            agent_name=agent_name,
            task=task,
            context=merged_context,
        )
        async with self._lock:
            self._tasks[task_id] = record

        await self._publish("task_submitted", record)
        asyncio.create_task(self._run_task(record))
        return record

    async def get_task(self, task_id: str) -> Optional[DeepAgentTaskRecord]:
        async with self._lock:
            return self._tasks.get(task_id)

    async def _publish(self, event_type: str, record: DeepAgentTaskRecord) -> None:
        if not self._config.redis_events_enabled:
            return
        await self._redis_events.publish(event_type, record.to_dict())

    async def _run_task(self, record: DeepAgentTaskRecord) -> None:
        record.state = DeepAgentTaskState.RUNNING
        record.updated_at = datetime.now(timezone.utc).isoformat()
        await self._publish("task_started", record)
        increment_task_counter(record.agent_name, record.state.value)

        with observe_task_duration(record.agent_name):
            try:
                result = await asyncio.wait_for(
                    self._execute_with_runtime(record),
                    timeout=self._config.default_timeout_seconds,
                )
                record.result = result
                record.state = DeepAgentTaskState.SUCCEEDED
            except asyncio.TimeoutError:
                record.state = DeepAgentTaskState.FAILED
                record.error = "task timed out"
            except Exception as exc:  # noqa: BLE001
                record.state = DeepAgentTaskState.FAILED
                record.error = str(exc)
                logger.debug("Deep agent task failed: %s\n%s", exc, traceback.format_exc())

        record.updated_at = datetime.now(timezone.utc).isoformat()
        increment_task_counter(record.agent_name, record.state.value)
        await self._publish("task_finished", record)

    async def _execute_with_runtime(self, record: DeepAgentTaskRecord) -> Dict[str, Any]:
        permission = self._permission_gate.evaluate(record.agent_name, [])
        if not permission.allowed:
            return {"status": "denied", "reason": permission.reason}

        if self._deep_agent_runtime is not None:
            payload = {
                "input": record.task,
                "context": record.context,
                "agent_name": record.agent_name,
            }
            if hasattr(self._deep_agent_runtime, "ainvoke"):
                response = await self._deep_agent_runtime.ainvoke(payload)
            elif hasattr(self._deep_agent_runtime, "invoke"):
                response = await asyncio.to_thread(self._deep_agent_runtime.invoke, payload)
            else:
                response = {"output": "deep agent runtime available but unsupported invoke method"}
            return {"status": "ok", "runtime": "deepagents", "response": response}

        fallback = await self._runner.run_subagent(
            subagent_name=record.agent_name,
            task=record.task,
            context=record.context,
        )
        return {"status": "ok", "runtime": "fallback", "response": fallback.to_dict()}


_ORCHESTRATOR: DeepAgentOrchestrator | None = None


def get_deep_agent_orchestrator() -> DeepAgentOrchestrator:
    global _ORCHESTRATOR
    if _ORCHESTRATOR is None:
        _ORCHESTRATOR = DeepAgentOrchestrator()
    return _ORCHESTRATOR
