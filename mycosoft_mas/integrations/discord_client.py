"""
Discord Integration Client.

Send messages, read channels, add reactions via Discord REST API.
Used by MYCA omnichannel system for Discord platform output.

Environment Variables:
    MYCA_DISCORD_TOKEN: Bot token for MYCA Discord bot
"""

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

DISCORD_API_BASE = "https://discord.com/api/v10"


class DiscordClient:
    """Client for Discord REST API."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.token = self.config.get("token", os.getenv("MYCA_DISCORD_TOKEN", ""))
        self.timeout = self.config.get("timeout", 30)
        self._client: Optional[httpx.AsyncClient] = None

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bot {self.token}",
            "Content-Type": "application/json; charset=utf-8",
        }

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=DISCORD_API_BASE,
                headers=self._headers(),
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def send_message(
        self,
        channel_id: str,
        text: str,
        thread_id: Optional[str] = None,
        embed: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Send a message to a channel (or thread)."""
        if not self.token:
            logger.warning("Discord client: no MYCA_DISCORD_TOKEN set")
            return None
        target = thread_id or channel_id
        client = await self._get_client()
        body: Dict[str, Any] = {"content": text[:2000]}
        if embed:
            body["embeds"] = [embed]
        try:
            r = await client.post(f"/channels/{target}/messages", json=body)
            if r.status_code >= 400:
                logger.warning(
                    "Discord send_message error: %s %s",
                    r.status_code,
                    r.text[:200],
                )
                return None
            return r.json()
        except Exception as e:
            logger.warning("Discord send_message failed: %s", e)
            return None

    async def read_channel(
        self,
        channel_id: str,
        limit: int = 50,
        before: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Read messages from a channel."""
        if not self.token:
            return []
        client = await self._get_client()
        params: Dict[str, Any] = {"limit": min(limit, 100)}
        if before:
            params["before"] = before
        try:
            r = await client.get(f"/channels/{channel_id}/messages", params=params)
            if r.status_code >= 400:
                return []
            data = r.json()
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.warning("Discord read_channel failed: %s", e)
            return []

    async def add_reaction(
        self,
        channel_id: str,
        message_id: str,
        emoji: str,
    ) -> bool:
        """Add a reaction to a message. Emoji must be URL-encoded or use name:id for custom."""
        if not self.token:
            return False
        client = await self._get_client()
        from urllib.parse import quote

        encoded = quote(emoji) if "%" not in emoji else emoji
        try:
            r = await client.put(
                f"/channels/{channel_id}/messages/{message_id}/" f"reactions/{encoded}/@me"
            )
            return r.status_code in (204, 200)
        except Exception as e:
            logger.warning("Discord add_reaction failed: %s", e)
            return False

    async def auth_test(self) -> bool:
        """Verify token is valid."""
        if not self.token:
            return False
        client = await self._get_client()
        try:
            r = await client.get("/users/@me")
            return r.status_code == 200
        except Exception:
            return False
