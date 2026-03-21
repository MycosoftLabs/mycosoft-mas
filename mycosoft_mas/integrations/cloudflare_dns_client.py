"""
Cloudflare DNS API Client

Fetches DNS records and zone info for DNS integrity checks.
Uses Bearer token (API Token with Zone:DNS:Read).

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


class CloudflareDNSClient:
    """
    Cloudflare DNS API client for DNS record inspection.
    Env: CLOUDFLARE_API_TOKEN, CLOUDFLARE_ZONE_ID
    """

    API_BASE = "https://api.cloudflare.com/client/v4"

    def __init__(
        self,
        api_token: Optional[str] = None,
        zone_id: Optional[str] = None,
    ):
        self.api_token = api_token or os.environ.get("CLOUDFLARE_API_TOKEN")
        self.zone_id = zone_id or os.environ.get("CLOUDFLARE_ZONE_ID")

    def is_configured(self) -> bool:
        return bool(self.api_token and self.zone_id)

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    async def list_dns_records(
        self,
        type_filter: Optional[str] = None,
        name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List DNS records in the zone."""
        if not self.is_configured():
            return []

        url = f"{self.API_BASE}/zones/{self.zone_id}/dns_records"
        params = {}
        if type_filter:
            params["type"] = type_filter
        if name:
            params["name"] = name

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(url, headers=self._headers(), params=params or None)
                r.raise_for_status()
                data = r.json()
                if data.get("success"):
                    return data.get("result", [])
        except Exception as e:
            logger.warning("Cloudflare DNS API request failed: %s", e)

        return []

    async def get_zone_info(self) -> Optional[Dict[str, Any]]:
        """Get zone details (status, name_servers, etc.)."""
        if not self.is_configured():
            return None

        url = f"{self.API_BASE}/zones/{self.zone_id}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(url, headers=self._headers())
                r.raise_for_status()
                data = r.json()
                if data.get("success"):
                    return data.get("result")
        except Exception as e:
            logger.warning("Cloudflare zone API request failed: %s", e)

        return None
