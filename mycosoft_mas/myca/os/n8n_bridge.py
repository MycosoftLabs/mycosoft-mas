"""
n8n Bridge — Connects MYCA OS to n8n workflow automation.

Primary n8n: MAS VM 192.168.0.188:5678
Secondary: MYCA local 127.0.0.1:5679 (VM 191)

API: n8n REST API v1 with X-N8N-API-KEY auth
- list_workflows() — GET /api/v1/workflows
- trigger_workflow(name, data) — find workflow, activate if needed, POST to webhook
- get_workflow_status(execution_id) — GET /api/v1/executions/{id}
- create_workflow(definition) — POST /api/v1/workflows

Date: 2026-03-05
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger("myca.os.n8n")


class N8NBridge:
    """Bridge to n8n workflow automation."""

    def __init__(self, os_ref: Any):
        self._os = os_ref
        self._session: Optional[aiohttp.ClientSession] = None
        self._base_url = (
            os.getenv("MYCA_N8N_URL") or os.getenv("N8N_URL") or "http://192.168.0.188:5678"
        ).rstrip("/")
        self._api_key = os.getenv("MYCA_N8N_API_KEY", "")

        # Static workflow name → webhook path (from known workflows)
        self._webhook_paths: Dict[str, str] = {
            "MYCA Ethics Evaluation": "myca/ethics/evaluate-recommendation",
            "MYCA Proactive Monitor": "myca/monitor/check",
            "MYCA Intent Orchestrator": "myca/intent/orchestrator",
        }

    def _headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self._api_key:
            h["X-N8N-API-KEY"] = self._api_key
        return h

    async def initialize(self) -> None:
        """Create aiohttp session."""
        self._session = aiohttp.ClientSession()
        logger.info("N8NBridge initialized (n8n at %s)", self._base_url)

    async def cleanup(self) -> None:
        """Close aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def health_check(self) -> Dict[str, Any]:
        """Check if n8n is reachable."""
        if not self._session:
            await self.initialize()
        try:
            async with self._session.get(
                f"{self._base_url}/healthz",
                headers=self._headers(),
                timeout=aiohttp.ClientTimeout(total=5),
            ) as r:
                ok = r.status == 200
                return {"healthy": ok, "status": r.status}
        except Exception as e:
            logger.debug("n8n health check failed: %s", e)
            return {"healthy": False, "error": str(e)}

    def _get_webhook_path_from_nodes(self, nodes: List[dict]) -> Optional[str]:
        """Extract webhook path from workflow nodes."""
        for node in nodes or []:
            if node.get("type") == "n8n-nodes-base.webhook":
                params = node.get("parameters", {})
                path = params.get("path") or params.get("webhookPath")
                if path:
                    return path
        return None

    async def list_workflows(self) -> List[Dict[str, Any]]:
        """List all workflows. Returns list of {id, name, active, ...}."""
        if not self._session:
            await self.initialize()
        try:
            async with self._session.get(
                f"{self._base_url}/api/v1/workflows",
                headers=self._headers(),
                timeout=aiohttp.ClientTimeout(total=15),
            ) as r:
                if r.status != 200:
                    body = await r.text()
                    logger.warning("n8n list_workflows failed: %s %s", r.status, body[:200])
                    return []
                data = await r.json()
                workflows = data.get("data", [])
                return [
                    {
                        "id": w.get("id"),
                        "name": w.get("name"),
                        "active": w.get("active", False),
                        "createdAt": w.get("createdAt"),
                    }
                    for w in workflows
                ]
        except Exception as e:
            logger.warning("N8NBridge list_workflows failed: %s", e)
            return []

    async def trigger_workflow(
        self,
        name: str,
        data: Optional[Dict[str, Any]] = None,
        *,
        webhook_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Trigger an n8n workflow by name.
        Resolves webhook path, activates workflow if needed, POSTs to webhook.
        Returns {status, summary, workflow_id?, execution_id?, response?}.
        """
        if not self._session:
            await self.initialize()
        if not self._api_key:
            return {"status": "failed", "error": "MYCA_N8N_API_KEY not configured"}

        payload = data if isinstance(data, dict) else {}
        path = webhook_path

        try:
            if path:
                wf_id = None
            else:
                workflows = await self.list_workflows()
                wf = next((w for w in workflows if w.get("name") == name), None)
                if not wf:
                    return {"status": "failed", "error": f"Workflow '{name}' not found"}
                wf_id = wf.get("id")

                path = self._webhook_paths.get(name)
                if not path and wf_id:
                    async with self._session.get(
                        f"{self._base_url}/api/v1/workflows/{wf_id}",
                        headers=self._headers(),
                    ) as wf_resp:
                        if wf_resp.status != 200:
                            return {
                                "status": "failed",
                                "error": f"Failed to fetch workflow: {wf_resp.status}",
                            }
                        wf_detail = await wf_resp.json()
                        nodes = wf_detail.get("data", {}).get("nodes", [])
                    path = self._get_webhook_path_from_nodes(nodes)

                if not path:
                    if wf_id:
                        async with self._session.post(
                            f"{self._base_url}/api/v1/workflows/{wf_id}/activate",
                            headers=self._headers(),
                        ):
                            pass
                    return {
                        "status": "completed",
                        "summary": f"Activated workflow '{name}' (no webhook)",
                        "workflow_id": wf_id,
                    }

                if wf_id:
                    async with self._session.post(
                        f"{self._base_url}/api/v1/workflows/{wf_id}/activate",
                        headers=self._headers(),
                    ):
                        pass

            webhook_url = f"{self._base_url}/webhook/{path.lstrip('/')}"
            async with self._session.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=60),
            ) as web_resp:
                body = await web_resp.text()
                try:
                    result = json.loads(body) if body else {}
                except json.JSONDecodeError:
                    result = {"raw": body[:1000]}

            out: Dict[str, Any] = {
                "status": "completed",
                "summary": f"Executed workflow via webhook: {path}",
                "webhook_path": path,
                "response": result,
            }
            if wf_id is not None:
                out["workflow_id"] = wf_id
            return out
        except aiohttp.ClientError as e:
            return {"status": "failed", "error": f"n8n request failed: {e}"}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def get_workflow_status(self, execution_id: str) -> Dict[str, Any]:
        """Get execution status by ID. Returns {id, status, workflowId, startedAt, stoppedAt, ...}."""
        if not self._session:
            await self.initialize()
        try:
            async with self._session.get(
                f"{self._base_url}/api/v1/executions/{execution_id}",
                headers=self._headers(),
                timeout=aiohttp.ClientTimeout(total=10),
            ) as r:
                if r.status == 404:
                    return {"status": "failed", "error": "Execution not found"}
                if r.status != 200:
                    body = await r.text()
                    return {"status": "failed", "error": f"n8n error {r.status}: {body[:200]}"}
                data = await r.json()
                exec_data = data.get("data", data)
                return {
                    "id": exec_data.get("id"),
                    "status": exec_data.get("status"),
                    "workflowId": exec_data.get("workflowId"),
                    "startedAt": exec_data.get("startedAt"),
                    "stoppedAt": exec_data.get("stoppedAt"),
                    "executionTime": exec_data.get("executionTime"),
                }
        except Exception as e:
            logger.warning("N8NBridge get_workflow_status failed: %s", e)
            return {"status": "failed", "error": str(e)}

    async def create_workflow(self, definition: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new workflow. definition is the n8n workflow JSON."""
        if not self._session:
            await self.initialize()
        try:
            async with self._session.post(
                f"{self._base_url}/api/v1/workflows",
                headers=self._headers(),
                json=definition,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as r:
                body = (
                    await r.json()
                    if r.headers.get("content-type", "").startswith("application/json")
                    else {}
                )
                if r.status not in (200, 201):
                    return {
                        "status": "failed",
                        "error": f"n8n create failed: {r.status}",
                        "detail": body,
                    }
                wf = body.get("data", body)
                return {
                    "status": "created",
                    "workflow_id": wf.get("id"),
                    "name": wf.get("name"),
                }
        except Exception as e:
            logger.warning("N8NBridge create_workflow failed: %s", e)
            return {"status": "failed", "error": str(e)}
