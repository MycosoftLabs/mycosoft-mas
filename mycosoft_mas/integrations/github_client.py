"""
GitHub Integration Client.

Programmatic access to repos, issues, PRs, CI/CD, releases.
Used by DevOps, code automation, and MAS agents.

Environment Variables:
    GITHUB_TOKEN: Personal access token or fine-grained token
    GITHUB_OWNER: Default org/owner (optional)
"""

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"


class GitHubClient:
    """Client for GitHub REST API."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.token = self.config.get("token", os.environ.get("GITHUB_TOKEN", ""))
        self.owner = self.config.get("owner", os.environ.get("GITHUB_OWNER", ""))
        self.timeout = self.config.get("timeout", 30)
        self._client: Optional[httpx.AsyncClient] = None

    def _headers(self) -> Dict[str, str]:
        h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=GITHUB_API_BASE,
                headers=self._headers(),
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def list_repos(
        self, owner: Optional[str] = None, type_: str = "all", limit: int = 30,
    ) -> List[Dict[str, Any]]:
        """List repositories for owner (org or user)."""
        owner = owner or self.owner
        if not owner:
            return []
        client = await self._get_client()
        try:
            r = await client.get(f"/orgs/{owner}/repos", params={"type": type_, "per_page": min(limit, 100)})
            if r.is_success:
                return r.json()
            r = await client.get(f"/users/{owner}/repos", params={"type": type_, "per_page": min(limit, 100)})
            if r.is_success:
                return r.json()
            return []
        except Exception as e:
            logger.warning("GitHub list_repos failed: %s", e)
            return []

    async def create_repo(
        self,
        name: str,
        owner: Optional[str] = None,
        private: bool = False,
        description: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a repository."""
        owner = owner or self.owner
        if not owner or not self.token:
            return None
        client = await self._get_client()
        try:
            path = f"/orgs/{owner}/repos" if owner else "/user/repos"
            body = {"name": name, "private": private}
            if description:
                body["description"] = description
            r = await client.post(path, json=body)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.warning("GitHub create_repo failed: %s", e)
            return None

    async def list_issues(
        self, owner: str, repo: str, state: str = "open", limit: int = 30,
    ) -> List[Dict[str, Any]]:
        """List issues in a repo."""
        client = await self._get_client()
        try:
            r = await client.get(
                f"/repos/{owner}/{repo}/issues",
                params={"state": state, "per_page": min(limit, 100)},
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.warning("GitHub list_issues failed: %s", e)
            return []

    async def create_issue(
        self, owner: str, repo: str, title: str, body: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create an issue."""
        if not self.token:
            return None
        client = await self._get_client()
        try:
            r = await client.post(
                f"/repos/{owner}/{repo}/issues",
                json={"title": title, "body": body or ""},
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.warning("GitHub create_issue failed: %s", e)
            return None

    async def list_pull_requests(
        self, owner: str, repo: str, state: str = "open", limit: int = 30,
    ) -> List[Dict[str, Any]]:
        """List pull requests."""
        client = await self._get_client()
        try:
            r = await client.get(
                f"/repos/{owner}/{repo}/pulls",
                params={"state": state, "per_page": min(limit, 100)},
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.warning("GitHub list_pull_requests failed: %s", e)
            return []

    async def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str = "main",
        body: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a pull request."""
        if not self.token:
            return None
        client = await self._get_client()
        try:
            r = await client.post(
                f"/repos/{owner}/{repo}/pulls",
                json={"title": title, "head": head, "base": base, "body": body or ""},
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.warning("GitHub create_pull_request failed: %s", e)
            return None

    async def search_code(self, query: str, limit: int = 30) -> List[Dict[str, Any]]:
        """Search code across GitHub."""
        client = await self._get_client()
        try:
            r = await client.get(
                "/search/code",
                params={"q": query, "per_page": min(limit, 100)},
            )
            r.raise_for_status()
            return r.json().get("items", [])
        except Exception as e:
            logger.warning("GitHub search_code failed: %s", e)
            return []

    async def list_workflow_runs(
        self, owner: str, repo: str, limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """List workflow runs (CI/CD)."""
        if not self.token:
            return []
        client = await self._get_client()
        try:
            r = await client.get(
                f"/repos/{owner}/{repo}/actions/runs",
                params={"per_page": min(limit, 100)},
            )
            r.raise_for_status()
            return r.json().get("workflow_runs", [])
        except Exception as e:
            logger.warning("GitHub list_workflow_runs failed: %s", e)
            return []

    async def trigger_workflow(
        self, owner: str, repo: str, workflow_id: str, ref: str = "main",
    ) -> Optional[Dict[str, Any]]:
        """Trigger a workflow dispatch."""
        if not self.token:
            return None
        client = await self._get_client()
        try:
            r = await client.post(
                f"/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches",
                json={"ref": ref},
            )
            if r.status_code in (200, 204):
                return {"status": "dispatched"}
            return None
        except Exception as e:
            logger.warning("GitHub trigger_workflow failed: %s", e)
            return None

    async def list_releases(self, owner: str, repo: str, limit: int = 10) -> List[Dict[str, Any]]:
        """List releases."""
        client = await self._get_client()
        try:
            r = await client.get(
                f"/repos/{owner}/{repo}/releases",
                params={"per_page": min(limit, 100)},
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.warning("GitHub list_releases failed: %s", e)
            return []

    async def health_check(self) -> Dict[str, Any]:
        """Verify connectivity to GitHub API."""
        if not self.token:
            return {"status": "unconfigured", "error": "Missing GITHUB_TOKEN"}
        try:
            client = await self._get_client()
            r = await client.get("/user")
            if r.is_success:
                return {"status": "healthy"}
            return {"status": "unhealthy", "error": r.text[:200]}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
