"""
Relay Financial Integration Client.

Account balances, transfers, transaction history, card management.
Used by RelayFinancialAgent and treasury automation.

Environment Variables:
    RELAY_API_KEY: API key from Relay Financial
    RELAY_API_BASE_URL: Optional override (default https://api.relayfi.com)
"""

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

RELAY_API_BASE = "https://api.relayfi.com"


class RelayClient:
    """Client for Relay Financial banking API."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.api_key = self.config.get("api_key", os.environ.get("RELAY_API_KEY", ""))
        self.base_url = self.config.get(
            "base_url", os.environ.get("RELAY_API_BASE_URL", RELAY_API_BASE)
        )
        self.timeout = self.config.get("timeout", 30)
        self._client: Optional[httpx.AsyncClient] = None

    def _headers(self) -> Dict[str, str]:
        h: Dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self._headers(),
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def list_accounts(self) -> List[Dict[str, Any]]:
        """List bank accounts."""
        if not self.api_key:
            return []
        client = await self._get_client()
        try:
            r = await client.get("/accounts")
            if r.is_success:
                data = r.json()
                return data.get("accounts", data) if isinstance(data, dict) else data
            return []
        except Exception as e:
            logger.warning("Relay list_accounts failed: %s", e)
            return []

    async def get_balance(self, account_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get account balance(s)."""
        if not self.api_key:
            return None
        client = await self._get_client()
        try:
            path = f"/accounts/{account_id}/balance" if account_id else "/accounts/balance"
            r = await client.get(path)
            if r.is_success:
                return r.json()
            return None
        except Exception as e:
            logger.warning("Relay get_balance failed: %s", e)
            return None

    async def list_transactions(
        self, account_id: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List transactions."""
        if not self.api_key:
            return []
        client = await self._get_client()
        try:
            path = "/transactions"
            params: Dict[str, Any] = {"limit": min(limit, 100)}
            if account_id:
                params["account_id"] = account_id
            r = await client.get(path, params=params)
            if r.is_success:
                data = r.json()
                return data.get("transactions", data) if isinstance(data, dict) else data
            return []
        except Exception as e:
            logger.warning("Relay list_transactions failed: %s", e)
            return []

    async def create_transfer(
        self,
        from_account_id: str,
        to_account_id: str,
        amount_cents: int,
        memo: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create an internal transfer (amount in cents)."""
        if not self.api_key:
            return None
        client = await self._get_client()
        try:
            body: Dict[str, Any] = {
                "from_account_id": from_account_id,
                "to_account_id": to_account_id,
                "amount_cents": amount_cents,
            }
            if memo:
                body["memo"] = memo
            r = await client.post("/transfers", json=body)
            if r.is_success:
                return r.json()
            return None
        except Exception as e:
            logger.warning("Relay create_transfer failed: %s", e)
            return None

    async def list_cards(self) -> List[Dict[str, Any]]:
        """List cards."""
        if not self.api_key:
            return []
        client = await self._get_client()
        try:
            r = await client.get("/cards")
            if r.is_success:
                data = r.json()
                return data.get("cards", data) if isinstance(data, dict) else data
            return []
        except Exception as e:
            logger.warning("Relay list_cards failed: %s", e)
            return []

    async def health_check(self) -> Dict[str, Any]:
        """Verify connectivity to Relay API."""
        if not self.api_key:
            return {"status": "unconfigured", "error": "Missing RELAY_API_KEY"}
        try:
            client = await self._get_client()
            r = await client.get("/accounts")
            if r.is_success:
                return {"status": "healthy"}
            return {"status": "unhealthy", "error": r.text[:200]}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
