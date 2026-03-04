"""
MAS Bridge — Connection to the Multi-Agent System on VM 188.

Provides MYCA OS with:
- Orchestrator API access (158+ agents)
- Agent dispatch (send tasks to specialist agents)
- MAS n8n workflow triggering (66 workflows on 188:5678)
- System health monitoring across the MAS
- Agent status and metrics queries

Date: 2026-03-04
"""

import os
import logging
from typing import Optional

import aiohttp

logger = logging.getLogger("myca.os.mas_bridge")


class MASBridge:
    """Bridge to the MAS orchestrator on VM 188."""

    def __init__(self, os_ref):
        self._os = os_ref
        self._session: Optional[aiohttp.ClientSession] = None
        self._orchestrator_url = os.getenv("MAS_API_URL", "http://192.168.0.188:8001")
        self._mas_n8n_url = os.getenv("MAS_N8N_URL", "http://192.168.0.188:5678")
        self._mas_n8n_key = os.getenv("MAS_N8N_API_KEY", "")

    async def initialize(self):
        self._session = aiohttp.ClientSession()
        health = await self.health_check()
        if health.get("healthy"):
            logger.info(f"MAS Bridge connected to {self._orchestrator_url}")
        else:
            logger.warning(f"MAS orchestrator not reachable at {self._orchestrator_url}")

    async def cleanup(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def health_check(self) -> dict:
        """Check MAS orchestrator health."""
        try:
            async with self._session.get(
                f"{self._orchestrator_url}/health",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {"healthy": True, "data": data}
        except Exception as e:
            logger.debug(f"MAS health check failed: {e}")
        return {"healthy": False}

    async def dispatch_task(self, agent_id: str, task: dict) -> dict:
        """Dispatch a task to a specific MAS agent."""
        try:
            payload = {
                "agent_id": agent_id,
                "task": {
                    "type": task.get("type", "general"),
                    "description": task.get("description", task.get("content", "")),
                    "priority": task.get("priority", "medium"),
                    "parameters": task.get("parameters", {}),
                },
            }
            async with self._session.post(
                f"{self._orchestrator_url}/api/agents/{agent_id}/tasks",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status in (200, 201):
                    return await resp.json()
                return {"status": "failed", "error": f"HTTP {resp.status}"}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def dispatch_to_specialist(self, task: dict) -> dict:
        """Route a task to the best specialist agent based on type."""
        task_type = task.get("type", "general")

        # Agent routing table
        routing = {
            "coding": "coding_agent",
            "research": "research_agent",
            "deployment": "deployment_agent",
            "security": "security_agent",
            "financial": "financial_agent",
            "scientific": "lab_agent",
            "mycology": "mycology_bio_agent",
            "earth2": "earth2_orchestrator",
            "integration": "n8n_workflow_agent",
            "data": "mindex_agent",
        }

        agent_id = routing.get(task_type, "coding_agent")
        return await self.dispatch_task(agent_id, task)

    async def list_agents(self) -> list:
        """List all registered MAS agents."""
        try:
            async with self._session.get(
                f"{self._orchestrator_url}/api/registry/agents",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("agents", [])
        except Exception:
            pass
        return []

    async def get_agent_status(self, agent_id: str) -> dict:
        """Get status of a specific agent."""
        try:
            async with self._session.get(
                f"{self._orchestrator_url}/api/agents/{agent_id}/status",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception:
            pass
        return {"status": "unknown"}

    async def trigger_mas_workflow(self, workflow_name: str, data: dict = None) -> dict:
        """Trigger a workflow on MAS n8n (188:5678)."""
        if not self._mas_n8n_key:
            return {"status": "failed", "error": "MAS n8n API key not configured"}

        headers = {"X-N8N-API-KEY": self._mas_n8n_key}
        try:
            async with self._session.get(
                f"{self._mas_n8n_url}/api/v1/workflows",
                headers=headers,
            ) as resp:
                workflows = (await resp.json()).get("data", [])
                wf = next((w for w in workflows if w["name"] == workflow_name), None)

            if wf:
                return {"status": "triggered", "workflow": workflow_name, "id": wf["id"]}
            return {"status": "failed", "error": f"Workflow not found: {workflow_name}"}
        except Exception as e:
            return {"status": "failed", "error": str(e)}
