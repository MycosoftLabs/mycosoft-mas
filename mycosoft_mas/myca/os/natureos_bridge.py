"""
NatureOS Bridge — Apps, tooling, analytics, and ecosystem context.

Promotes NatureOS from an adjacent client/sensor surface into a first-class
runtime bridge for MYCA OS. Used when MYCA needs platform status, device
telemetry, workflow/tool context, or NatureOS application awareness.

Date: 2026-03-06
"""

from __future__ import annotations

import logging
from typing import Optional

import aiohttp

logger = logging.getLogger("myca.os.natureos_bridge")


class NatureOSBridge:
    """Bridge to NatureOS APIs and proxy surfaces."""

    def __init__(self, os_ref):
        self._os = os_ref
        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize(self):
        self._session = aiohttp.ClientSession()
        logger.info("NatureOS Bridge initialized")

    async def cleanup(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def health_check(self) -> dict:
        """Check whether at least one NatureOS surface is reachable."""
        if not self._session or self._session.closed:
            return {"healthy": False, "surface": None}

        from mycosoft_mas.integrations.natureos_client import NATUREOSClient

        client = NATUREOSClient()
        checks = {"healthy": False, "surface": None}

        try:
            status_url = (
                f"{client.mas_base_url.rstrip('/')}/api/natureos/status"
                if client.mas_base_url
                else ""
            )
            if status_url:
                async with self._session.get(
                    status_url,
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    if resp.status == 200:
                        checks["healthy"] = True
                        checks["surface"] = "mas-natureos-status"
                        return checks
        except Exception:
            pass

        try:
            matlab = await client.get_matlab_health()
            if matlab:
                checks["healthy"] = True
                checks["surface"] = "natureos-matlab"
        except Exception:
            pass

        return checks

    async def get_context_summary(self) -> str:
        """Get a short NatureOS summary for LLM/live runtime context."""
        if not self._session or self._session.closed:
            return ""

        from mycosoft_mas.integrations.natureos_client import NATUREOSClient

        client = NATUREOSClient()
        parts: list[str] = []

        try:
            if client.mas_base_url:
                async with self._session.get(
                    f"{client.mas_base_url.rstrip('/')}/api/natureos/status",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if isinstance(data, dict):
                            summary = (
                                data.get("summary") or data.get("status") or data.get("message")
                            )
                            if summary:
                                parts.append(f"NatureOS status: {summary}")
        except Exception as e:
            logger.debug("NatureOS status summary failed: %s", e)

        try:
            matlab = await client.get_matlab_health()
            if isinstance(matlab, dict):
                engine_status = matlab.get("status") or matlab.get("engine") or "available"
                parts.append(f"NatureOS analysis engine: {engine_status}")
        except Exception as e:
            logger.debug("NatureOS MATLAB health failed: %s", e)

        try:
            devices = await client._get("/api/Devices")
            if isinstance(devices, dict):
                device_items = (
                    devices.get("devices") or devices.get("data") or devices.get("items") or []
                )
                if isinstance(device_items, list):
                    parts.append(f"NatureOS devices: {len(device_items)} visible")
        except Exception as e:
            logger.debug("NatureOS device summary failed: %s", e)

        if not parts:
            return "NatureOS: platform surfaces available when API and proxy routes are reachable."
        return " ".join(parts)
