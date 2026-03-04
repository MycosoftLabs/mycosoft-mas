"""
Perplexity Integration Client.

Real-time web search + AI answers, research queries.
Used by research agents and knowledge retrieval.

Environment Variables:
    PERPLEXITY_API_KEY: API key from perplexity.ai
"""

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

PERPLEXITY_API_BASE = "https://api.perplexity.ai"


class PerplexityClient:
    """Client for Perplexity API (OpenAI-compatible)."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.api_key = self.config.get(
            "api_key", os.environ.get("PERPLEXITY_API_KEY", "")
        )
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
                base_url=PERPLEXITY_API_BASE,
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
        model: str = "llama-3.1-sonar-small-128k-online",
        temperature: float = 0.2,
    ) -> Optional[str]:
        """Chat with real-time web search. Returns assistant message content."""
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
                    "max_tokens": 1024,
                },
            )
            if r.is_success:
                data = r.json()
                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content")
            return None
        except Exception as e:
            logger.warning("Perplexity chat failed: %s", e)
            return None

    async def search(self, query: str) -> Optional[str]:
        """Real-time search query. Returns AI answer with citations."""
        return await self.chat(
            messages=[{"role": "user", "content": query}],
        )

    async def health_check(self) -> Dict[str, Any]:
        """Verify connectivity to Perplexity API."""
        if not self.api_key:
            return {"status": "unconfigured", "error": "Missing PERPLEXITY_API_KEY"}
        try:
            out = await self.search("What is 2+2?")
            if out:
                return {"status": "healthy"}
            return {"status": "unhealthy", "error": "No response"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
