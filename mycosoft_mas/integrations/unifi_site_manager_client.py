"""
UniFi Site Manager API client (cloud).

Uses the official Site Manager REST API at api.ui.com with X-API-Key auth.
Complements the local-controller client in unifi_client.py (UNIFI_HOST / proxy/network).

Spec reference: https://developer.ui.com/site-manager-api/

Author: MYCA
Created: March 25, 2026
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    import httpx

    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


class UniFiSiteManagerError(Exception):
    """Raised when Site Manager API returns an error or the client is misconfigured."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


def _resolve_api_key() -> str:
    return (
        os.environ.get("UNIFI_SITE_MANAGER_API_KEY", "")
        or os.environ.get("UI_COM_API_KEY", "")
        or ""
    ).strip()


class UniFiSiteManagerClient:
    """
    UniFi Site Manager (cloud) API client.

    Env:
      UNIFI_SITE_MANAGER_API_KEY — API key from unifi.ui.com (preferred)
      UI_COM_API_KEY — alternate name for the same key
      UNIFI_SITE_MANAGER_BASE_URL — default https://api.ui.com
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        self.api_key = (api_key if api_key is not None else _resolve_api_key()).strip()
        self.base_url = (
            base_url or os.environ.get("UNIFI_SITE_MANAGER_BASE_URL") or "https://api.ui.com"
        ).rstrip("/")
        self.timeout = timeout

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> Dict[str, str]:
        return {
            "X-API-Key": self.api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def _request_get(self, path: str, query: Optional[List[Tuple[str, str]]] = None) -> Any:
        if not HAS_HTTPX:
            raise UniFiSiteManagerError("httpx not installed", status_code=503)
        if not self.api_key:
            raise UniFiSiteManagerError(
                "Site Manager API key not set (UNIFI_SITE_MANAGER_API_KEY or UI_COM_API_KEY)",
                status_code=503,
            )
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.get(url, headers=self._headers(), params=query or [])
                if r.status_code == 401:
                    raise UniFiSiteManagerError("Site Manager API rejected the API key", 401)
                if r.status_code == 429:
                    raise UniFiSiteManagerError("Site Manager API rate limited", 429)
                r.raise_for_status()
                return r.json()
        except UniFiSiteManagerError:
            raise
        except httpx.HTTPStatusError as e:
            logger.warning("Site Manager HTTP error: %s %s", e.response.status_code, e)
            raise UniFiSiteManagerError(
                f"Site Manager API error: HTTP {e.response.status_code}",
                status_code=502,
            ) from e
        except Exception as e:
            logger.warning("Site Manager request failed: %s", e)
            raise UniFiSiteManagerError(str(e), status_code=502) from e

    async def list_hosts(
        self,
        page_size: Optional[str] = None,
        next_token: Optional[str] = None,
    ) -> Any:
        """GET /v1/hosts — all hosts for the UI account."""
        q: List[Tuple[str, str]] = []
        if page_size:
            q.append(("pageSize", page_size))
        if next_token:
            q.append(("nextToken", next_token))
        return await self._request_get("/v1/hosts", q or None)

    async def get_host(self, host_id: str) -> Any:
        """GET /v1/hosts/{id}"""
        return await self._request_get(f"/v1/hosts/{host_id}")

    async def list_sites(self) -> Any:
        """GET /v1/sites — sites from hosts running UniFi Network application."""
        return await self._request_get("/v1/sites")

    async def list_devices(
        self,
        host_ids: Optional[List[str]] = None,
        time: Optional[str] = None,
        page_size: Optional[str] = None,
        next_token: Optional[str] = None,
    ) -> Any:
        """GET /v1/devices — optional hostIds, time, pagination."""
        q: List[Tuple[str, str]] = []
        for hid in host_ids or []:
            if hid:
                q.append(("hostIds", hid))
        if time:
            q.append(("time", time))
        if page_size:
            q.append(("pageSize", page_size))
        if next_token:
            q.append(("nextToken", next_token))
        return await self._request_get("/v1/devices", q or None)
