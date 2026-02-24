"""
UniFi Network API Client

Connects to UniFi Dream Machine Pro / Controller for topology, clients, devices.
Uses X-API-Key authentication (UniFi Network Application 8.x+).

Author: MYCA
Created: February 12, 2026
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


class UniFiClient:
    """
    UniFi Network API client.
    Env: UNIFI_HOST, UNIFI_API_KEY, UNIFI_SITE (default: default)
    """

    def __init__(
        self,
        host: Optional[str] = None,
        api_key: Optional[str] = None,
        site: Optional[str] = None,
        verify_ssl: bool = False,
    ):
        self.host = host or os.environ.get("UNIFI_HOST", "192.168.0.1")
        self.api_key = api_key or os.environ.get("UNIFI_API_KEY")
        self.site = site or os.environ.get("UNIFI_SITE", "default")
        self.verify_ssl = verify_ssl
        self._base = f"https://{self.host}/proxy/network/api/s/{self.site}"

    def _headers(self) -> Dict[str, str]:
        return {"X-API-Key": self.api_key or "", "Content-Type": "application/json"}

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def get_devices(self) -> List[Dict[str, Any]]:
        """Fetch all network devices (APs, switches, gateways)."""
        return await self._get("/stat/device")

    async def get_clients(self) -> List[Dict[str, Any]]:
        """Fetch all connected clients (sta)."""
        return await self._get("/stat/sta")

    async def get_topology(self) -> Dict[str, Any]:
        """Fetch devices and clients for topology view."""
        devices = await self.get_devices()
        clients = await self.get_clients()
        return {"devices": devices, "clients": clients}

    async def get_health(self) -> List[Dict[str, Any]]:
        """Fetch controller health stats."""
        return await self._get("/stat/health")

    async def get_alarms(self) -> List[Dict[str, Any]]:
        """Fetch active alarms."""
        return await self._get("/stat/alarm")

    async def _get(self, path: str) -> List[Dict[str, Any]]:
        if not HAS_HTTPX:
            logger.warning("httpx not installed; UniFi client unavailable")
            return []
        if not self.api_key:
            return []

        url = f"{self._base}{path}"
        try:
            async with httpx.AsyncClient(verify=self.verify_ssl, timeout=15.0) as client:
                r = await client.get(url, headers=self._headers())
                r.raise_for_status()
                data = r.json()
                return data.get("data", [])
        except Exception as e:
            logger.warning("UniFi API request failed: %s", e)
            return []
