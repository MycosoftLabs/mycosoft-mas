"""
Coinbase Integration Client.

Buy/sell crypto, portfolio, exchange rates, price alerts.
Used by crypto agents and financial automation.

Environment Variables:
    COINBASE_API_KEY: API key from Coinbase Advanced
    COINBASE_API_SECRET: API secret
"""

import logging
import os
import time
import hmac
import hashlib
import base64
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

COINBASE_API_BASE = "https://api.coinbase.com/api/v3/brokerage"


class CoinbaseClient:
    """Client for Coinbase Advanced Trade API."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.api_key = self.config.get(
            "api_key", os.environ.get("COINBASE_API_KEY", "")
        )
        self.api_secret = self.config.get(
            "api_secret", os.environ.get("COINBASE_API_SECRET", "")
        )
        self.timeout = self.config.get("timeout", 30)
        self._client: Optional[httpx.AsyncClient] = None

    def _sign(self, method: str, path: str, body: str = "") -> Dict[str, str]:
        """Generate Coinbase API v3 signature."""
        timestamp = str(int(time.time()))
        message = timestamp + method.upper() + path + body
        sig = hmac.new(
            self.api_secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).digest()
        return {
            "CB-ACCESS-KEY": self.api_key,
            "CB-ACCESS-SIGN": base64.b64encode(sig).decode(),
            "CB-ACCESS-TIMESTAMP": timestamp,
            "Content-Type": "application/json",
        }

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=COINBASE_API_BASE,
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def get_accounts(self) -> List[Dict[str, Any]]:
        """List trading accounts (portfolios)."""
        if not self.api_key or not self.api_secret:
            return []
        client = await self._get_client()
        path = "/accounts"
        headers = self._sign("GET", path)
        try:
            r = await client.get(path, headers=headers)
            if r.is_success:
                data = r.json()
                return data.get("accounts", [])
            return []
        except Exception as e:
            logger.warning("Coinbase get_accounts failed: %s", e)
            return []

    async def get_products(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List traded products (pairs)."""
        client = await self._get_client()
        try:
            r = await client.get(
                "https://api.exchange.coinbase.com/products",
                params={"limit": min(limit, 100)},
            )
            if r.is_success:
                return r.json()
            return []
        except Exception as e:
            logger.warning("Coinbase get_products failed: %s", e)
            return []

    async def get_product_ticker(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Get 24h ticker for a product (e.g. BTC-USD)."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as c:
                r = await c.get(
                    f"https://api.exchange.coinbase.com/products/{product_id}/ticker"
                )
                if r.is_success:
                    return r.json()
            return None
        except Exception as e:
            logger.warning("Coinbase get_product_ticker failed: %s", e)
            return None

    async def get_exchange_rates(self, currency: str = "USD") -> Optional[Dict[str, Any]]:
        """Get exchange rates (public, no auth)."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as c:
                r = await c.get(
                    f"https://api.coinbase.com/v2/exchange-rates",
                    params={"currency": currency},
                )
                if r.is_success:
                    return r.json()
            return None
        except Exception as e:
            logger.warning("Coinbase get_exchange_rates failed: %s", e)
            return None

    async def health_check(self) -> Dict[str, Any]:
        """Verify connectivity to Coinbase API."""
        try:
            rates = await self.get_exchange_rates()
            if rates and "data" in rates:
                return {"status": "healthy"}
            return {"status": "unhealthy", "error": "No rates"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
