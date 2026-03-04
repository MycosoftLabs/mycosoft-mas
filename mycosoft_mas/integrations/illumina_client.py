"""
Illumina BaseSpace Sequence Hub Integration Client.

DNA sequencing run monitoring, sample management, FASTQ download.
BaseSpace API v1pre3.

Environment Variables:
    ILLUMINA_ACCESS_TOKEN: OAuth2 access token (obtain via BaseSpace OAuth flow)
    ILLUMINA_CLIENT_ID: OAuth2 client ID (optional, for token refresh)
    ILLUMINA_CLIENT_SECRET: OAuth2 client secret (optional)
"""

import os
import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

ILLUMINA_BASE_URL = "https://api.basespace.illumina.com/v1pre3"


class IlluminaClient:
    """Client for Illumina BaseSpace Sequence Hub REST API."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.access_token = self.config.get(
            "access_token", os.getenv("ILLUMINA_ACCESS_TOKEN", "")
        )
        self.client_id = self.config.get("client_id", os.getenv("ILLUMINA_CLIENT_ID", ""))
        self.client_secret = self.config.get(
            "client_secret", os.getenv("ILLUMINA_CLIENT_SECRET", "")
        )
        self.timeout = self.config.get("timeout", 60)
        self._client: Optional[httpx.AsyncClient] = None

    def _headers(self) -> Dict[str, str]:
        return {
            "x-access-token": self.access_token,
            "Content-Type": "application/json",
        }

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=ILLUMINA_BASE_URL,
                headers=self._headers(),
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """GET request; returns Response dict or None on error."""
        if not self.access_token:
            logger.warning("Illumina client: no ILLUMINA_ACCESS_TOKEN set")
            return None
        client = await self._get_client()
        try:
            r = await client.get(path, params=params)
            r.raise_for_status()
            data = r.json()
            return data.get("Response", data)
        except httpx.HTTPStatusError as e:
            logger.warning("Illumina API error %s: %s", e.response.status_code, e)
            return None
        except Exception as e:
            logger.warning("Illumina API request failed: %s", e)
            return None

    async def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Get the authenticated user."""
        return await self._get("/users/current")

    async def list_projects(
        self,
        user_id: Optional[str] = None,
        offset: int = 0,
        limit: int = 100,
        sort_by: str = "Id",
        sort_dir: str = "Desc",
    ) -> Dict[str, Any]:
        """List projects for a user. If user_id is None, uses current user."""
        user = await self.get_current_user() if not user_id else {"Id": user_id}
        uid = user.get("Id") if isinstance(user, dict) else None
        if not uid:
            return {"Items": [], "TotalCount": 0, "DisplayedCount": 0}
        path = f"/users/{uid}/projects"
        params = {"Offset": offset, "Limit": limit, "SortBy": sort_by, "SortDir": sort_dir}
        resp = await self._get(path, params)
        if not resp:
            return {"Items": [], "TotalCount": 0, "DisplayedCount": 0}
        return resp

    async def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get project by ID."""
        return await self._get(f"/projects/{project_id}")

    async def list_runs(
        self,
        user_id: Optional[str] = None,
        statuses: Optional[str] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """List sequencing runs. statuses e.g. 'complete'."""
        user = await self.get_current_user() if not user_id else {"Id": user_id}
        uid = user.get("Id") if isinstance(user, dict) else None
        if not uid:
            return {"Items": [], "TotalCount": 0, "DisplayedCount": 0}
        path = f"/users/{uid}/runs"
        params: Dict[str, Any] = {"Offset": offset, "Limit": limit}
        if statuses:
            params["Statuses"] = statuses
        resp = await self._get(path, params)
        if not resp:
            return {"Items": [], "TotalCount": 0, "DisplayedCount": 0}
        return resp

    async def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get run by ID."""
        return await self._get(f"/runs/{run_id}")

    async def list_project_samples(
        self,
        project_id: str,
        offset: int = 0,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """List samples in a project."""
        path = f"/projects/{project_id}/samples"
        params = {"Offset": offset, "Limit": limit}
        resp = await self._get(path, params)
        if not resp:
            return {"Items": [], "TotalCount": 0, "DisplayedCount": 0}
        return resp

    async def list_run_samples(
        self,
        run_id: str,
        offset: int = 0,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """List samples in a run."""
        path = f"/runs/{run_id}/samples"
        params = {"Offset": offset, "Limit": limit}
        resp = await self._get(path, params)
        if not resp:
            return {"Items": [], "TotalCount": 0, "DisplayedCount": 0}
        return resp

    async def get_sample(self, sample_id: str) -> Optional[Dict[str, Any]]:
        """Get sample by ID."""
        return await self._get(f"/samples/{sample_id}")

    async def list_sample_files(
        self,
        sample_id: str,
        extensions: Optional[str] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """List files in a sample. Use extensions='gz' for FASTQ files."""
        path = f"/samples/{sample_id}/files"
        params: Dict[str, Any] = {"Offset": offset, "Limit": limit}
        if extensions:
            params["Extensions"] = extensions
        resp = await self._get(path, params)
        if not resp:
            return {"Items": [], "TotalCount": 0, "DisplayedCount": 0}
        return resp

    async def list_run_files(
        self,
        run_id: str,
        extensions: Optional[str] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """List files in a run."""
        path = f"/runs/{run_id}/files"
        params: Dict[str, Any] = {"Offset": offset, "Limit": limit}
        if extensions:
            params["Extensions"] = extensions
        resp = await self._get(path, params)
        if not resp:
            return {"Items": [], "TotalCount": 0, "DisplayedCount": 0}
        return resp

    async def get_file(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get file metadata including HrefContent for download."""
        return await self._get(f"/files/{file_id}")

    async def download_file(
        self,
        file_id: str,
        dest_path: Optional[str] = None,
    ) -> Optional[bytes]:
        """Download file content. Returns bytes or writes to dest_path if provided."""
        if not self.access_token:
            return None
        client = await self._get_client()
        try:
            r = await client.get(f"/files/{file_id}/content")
            r.raise_for_status()
            content = r.content
            if dest_path:
                with open(dest_path, "wb") as f:
                    f.write(content)
            return content
        except Exception as e:
            logger.warning("Illumina file download failed: %s", e)
            return None

    async def list_fastq_files(
        self,
        sample_id: str,
    ) -> List[Dict[str, Any]]:
        """List FASTQ (.gz) files for a sample."""
        resp = await self.list_sample_files(sample_id, extensions="gz", limit=1000)
        return resp.get("Items", [])

    async def health_check(self) -> Dict[str, Any]:
        """Check API connectivity and token validity."""
        ok = bool(self.access_token)
        user = None
        if ok:
            user = await self.get_current_user()
            ok = user is not None and isinstance(user, dict)
        return {
            "ok": ok,
            "has_token": bool(self.access_token),
            "user_id": user.get("Id") if user else None,
        }
