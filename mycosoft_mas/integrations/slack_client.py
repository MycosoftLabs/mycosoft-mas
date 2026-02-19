"""
Slack Integration Client.

Post messages, list channels, interact with Slack. Used by: SecretaryAgent,
n8n workflows, MYCA notifications.

Environment Variables:
    SLACK_OAUTH_TOKEN: OAuth token (xoxb- for bot, xoxp- for user)
                       Create at https://api.slack.com/apps
"""

import os
import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

SLACK_API_BASE = "https://slack.com/api"


class SlackClient:
    """Client for Slack Web API."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.token = self.config.get("token", os.getenv("SLACK_OAUTH_TOKEN", ""))
        self.timeout = self.config.get("timeout", 30)
        self._client: Optional[httpx.AsyncClient] = None

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json; charset=utf-8",
        }

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=SLACK_API_BASE,
                headers=self._headers(),
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def post_message(
        self,
        channel: str,
        text: str,
        thread_ts: Optional[str] = None,
        blocks: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Post a message to a channel (channel ID or name)."""
        if not self.token:
            logger.warning("Slack client: no SLACK_OAUTH_TOKEN set")
            return None
        client = await self._get_client()
        body: Dict[str, Any] = {"channel": channel, "text": text}
        if thread_ts:
            body["thread_ts"] = thread_ts
        if blocks:
            body["blocks"] = blocks
        try:
            r = await client.post("/chat.postMessage", json=body)
            data = r.json()
            if not data.get("ok"):
                logger.warning("Slack post_message error: %s", data.get("error"))
                return None
            return data
        except Exception as e:
            logger.warning("Slack post_message failed: %s", e)
            return None

    async def list_channels(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List public channels (conversations.list)."""
        if not self.token:
            return []
        client = await self._get_client()
        try:
            r = await client.get("/conversations.list", params={"limit": limit, "types": "public_channel"})
            data = r.json()
            if not data.get("ok"):
                return []
            return data.get("channels", [])
        except Exception as e:
            logger.warning("Slack list_channels failed: %s", e)
            return []

    async def auth_test(self) -> bool:
        """Verify token is valid."""
        if not self.token:
            return False
        client = await self._get_client()
        try:
            r = await client.get("/auth.test")
            return r.json().get("ok", False)
        except Exception:
            return False
