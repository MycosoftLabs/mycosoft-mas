"""
Mycorrhizae Protocol Client for MAS

Publishes and subscribes to Mycorrhizae channels for device communication.
Used by device APIs and agents for real-time device telemetry and commands.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Callable, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


def _get_config() -> tuple[str, str]:
    api_url = os.environ.get("MYCORRHIZAE_API_URL", "http://192.168.0.187:8002").rstrip("/")
    api_key = os.environ.get("MYCORRHIZAE_API_KEY", "")
    return api_url, api_key


class MycorrhizaeClient:
    """
    MAS client for Mycorrhizae Protocol.
    Publishes device commands and can subscribe to device telemetry.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        url, key = _get_config()
        self.base_url = (base_url or url).rstrip("/")
        self.api_key = api_key or key

    def _headers(self) -> Dict[str, str]:
        h: Dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            h["X-API-Key"] = self.api_key
        return h

    async def publish(
        self,
        channel: str,
        payload: Dict[str, Any],
        message_type: str = "telemetry",
    ) -> bool:
        """Publish a message to a Mycorrhizae channel."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self.base_url}/api/channels/{channel}/publish",
                    json={"payload": payload, "message_type": message_type},
                    headers=self._headers(),
                )
            return resp.status_code in (200, 201)
        except Exception as e:
            logger.warning("Mycorrhizae publish failed: %s", e)
            return False

    async def send_device_command(
        self,
        device_id: str,
        command: Dict[str, Any],
    ) -> bool:
        """Send a command to a device via Mycorrhizae command channel."""
        channel = f"device.{device_id}.command"
        return await self.publish(channel, command, message_type="command")
