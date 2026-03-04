"""
Hugging Face Integration Client.

Model search, inference API, datasets, Spaces. Used by ML agents and training pipelines.

Environment Variables:
    HUGGINGFACE_TOKEN: Access token from huggingface.co/settings/tokens
"""

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

HF_API_BASE = "https://huggingface.co/api"
HF_INFERENCE_BASE = "https://api-inference.huggingface.co"


class HuggingFaceClient:
    """Client for Hugging Face Hub and Inference API."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.token = self.config.get("token", os.environ.get("HUGGINGFACE_TOKEN", ""))
        self.timeout = self.config.get("timeout", 60)
        self._client: Optional[httpx.AsyncClient] = None

    def _headers(self) -> Dict[str, str]:
        h: Dict[str, str] = {}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=HF_API_BASE,
                headers=self._headers(),
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def search_models(
        self,
        query: str = "",
        author: Optional[str] = None,
        library: Optional[str] = None,
        limit: int = 30,
    ) -> List[Dict[str, Any]]:
        """Search models on Hugging Face Hub."""
        client = await self._get_client()
        try:
            params: Dict[str, Any] = {"limit": min(limit, 100)}
            if query:
                params["search"] = query
            if author:
                params["author"] = author
            if library:
                params["library"] = library
            r = await client.get("/models", params=params)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.warning("HuggingFace search_models failed: %s", e)
            return []

    async def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get model metadata."""
        client = await self._get_client()
        try:
            r = await client.get(f"/models/{model_id}")
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.warning("HuggingFace get_model_info failed: %s", e)
            return None

    async def inference(
        self,
        model_id: str,
        inputs: Any,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Run inference via Hugging Face Inference API."""
        if not self.token:
            logger.warning("HuggingFace inference requires HUGGINGFACE_TOKEN")
            return None
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            try:
                body: Dict[str, Any] = {"inputs": inputs}
                if parameters:
                    body["parameters"] = parameters
                r = await c.post(
                    f"{HF_INFERENCE_BASE}/models/{model_id}",
                    headers={"Authorization": f"Bearer {self.token}"},
                    json=body,
                )
                if r.is_success:
                    return r.json()
                return {"error": r.text[:500]}
            except Exception as e:
                logger.warning("HuggingFace inference failed: %s", e)
                return None

    async def list_datasets(
        self,
        search: Optional[str] = None,
        author: Optional[str] = None,
        limit: int = 30,
    ) -> List[Dict[str, Any]]:
        """List datasets."""
        client = await self._get_client()
        try:
            params: Dict[str, Any] = {"limit": min(limit, 100)}
            if search:
                params["search"] = search
            if author:
                params["author"] = author
            r = await client.get("/datasets", params=params)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.warning("HuggingFace list_datasets failed: %s", e)
            return []

    async def list_spaces(
        self,
        search: Optional[str] = None,
        author: Optional[str] = None,
        limit: int = 30,
    ) -> List[Dict[str, Any]]:
        """List Spaces (hosted apps)."""
        client = await self._get_client()
        try:
            params: Dict[str, Any] = {"limit": min(limit, 100)}
            if search:
                params["search"] = search
            if author:
                params["author"] = author
            r = await client.get("/spaces", params=params)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.warning("HuggingFace list_spaces failed: %s", e)
            return []

    async def trending_models(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get trending models (by downloads)."""
        models = await self.search_models(limit=limit)
        return sorted(models, key=lambda m: m.get("downloads", 0), reverse=True)[:limit]

    async def health_check(self) -> Dict[str, Any]:
        """Verify connectivity to Hugging Face API."""
        try:
            client = await self._get_client()
            r = await client.get("/models", params={"limit": 1})
            if r.is_success:
                return {"status": "healthy"}
            return {"status": "unhealthy", "error": r.text[:200]}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
