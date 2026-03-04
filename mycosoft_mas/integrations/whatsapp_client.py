"""
WhatsApp Integration Client via Evolution API.

Send messages, send media, interact with WhatsApp via Evolution API
running on MYCA VM (192.168.0.191).

Environment Variables:
    MYCA_EVOLUTION_API_URL: Evolution API base URL (default http://192.168.0.191:8083)
    MYCA_WHATSAPP_INSTANCE: Instance name for Evolution API
"""

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

DEFAULT_EVOLUTION_URL = "http://192.168.0.191:8083"


class WhatsAppClient:
    """Client for Evolution API (WhatsApp)."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.base_url = (
            self.config.get("base_url")
            or os.getenv("MYCA_EVOLUTION_API_URL", DEFAULT_EVOLUTION_URL)
        ).rstrip("/")
        self.instance = self.config.get("instance") or os.getenv(
            "MYCA_WHATSAPP_INSTANCE", "myca"
        )
        self.timeout = self.config.get("timeout", 30)
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def _normalize_phone(self, phone: str) -> str:
        """Ensure phone has country code, no leading + for API."""
        p = phone.strip().replace(" ", "").replace("-", "")
        if p.startswith("+"):
            p = p[1:]
        if not p.startswith("55") and len(p) == 10:
            p = "1" + p
        return p

    async def send_message(
        self,
        phone: str,
        text: str,
        delay: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Send a plain text message to a phone number."""
        client = await self._get_client()
        number = self._normalize_phone(phone)
        payload: Dict[str, Any] = {
            "number": number,
            "text": text,
        }
        if delay is not None:
            payload["delay"] = delay
        try:
            r = await client.post(
                f"/message/sendText/{self.instance}",
                json=payload,
            )
            if r.status_code >= 400:
                logger.warning(
                    "WhatsApp send_message error: %s %s",
                    r.status_code,
                    r.text[:200],
                )
                return None
            return r.json()
        except Exception as e:
            logger.warning("WhatsApp send_message failed: %s", e)
            return None

    async def send_media(
        self,
        phone: str,
        url: str,
        caption: str = "",
        mediatype: str = "image",
        mimetype: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Send media (image/video/document) by URL."""
        client = await self._get_client()
        number = self._normalize_phone(phone)
        payload: Dict[str, Any] = {
            "number": number,
            "mediatype": mediatype,
            "media": url,
            "caption": caption,
        }
        if mimetype:
            payload["mimetype"] = mimetype
        try:
            r = await client.post(
                f"/message/sendMedia/{self.instance}",
                json=payload,
            )
            if r.status_code >= 400:
                logger.warning(
                    "WhatsApp send_media error: %s %s",
                    r.status_code,
                    r.text[:200],
                )
                return None
            return r.json()
        except Exception as e:
            logger.warning("WhatsApp send_media failed: %s", e)
            return None

    async def get_messages(
        self,
        limit: int = 50,
        chat_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch recent messages. Evolution API may expose fetch messages endpoint."""
        client = await self._get_client()
        try:
            r = await client.get(
                f"/chat/findMessages/{self.instance}",
                params={"limit": limit, **({"chatId": chat_id} if chat_id else {})},
            )
            if r.status_code >= 400:
                return []
            data = r.json()
            return data if isinstance(data, list) else data.get("messages", [])
        except Exception as e:
            logger.warning("WhatsApp get_messages failed: %s", e)
            return []

    async def health_check(self) -> bool:
        """Check if Evolution API is reachable."""
        try:
            client = await self._get_client()
            r = await client.get("/", timeout=5)
            return r.status_code < 500
        except Exception:
            return False
