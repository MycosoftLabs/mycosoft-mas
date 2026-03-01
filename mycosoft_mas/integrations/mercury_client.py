"""
Mercury Banking API client.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx


class MercuryClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: int = 30,
    ):
        self.api_key = api_key or os.getenv("MERCURY_API_KEY", "")
        self.base_url = (base_url or os.getenv("MERCURY_API_BASE_URL", "https://api.mercury.com")).rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._client: Optional[httpx.AsyncClient] = None

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout_seconds,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def get_accounts(self) -> List[Dict[str, Any]]:
        if not self.is_configured():
            raise RuntimeError("MERCURY_API_KEY is required")
        client = await self._get_client()
        resp = await client.get(f"{self.base_url}/api/v1/accounts")
        resp.raise_for_status()
        payload = resp.json()
        return payload.get("accounts", [])

    async def get_account_balance(self, account_id: str) -> Dict[str, Any]:
        if not self.is_configured():
            raise RuntimeError("MERCURY_API_KEY is required")
        client = await self._get_client()
        resp = await client.get(f"{self.base_url}/api/v1/account/{account_id}")
        resp.raise_for_status()
        account = resp.json()
        return {
            "account_id": account_id,
            "available_balance": account.get("availableBalance"),
            "current_balance": account.get("currentBalance"),
            "currency": account.get("currency", "USD"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def get_transactions(
        self,
        account_id: str,
        *,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        if not self.is_configured():
            raise RuntimeError("MERCURY_API_KEY is required")
        client = await self._get_client()
        params: Dict[str, Any] = {"limit": limit}
        if start_date:
            params["start"] = start_date
        if end_date:
            params["end"] = end_date
        resp = await client.get(
            f"{self.base_url}/api/v1/account/{account_id}/transactions",
            params=params,
        )
        resp.raise_for_status()
        payload = resp.json()
        return payload.get("transactions", [])
