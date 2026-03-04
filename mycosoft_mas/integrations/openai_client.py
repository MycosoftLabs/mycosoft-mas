"""
OpenAI / ChatGPT Integration Client.

GPT inference, embeddings, image generation, fine-tuning, Assistants API.
Used by LLM pipeline and MAS agents.

Environment Variables:
    OPENAI_API_KEY: API key from platform.openai.com
"""

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

OPENAI_API_BASE = "https://api.openai.com/v1"


class OpenAIClient:
    """Client for OpenAI API."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.api_key = self.config.get("api_key", os.environ.get("OPENAI_API_KEY", ""))
        self.timeout = self.config.get("timeout", 60)
        self._client: Optional[httpx.AsyncClient] = None

    def _headers(self) -> Dict[str, str]:
        h: Dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=OPENAI_API_BASE,
                headers=self._headers(),
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
    ) -> Optional[str]:
        """Chat completion, returns assistant message content."""
        if not self.api_key:
            return None
        client = await self._get_client()
        try:
            r = await client.post(
                "/chat/completions",
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                },
            )
            if r.is_success:
                data = r.json()
                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content")
            return None
        except Exception as e:
            logger.warning("OpenAI chat failed: %s", e)
            return None

    async def embeddings(
        self, text: str, model: str = "text-embedding-3-small"
    ) -> Optional[List[float]]:
        """Get embedding for text."""
        if not self.api_key:
            return None
        client = await self._get_client()
        try:
            r = await client.post(
                "/embeddings",
                json={"model": model, "input": text},
            )
            if r.is_success:
                data = r.json()
                emb = data.get("data", [])
                if emb:
                    return emb[0].get("embedding")
            return None
        except Exception as e:
            logger.warning("OpenAI embeddings failed: %s", e)
            return None

    async def list_models(self) -> List[Dict[str, Any]]:
        """List available models."""
        if not self.api_key:
            return []
        client = await self._get_client()
        try:
            r = await client.get("/models")
            if r.is_success:
                return r.json().get("data", [])
            return []
        except Exception as e:
            logger.warning("OpenAI list_models failed: %s", e)
            return []

    async def health_check(self) -> Dict[str, Any]:
        """Verify connectivity to OpenAI API."""
        if not self.api_key:
            return {"status": "unconfigured", "error": "Missing OPENAI_API_KEY"}
        try:
            client = await self._get_client()
            r = await client.get("/models")
            if r.is_success:
                return {"status": "healthy"}
            return {"status": "unhealthy", "error": r.text[:200]}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
