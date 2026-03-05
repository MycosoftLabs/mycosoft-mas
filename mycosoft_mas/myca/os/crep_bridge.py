"""
CREP Bridge — Live worldview from Common Relevant Environmental Picture.

Fetches situational awareness: aviation, maritime, satellites, weather, fungal layer.
Used when MYCA needs environmental context (e.g. "what's happening in the lab", "environmental status").

References: CREP dashboard at /natureos/crep, /dashboard/crep; MAS has crep-agent, crep-collector.

Date: 2026-03-02
"""

import os
import logging
from typing import Optional

import aiohttp

logger = logging.getLogger("myca.os.crep_bridge")


class CREPBridge:
    """Bridge to CREP (Common Relevant Environmental Picture) for live worldview."""

    def __init__(self, os_ref):
        self._os = os_ref
        self._session: Optional[aiohttp.ClientSession] = None
        self._mas_url = os.getenv("MAS_API_URL", "http://192.168.0.188:8001")

    async def initialize(self):
        self._session = aiohttp.ClientSession()
        logger.info("CREP Bridge initialized")

    async def cleanup(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def get_worldview_summary(self) -> str:
        """
        Fetch a short text summary of current environmental situation.
        Returns a human-readable summary for LLM context, or empty string on failure.
        """
        if not self._session or self._session.closed:
            return ""

        try:
            async with self._session.get(
                f"{self._mas_url.rstrip('/')}/api/crep/stream/status",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    connections = data.get("active_connections", 0)
                    return f"CREP stream: {connections} active dashboard connection(s). Environmental data (aviation, maritime, satellites, weather) available when collectors are running."
            return "CREP: Stream status unknown."
        except Exception as e:
            logger.debug("CREP worldview fetch failed: %s", e)
        return ""
