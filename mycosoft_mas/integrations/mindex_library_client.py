"""
MINDEX Library + SINE client for MAS agents, NLM training, and n8n workflows.

Talks to MINDEX VM (default 192.168.0.189:8000) — never the website BFF.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


def _mindex_api_base() -> str:
    base = os.getenv("MINDEX_API_URL", "http://192.168.0.189:8000").rstrip("/")
    if not base.endswith("/api/mindex"):
        base = f"{base}/api/mindex"
    return base


def _auth_headers() -> Dict[str, str]:
    headers: Dict[str, str] = {"Accept": "application/json"}
    token = os.getenv("MINDEX_INTERNAL_TOKEN", "").strip()
    if token:
        headers["X-Internal-Token"] = token
        return headers
    api_key = os.getenv("MINDEX_API_KEY", "").strip()
    if api_key:
        headers["X-API-Key"] = api_key
    return headers


class MindexLibraryClient:
    """Async httpx client for MINDEX library + SINE acoustic APIs."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout_s: float = 60.0,
    ) -> None:
        self.base_url = (base_url or _mindex_api_base()).rstrip("/")
        self.timeout_s = timeout_s

    def _json_headers(self) -> Dict[str, str]:
        h = _auth_headers()
        h["Content-Type"] = "application/json"
        return h

    async def health_check(self) -> Dict[str, Any]:
        """Lightweight reachability check via library catalog."""
        try:
            data = await self.list_catalog(limit=1)
            return {"status": "ok", "reachable": True, "db_registered_total": data.get("db_registered_total")}
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                return {
                    "status": "auth_required",
                    "reachable": True,
                    "error": "401 — set MINDEX_INTERNAL_TOKEN or MINDEX_API_KEY",
                }
            logger.warning("MINDEX library health check HTTP %s", exc.response.status_code)
            return {"status": "error", "reachable": False, "error": str(exc)}
        except Exception as exc:
            logger.warning("MINDEX library health check failed: %s", exc)
            return {"status": "unreachable", "reachable": False, "error": str(exc)}

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            response = await client.request(
                method,
                url,
                params=params,
                json=json_body,
                headers=self._json_headers() if json_body is not None else _auth_headers(),
            )
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, dict) else {"result": data}

    async def list_catalog(
        self,
        limit: int = 100,
        path: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"limit": limit}
        if path:
            params["path"] = path
        return await self._request("GET", "/library/catalog", params=params)

    async def list_blobs(
        self,
        category: str = "acoustic",
        *,
        sensor_type: Optional[str] = None,
        origin_dataset_id: Optional[str] = None,
        label_primary: Optional[str] = None,
        acoustic_environment: Optional[str] = None,
        q: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "category": category,
            "limit": limit,
            "offset": offset,
        }
        if sensor_type:
            params["sensor_type"] = sensor_type
        if origin_dataset_id:
            params["origin_dataset_id"] = origin_dataset_id
        if label_primary:
            params["label_primary"] = label_primary
        if acoustic_environment:
            params["acoustic_environment"] = acoustic_environment
        if q:
            params["q"] = q
        return await self._request("GET", "/library/blobs", params=params)

    async def iter_acoustic_blobs(
        self,
        page_size: int = 100,
        max_pages: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Paginate all acoustic blobs (stops on empty page or max_pages)."""
        items: List[Dict[str, Any]] = []
        offset = 0
        pages = 0
        while True:
            if max_pages is not None and pages >= max_pages:
                break
            page = await self.list_blobs(category="acoustic", limit=page_size, offset=offset)
            batch = page.get("items") or []
            if not batch:
                break
            items.extend(batch)
            offset += len(batch)
            pages += 1
            total = int(page.get("total") or 0)
            if offset >= total:
                break
        return items

    async def get_blob(self, blob_id: str) -> Dict[str, Any]:
        return await self._request("GET", f"/library/blobs/{blob_id}")

    def stream_url(self, blob_id: str) -> str:
        """Absolute URL for blob audio stream (agents may fetch or hand to players)."""
        return f"{self.base_url}/library/blobs/{blob_id}/stream"

    async def classify_blob(
        self,
        blob_id: str,
        detectors: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if detectors:
            params["detectors"] = ",".join(detectors)
        return await self._request(
            "POST",
            f"/library/blobs/{blob_id}/classify",
            params=params or None,
        )

    async def analyze_blob(
        self,
        blob_id: str,
        detectors: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Full SINE analysis run (persists detection events)."""
        params: Dict[str, Any] = {}
        if detectors:
            params["detectors"] = ",".join(detectors)
        return await self._request(
            "POST",
            f"/sine/blobs/{blob_id}/analyze",
            params=params or None,
        )

    async def get_human_tags(
        self,
        limit: int = 100,
        offset: int = 0,
        training_eligible_only: bool = True,
    ) -> Dict[str, Any]:
        return await self._request(
            "GET",
            "/sine/training/human-tags",
            params={
                "limit": limit,
                "offset": offset,
                "training_eligible_only": training_eligible_only,
            },
        )

    async def post_wave_annotation(
        self,
        blob_id: str,
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        return await self._request(
            "POST",
            f"/library/blobs/{blob_id}/wave-annotation",
            json_body=body,
        )

    async def post_human_identification(
        self,
        blob_id: str,
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        return await self._request(
            "POST",
            f"/library/blobs/{blob_id}/human-identification",
            json_body=body,
        )

    async def persist_nmf(
        self,
        packet: Dict[str, Any],
        source_id: str = "",
        anomaly_score: float = 0.0,
    ) -> Dict[str, Any]:
        """Forward Nature Message Frame packet to MINDEX nlm.nature_embeddings."""
        return await self._request(
            "POST",
            "/nlm/nmf",
            json_body={
                "packet": packet,
                "source_id": source_id,
                "anomaly_score": anomaly_score,
            },
        )


def get_mindex_library_client() -> MindexLibraryClient:
    return MindexLibraryClient()
