"""
N8N Workflow Agent - n8n workflow execution and management.
Uses N8NWorkflowEngine for CRUD/sync and N8NClient for async trigger/execute.
No mock data.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

try:
    from mycosoft_mas.agents.base_agent import BaseAgent
except Exception:
    BaseAgent = object  # type: ignore[misc, assignment]

logger = logging.getLogger(__name__)


def _get_engine():
    """Create N8NWorkflowEngine for cloud/production n8n (sync)."""
    from mycosoft_mas.core.n8n_workflow_engine import N8NWorkflowEngine

    base_url = os.getenv("N8N_URL", "http://192.168.0.188:5678")
    api_key = os.getenv("N8N_API_KEY", "")
    return N8NWorkflowEngine(base_url=base_url, api_key=api_key)


def _get_n8n_client():
    """Create async N8NClient for triggering workflows."""
    from mycosoft_mas.integrations.n8n_client import N8NClient

    return N8NClient()


class N8NWorkflowAgent(BaseAgent if BaseAgent is not object else object):  # type: ignore[misc]
    """n8n workflow execution and management; real n8n API integration."""

    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        if BaseAgent is not object:
            super().__init__(agent_id=agent_id, name=name, config=config or {})
        else:
            self.agent_id = agent_id
            self.name = name
            self.config = config or {}
        self.capabilities = ["workflow", "execute", "trigger", "list", "activate", "deactivate", "sync"]

    def _engine(self):
        return _get_engine()

    async def _run_sync(self, fn, *args, **kwargs):
        """Run sync engine method in thread pool."""
        return await asyncio.to_thread(fn, *args, **kwargs)

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process workflow task; calls real n8n API."""
        task_type = task.get("type", "")
        try:
            if task_type == "continuous_cycle":
                return {"status": "success", "result": {"cycle": "idle"}}

            if task_type == "execute_workflow" or task_type == "trigger_workflow":
                workflow_name = task.get("workflow_name") or task.get("workflow_id")
                parameters = task.get("parameters") or task.get("data") or {}
                if not workflow_name:
                    return {"status": "error", "result": {"error": "workflow_name or workflow_id required"}}
                engine = self._engine()
                wf = await self._run_sync(engine.get_workflow_by_name, str(workflow_name))
                if not wf:
                    # Try by id
                    try:
                        wf = await self._run_sync(engine.get_workflow, str(workflow_name))
                    except Exception:
                        wf = None
                if not wf:
                    return {"status": "error", "result": {"error": f"Workflow not found: {workflow_name}"}}
                workflow_id = wf.get("id")
                client = _get_n8n_client()
                result = await client.execute_workflow(workflow_id, data=parameters)
                return {"status": "success", "result": {"workflow_id": workflow_id, "triggered": True, "response": result}}

            if task_type == "list_workflows":
                engine = self._engine()
                active_only = task.get("active_only", False)
                category = task.get("category")
                if category:
                    from mycosoft_mas.core.n8n_workflow_engine import WorkflowCategory
                    cat_enum = getattr(WorkflowCategory, str(category).upper(), None) or WorkflowCategory.CUSTOM
                else:
                    cat_enum = None
                workflows = await self._run_sync(engine.list_workflows, active_only=active_only, category=cat_enum)
                return {
                    "status": "success",
                    "result": {"workflows": [w.to_dict() for w in workflows], "count": len(workflows)},
                }

            if task_type == "get_workflow":
                workflow_id = task.get("workflow_id") or task.get("workflow_name")
                if not workflow_id:
                    return {"status": "error", "result": {"error": "workflow_id or workflow_name required"}}
                engine = self._engine()
                wf = await self._run_sync(engine.get_workflow_by_name, str(workflow_id))
                if not wf:
                    try:
                        wf = await self._run_sync(engine.get_workflow, str(workflow_id))
                    except Exception:
                        wf = None
                if not wf:
                    return {"status": "error", "result": {"error": f"Workflow not found: {workflow_id}"}}
                return {"status": "success", "result": {"workflow": wf}}

            if task_type == "activate":
                workflow_id = task.get("workflow_id")
                if not workflow_id:
                    return {"status": "error", "result": {"error": "workflow_id required"}}
                engine = self._engine()
                out = await self._run_sync(engine.activate_workflow, workflow_id)
                return {"status": "success", "result": {"workflow_id": workflow_id, "activated": True, "response": out}}

            if task_type == "deactivate":
                workflow_id = task.get("workflow_id")
                if not workflow_id:
                    return {"status": "error", "result": {"error": "workflow_id required"}}
                engine = self._engine()
                out = await self._run_sync(engine.deactivate_workflow, workflow_id)
                return {"status": "success", "result": {"workflow_id": workflow_id, "deactivated": True, "response": out}}

            if task_type == "sync_all":
                engine = self._engine()
                activate_core = task.get("activate_core", True)
                sync_result = await self._run_sync(engine.sync_all_local_workflows, activate_core=activate_core)
                return {
                    "status": "success",
                    "result": {
                        "imported": sync_result.imported,
                        "skipped": sync_result.skipped,
                        "activated": sync_result.activated,
                        "errors": sync_result.errors,
                        "timestamp": sync_result.timestamp,
                    },
                }

            return {"status": "error", "result": {"error": f"Unknown task type: {task_type}"}}
        except Exception as e:
            logger.exception("N8NWorkflowAgent process_task failed")
            return {"status": "error", "result": {"error": str(e)}}

    async def run_cycle(self) -> Dict[str, Any]:
        """Single cycle for 24/7 runner."""
        return {
            "tasks_processed": 0,
            "insights_generated": 0,
            "knowledge_added": 0,
            "summary": "N8NWorkflowAgent idle cycle complete",
        }
