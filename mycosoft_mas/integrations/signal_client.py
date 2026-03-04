"""
Signal Integration Client via signal-cli REST API.

Send messages, receive messages, list groups via signal-cli REST API
running on MYCA VM (192.168.0.191).

Environment Variables:
    MYCA_SIGNAL_CLI_URL: signal-cli REST base URL (default http://192.168.0.191:8089)
    MYCA_SIGNAL_NUMBER: MYCA's Signal phone number (e.g. +1234567890)
"""

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

DEFAULT_SIGNAL_CLI_URL = "http://192.168.0.191:8089"


class SignalClient:
    """Client for signal-cli REST API."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.base_url = (
            self.config.get("base_url")
            or os.getenv("MYCA_SIGNAL_CLI_URL", DEFAULT_SIGNAL_CLI_URL)
        ).rstrip("/")
        self.number = self.config.get("number") or os.getenv(
            "MYCA_SIGNAL_NUMBER", ""
        )
        self.timeout = self.config.get("timeout", 30)
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def _normalize_recipient(self, recipient: str) -> str:
        """Normalize phone or group ID for API."""
        r = recipient.strip()
        if r.startswith("group."):
            return r
        return r.replace(" ", "").replace("-", "")

    async def send_message(
        self,
        recipient: str,
        text: str,
        attachments: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Send a message to a phone number or group.

        Uses v2 send: POST /v2/send with message, number, recipients.
        """
        if not self.number:
            logger.warning("Signal client: no MYCA_SIGNAL_NUMBER set")
            return None
        client = await self._get_client()
        rec = self._normalize_recipient(recipient)
        payload: Dict[str, Any] = {
            "message": text,
            "number": self.number,
            "recipients": [rec],
        }
        if attachments:
            payload["base64_attachments"] = attachments
        try:
            r = await client.post("/v2/send", json=payload)
            if r.status_code >= 400:
                logger.warning(
                    "Signal send_message error: %s %s",
                    r.status_code,
                    r.text[:200],
                )
                return None
            return r.json() if r.content else {"status": "sent"}
        except Exception as e:
            logger.warning("Signal send_message failed: %s", e)
            return None

    async def receive_messages(self) -> List[Dict[str, Any]]:
        """Receive messages. signal-cli REST typically uses webhooks for receive."""
        client = await self._get_client()
        try:
            r = await client.get("/v1/receive/" + self.number.replace("+", ""))
            if r.status_code >= 400:
                return []
            data = r.json()
            return data if isinstance(data, list) else data.get("data", [])
        except Exception as e:
            logger.warning("Signal receive_messages failed: %s", e)
            return []

    async def list_groups(self) -> List[Dict[str, Any]]:
        """List groups for the configured number."""
        if not self.number:
            return []
        client = await self._get_client()
        try:
            r = await client.get(
                "/v1/groups/" + self.number.replace("+", "").replace(" ", "")
            )
            if r.status_code >= 400:
                return []
            data = r.json()
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.warning("Signal list_groups failed: %s", e)
            return []

    async def health_check(self) -> bool:
        """Check if signal-cli REST API is reachable."""
        try:
            client = await self._get_client()
            r = await client.get("/v1/about", timeout=5)
            return r.status_code < 500
        except Exception:
            return False
