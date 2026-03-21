"""
MycoBrain Device Bridge — Device status and telemetry.

Fetches MycoBrain device status (mushroom1, sporebase, etc.) from MAS device registry
and MycoBrain service. Used when MYCA is asked about "devices", "lab", "sensors", "MycoBrain".

MycoBrain service: 8003 (local) or 187:8003 (Sandbox).
MAS device registry: /api/devices (on 188) — heartbeat is canonical write, /register is alias.

Date: 2026-03-07
"""

import logging
import os
from typing import Optional

import aiohttp

logger = logging.getLogger("myca.os.mycobrain_bridge")


class MycoBrainBridge:
    """Bridge to MycoBrain devices and MAS device registry."""

    def __init__(self, os_ref):
        self._os = os_ref
        self._session: Optional[aiohttp.ClientSession] = None
        self._mas_url = os.getenv("MAS_API_URL", "http://192.168.0.188:8001")
        self._mycobrain_url = os.getenv("MYCOBRAIN_SERVICE_URL", "http://192.168.0.187:8003")

    async def initialize(self):
        self._session = aiohttp.ClientSession()
        logger.info("MycoBrain Bridge initialized")

    async def cleanup(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def get_device_status(self) -> list:
        """
        Get status of all registered MycoBrain devices from MAS registry.

        Returns:
            List of device dicts with id, name, status, role, last_seen, etc.
        """
        if not self._session or self._session.closed:
            return []

        try:
            async with self._session.get(
                f"{self._mas_url.rstrip('/')}/api/devices",
                params={"include_offline": "true"},
                timeout=aiohttp.ClientTimeout(total=8),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    devices = (
                        data.get("devices", data)
                        if isinstance(data, dict)
                        else (data if isinstance(data, list) else [])
                    )
                    return devices if isinstance(devices, list) else []
        except Exception as e:
            logger.debug("Device status fetch failed: %s", e)
        return []

    async def get_telemetry_summary(self) -> str:
        """
        Get a short text summary of device status and telemetry for LLM context.
        """
        devices = await self.get_device_status()
        if not devices:
            # Fallback: try MycoBrain service /devices directly
            try:
                if self._session and not self._session.closed:
                    async with self._session.get(
                        f"{self._mycobrain_url.rstrip('/')}/devices",
                        timeout=aiohttp.ClientTimeout(total=5),
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            devs = data.get("devices", []) if isinstance(data, dict) else []
                            if devs:
                                return _format_device_summary(devs)
            except Exception:
                pass
            return "MycoBrain: No devices in registry. Device status available when MycoBrain service and MAS are running."

        return _format_device_summary(devices)


def _format_device_summary(devices: list) -> str:
    """Format device list as a short summary using device_* fields from MAS registry."""
    if not devices:
        return ""
    parts = [f"MycoBrain devices: {len(devices)} registered."]
    for d in devices[:5]:
        name = d.get("device_display_name") or d.get("device_name") or d.get("device_id", "unknown")
        status = d.get("status", d.get("online", "unknown"))
        role = d.get("device_role", "")
        s = f"{name}({status})"
        if role:
            s += f" [{role}]"
        parts.append(s)
    return " ".join(parts)
