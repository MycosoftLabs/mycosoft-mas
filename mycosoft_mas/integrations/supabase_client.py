"""
Supabase Client

Thin async wrapper around Supabase REST, Auth, and Storage APIs.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Async Supabase client using REST/Auth/Storage endpoints."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        self.supabase_url = (config.get("url") or os.environ.get("SUPABASE_URL", "")).rstrip("/")
        self.service_role_key = (
            config.get("service_role_key")
            or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
            or os.environ.get("SUPABASE_SERVICE_KEY")
        )
        self.anon_key = config.get("anon_key") or os.environ.get("SUPABASE_ANON_KEY")
        self.timeout = int(config.get("timeout", 30))

        if not self.supabase_url:
            raise ValueError("SUPABASE_URL is required")

        self.rest_base = f"{self.supabase_url}/rest/v1"
        self.auth_base = f"{self.supabase_url}/auth/v1"
        self.storage_base = f"{self.supabase_url}/storage/v1"

    def _headers(self, use_service_key: bool = True) -> Dict[str, str]:
        key = self.service_role_key if use_service_key else self.anon_key
        if not key:
            raise ValueError("Supabase API key missing (service_role_key or anon_key)")
        return {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, url: str, headers: Dict[str, str], **kwargs) -> Any:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
            if response.text:
                return response.json()
            return {}

    async def health_check(self) -> Dict[str, Any]:
        """Check Supabase Auth health endpoint."""
        try:
            url = f"{self.auth_base}/health"
            result = await self._request("GET", url, headers=self._headers(use_service_key=False))
            return {"status": "ok", "details": result}
        except Exception as exc:
            logger.error("Supabase health check failed: %s", exc)
            return {"status": "error", "error": str(exc)}

    async def auth_sign_in(self, email: str, password: str) -> Dict[str, Any]:
        url = f"{self.auth_base}/token"
        params = {"grant_type": "password"}
        payload = {"email": email, "password": password}
        return await self._request(
            "POST", url, headers=self._headers(use_service_key=False), params=params, json=payload
        )

    async def select(
        self,
        table: str,
        filters: Optional[Dict[str, Any]] = None,
        select: str = "*",
        limit: Optional[int] = None,
        order: Optional[str] = None,
    ) -> Any:
        params: Dict[str, Any] = {"select": select}
        if filters:
            for key, value in filters.items():
                params[key] = f"eq.{value}"
        if limit is not None:
            params["limit"] = limit
        if order:
            params["order"] = order
        url = f"{self.rest_base}/{table}"
        return await self._request("GET", url, headers=self._headers(), params=params)

    async def insert(self, table: str, data: Dict[str, Any]) -> Any:
        url = f"{self.rest_base}/{table}"
        headers = self._headers()
        headers["Prefer"] = "return=representation"
        return await self._request("POST", url, headers=headers, json=data)

    async def update(self, table: str, data: Dict[str, Any], filters: Dict[str, Any]) -> Any:
        params = {key: f"eq.{value}" for key, value in filters.items()}
        url = f"{self.rest_base}/{table}"
        headers = self._headers()
        headers["Prefer"] = "return=representation"
        return await self._request("PATCH", url, headers=headers, params=params, json=data)

    async def delete(self, table: str, filters: Dict[str, Any]) -> Any:
        params = {key: f"eq.{value}" for key, value in filters.items()}
        url = f"{self.rest_base}/{table}"
        headers = self._headers()
        headers["Prefer"] = "return=representation"
        return await self._request("DELETE", url, headers=headers, params=params)

    async def rpc(self, function_name: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.rest_base}/rpc/{function_name}"
        return await self._request("POST", url, headers=self._headers(), json=params or {})

    async def storage_upload(
        self,
        bucket: str,
        path: str,
        content: bytes,
        content_type: str = "application/octet-stream",
        upsert: bool = True,
    ) -> Any:
        url = f"{self.storage_base}/object/{bucket}/{path}"
        headers = self._headers()
        headers["Content-Type"] = content_type
        headers["x-upsert"] = "true" if upsert else "false"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, headers=headers, content=content)
            response.raise_for_status()
            return response.json() if response.text else {"status": "ok"}
