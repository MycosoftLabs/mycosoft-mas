"""
NLM Bridge — Nature Learning Model context and health.

Promotes NLM from a background scientific surface into a first-class MYCA OS
runtime bridge for environmental intelligence and biosphere-grounded context.

Date: 2026-03-06
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import aiohttp

logger = logging.getLogger("myca.os.nlm_bridge")


class NLMBridge:
    """Bridge to the Nature Learning Model API."""

    def __init__(self, os_ref):
        self._os = os_ref
        self._session: Optional[aiohttp.ClientSession] = None
        self._nlm_url = os.getenv("NLM_API_URL", "http://192.168.0.188:8200").rstrip("/")

    async def initialize(self):
        self._session = aiohttp.ClientSession()
        logger.info("NLM Bridge initialized")

    async def cleanup(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def get_summary(self) -> str:
        if not self._session or self._session.closed:
            return ""

        try:
            async with self._session.get(
                f"{self._nlm_url}/health",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    status = data.get("status", "healthy")
                    model = data.get("model") or data.get("service") or "NLM"
                    return f"NLM: {model} is {status}."
        except Exception as e:
            logger.debug("NLM summary fetch failed: %s", e)
        return ""
