"""
Asana Integration Client.

Task and project management. Used by: SecretaryAgent, ProjectManagerAgent,
n8n workflows, and MYCA for task sync.

Environment Variables:
    ASANA_API_KEY: Personal access token from Asana (My Settings > Apps > Personal access tokens)
    ASANA_WORKSPACE_ID: Default workspace GID (optional)
"""

import os
import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

ASANA_API_BASE = "https://app.asana.com/api/1.0"


class AsanaClient:
    """Client for Asana REST API."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.api_key = self.config.get("api_key", os.getenv("ASANA_API_KEY", ""))
        self.workspace_id = self.config.get("workspace_id", os.getenv("ASANA_WORKSPACE_ID", ""))
        self.timeout = self.config.get("timeout", 30)
        self._client: Optional[httpx.AsyncClient] = None

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=ASANA_API_BASE,
                headers=self._headers(),
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def list_tasks(
        self,
        project_gid: Optional[str] = None,
        workspace_gid: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """List tasks (optionally in a project or workspace)."""
        if not self.api_key:
            logger.warning("Asana client: no ASANA_API_KEY set")
            return []
        client = await self._get_client()
        params: Dict[str, Any] = {"limit": limit}
        if project_gid:
            params["project"] = project_gid
        elif workspace_gid or self.workspace_id:
            params["workspace"] = workspace_gid or self.workspace_id
        try:
            r = await client.get("/tasks", params=params)
            r.raise_for_status()
            data = r.json()
            return data.get("data", [])
        except Exception as e:
            logger.warning("Asana list_tasks failed: %s", e)
            return []

    async def create_task(
        self,
        name: str,
        workspace_gid: Optional[str] = None,
        project_gid: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a task in Asana."""
        if not self.api_key:
            return None
        client = await self._get_client()
        body: Dict[str, Any] = {"name": name}
        if notes:
            body["notes"] = notes
        if workspace_gid or self.workspace_id:
            body["workspace"] = workspace_gid or self.workspace_id
        if project_gid:
            body["projects"] = [project_gid]
        try:
            r = await client.post("/tasks", json={"data": body})
            r.raise_for_status()
            return r.json().get("data")
        except Exception as e:
            logger.warning("Asana create_task failed: %s", e)
            return None

    async def get_workspaces(self) -> List[Dict[str, Any]]:
        """List workspaces available to the token."""
        if not self.api_key:
            return []
        client = await self._get_client()
        try:
            r = await client.get("/workspaces")
            r.raise_for_status()
            return r.json().get("data", [])
        except Exception as e:
            logger.warning("Asana get_workspaces failed: %s", e)
            return []
