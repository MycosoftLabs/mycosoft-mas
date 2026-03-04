"""
Weights & Biases Client

Provides access to W&B services via REST API:
- Experiment tracking (runs, metrics, logs)
- Model versioning (artifacts)
- Sweep orchestration (hyperparameter search)
- Reports and dashboards

Env vars:
    WANDB_API_KEY   -- W&B API key
    WANDB_ENTITY    -- W&B entity (user or team)
"""

import os
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

WANDB_BASE = "https://api.wandb.ai"
WANDB_GQL = f"{WANDB_BASE}/graphql"


class WandbClient:
    """Client for Weights & Biases REST/GraphQL API."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.api_key = self.config.get("wandb_api_key") or os.getenv("WANDB_API_KEY", "")
        self.entity = self.config.get("wandb_entity") or os.getenv("WANDB_ENTITY", "mycosoft")
        self.timeout = self.config.get("timeout", 30)
        self._client: Optional[httpx.AsyncClient] = None

    async def _http(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def health_check(self) -> Dict[str, Any]:
        try:
            projects = await self.list_projects()
            return {
                "status": "ok",
                "entity": self.entity,
                "project_count": len(projects),
                "ts": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _gql(self, query: str, variables: Optional[Dict] = None) -> Dict[str, Any]:
        c = await self._http()
        r = await c.post(
            WANDB_GQL,
            headers=self._headers(),
            json={"query": query, "variables": variables or {}},
        )
        r.raise_for_status()
        return r.json()

    async def list_projects(self) -> List[Dict[str, Any]]:
        query = """
        query($entity: String!) {
            entity(name: $entity) {
                projects(first: 50) {
                    edges { node { name description createdAt } }
                }
            }
        }
        """
        data = await self._gql(query, {"entity": self.entity})
        edges = data.get("data", {}).get("entity", {}).get("projects", {}).get("edges", [])
        return [e["node"] for e in edges]

    async def list_runs(self, project: str, limit: int = 20) -> List[Dict[str, Any]]:
        query = """
        query($entity: String!, $project: String!, $limit: Int!) {
            project(name: $project, entityName: $entity) {
                runs(first: $limit, order: "-createdAt") {
                    edges { node { name displayName state createdAt summaryMetrics } }
                }
            }
        }
        """
        data = await self._gql(query, {"entity": self.entity, "project": project, "limit": limit})
        edges = data.get("data", {}).get("project", {}).get("runs", {}).get("edges", [])
        return [e["node"] for e in edges]

    async def get_run(self, project: str, run_id: str) -> Dict[str, Any]:
        query = """
        query($entity: String!, $project: String!, $runName: String!) {
            project(name: $project, entityName: $entity) {
                run(name: $runName) {
                    name displayName state config summaryMetrics createdAt heartbeatAt
                }
            }
        }
        """
        data = await self._gql(query, {"entity": self.entity, "project": project, "runName": run_id})
        return data.get("data", {}).get("project", {}).get("run", {})

    async def list_artifacts(self, project: str, artifact_type: str = "model") -> List[Dict[str, Any]]:
        query = """
        query($entity: String!, $project: String!, $type: String!) {
            project(name: $project, entityName: $entity) {
                artifactType(name: $type) {
                    artifactCollections(first: 50) {
                        edges { node { name description createdAt } }
                    }
                }
            }
        }
        """
        data = await self._gql(query, {"entity": self.entity, "project": project, "type": artifact_type})
        at = data.get("data", {}).get("project", {}).get("artifactType", {})
        edges = at.get("artifactCollections", {}).get("edges", []) if at else []
        return [e["node"] for e in edges]

    async def list_sweeps(self, project: str) -> List[Dict[str, Any]]:
        query = """
        query($entity: String!, $project: String!) {
            project(name: $project, entityName: $entity) {
                sweeps(first: 20) {
                    edges { node { name displayName state bestLoss runCount config } }
                }
            }
        }
        """
        data = await self._gql(query, {"entity": self.entity, "project": project})
        edges = data.get("data", {}).get("project", {}).get("sweeps", {}).get("edges", [])
        return [e["node"] for e in edges]

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
