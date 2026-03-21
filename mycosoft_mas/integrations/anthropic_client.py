"""
Anthropic / Claude Integration Client.

Claude inference, tool use, batch processing, prompt caching.
Used by LLM pipeline and MAS agents.

Environment Variables:
    ANTHROPIC_API_KEY: API key from console.anthropic.com
"""

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

ANTHROPIC_API_BASE = "https://api.anthropic.com/v1"


class AnthropicClient:
    """Client for Anthropic Claude API."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.api_key = self.config.get("api_key", os.environ.get("ANTHROPIC_API_KEY", ""))
        self.timeout = self.config.get("timeout", 60)
        self._client: Optional[httpx.AsyncClient] = None

    def _headers(self) -> Dict[str, str]:
        h: Dict[str, str] = {
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        if self.api_key:
            h["x-api-key"] = self.api_key
        return h

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=ANTHROPIC_API_BASE,
                headers=self._headers(),
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def messages(
        self,
        messages: List[Dict[str, Any]],
        model: str = "claude-3-5-sonnet-20241022",
        max_tokens: int = 1024,
        system: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Send messages and get Claude response."""
        if not self.api_key:
            return None
        client = await self._get_client()
        body: Dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system:
            body["system"] = system
        if tools:
            body["tools"] = tools
        try:
            r = await client.post("/messages", json=body)
            if r.is_success:
                return r.json()
            return None
        except Exception as e:
            logger.warning("Anthropic messages failed: %s", e)
            return None

    async def chat(
        self,
        content: str,
        model: str = "claude-3-5-sonnet-20241022",
        system: Optional[str] = None,
    ) -> Optional[str]:
        """Simple chat, returns text content."""
        out = await self.messages(
            messages=[{"role": "user", "content": content}],
            model=model,
            system=system,
        )
        if not out:
            return None
        for block in out.get("content", []):
            if block.get("type") == "text":
                return block.get("text")
        return None

    async def health_check(self) -> Dict[str, Any]:
        """Verify connectivity to Anthropic API."""
        if not self.api_key:
            return {"status": "unconfigured", "error": "Missing ANTHROPIC_API_KEY"}
        try:
            out = await self.chat("Say OK", model="claude-3-haiku-20240307")
            if out:
                return {"status": "healthy"}
            return {"status": "unhealthy", "error": "No response"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
