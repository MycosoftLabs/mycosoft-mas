"""
Presence Bridge — Live user and staff presence context.

Promotes website presence data into the MYCA OS runtime for staff-awareness,
active sessions, and "who is online" style reasoning.

Date: 2026-03-06
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import aiohttp

logger = logging.getLogger("myca.os.presence_bridge")


class PresenceBridge:
    """Bridge to live presence APIs."""

    def __init__(self, os_ref):
        self._os = os_ref
        self._session: Optional[aiohttp.ClientSession] = None
        self._presence_url = os.getenv(
            "PRESENCE_API_URL", "http://192.168.0.187:3000/api/presence"
        ).rstrip("/")

    async def initialize(self):
        self._session = aiohttp.ClientSession()
        logger.info("Presence Bridge initialized")

    async def cleanup(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def get_presence_summary(self) -> str:
        if not self._session or self._session.closed:
            return ""

        try:
            async with self._session.get(
                f"{self._presence_url}/stats",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    online = data.get("online_users") or data.get("online_count") or 0
                    sessions = data.get("active_sessions") or data.get("sessions_count") or 0
                    staff = data.get("staff_online") or data.get("staff_count") or 0
                    return f"Presence: {online} user(s) online, {sessions} active session(s), {staff} staff online."
        except Exception as e:
            logger.debug("Presence summary fetch failed: %s", e)
        return ""
