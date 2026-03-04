"""
Fiat On/Off Ramp Client

Provides access to crypto-to-fiat and fiat-to-crypto services:
- MoonPay -- buy/sell crypto with fiat (cards, bank transfers)
- Transak -- fiat on-ramp with global coverage

Env vars:
    MOONPAY_API_KEY        -- MoonPay API key
    MOONPAY_SECRET_KEY     -- MoonPay secret key (for server-side signing)
    TRANSAK_API_KEY        -- Transak API key
"""

import os
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

MOONPAY_BASE = "https://api.moonpay.com/v3"
TRANSAK_BASE = "https://api.transak.com/api/v2"


class FiatRampClient:
    """Multi-provider fiat on/off ramp client."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.moonpay_key = self.config.get("moonpay_api_key") or os.getenv("MOONPAY_API_KEY", "")
        self.moonpay_secret = self.config.get("moonpay_secret_key") or os.getenv("MOONPAY_SECRET_KEY", "")
        self.transak_key = self.config.get("transak_api_key") or os.getenv("TRANSAK_API_KEY", "")
        self.timeout = self.config.get("timeout", 30)
        self._client: Optional[httpx.AsyncClient] = None

    async def _http(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def health_check(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "moonpay_key_set": bool(self.moonpay_key),
            "transak_key_set": bool(self.transak_key),
            "ts": datetime.utcnow().isoformat(),
        }

    # -- MoonPay --------------------------------------------------------------

    async def moonpay_currencies(self) -> List[Dict[str, Any]]:
        """List supported cryptocurrencies on MoonPay."""
        c = await self._http()
        r = await c.get(
            f"{MOONPAY_BASE}/currencies",
            params={"apiKey": self.moonpay_key},
        )
        r.raise_for_status()
        return r.json()

    async def moonpay_price(self, currency: str = "sol", fiat: str = "usd") -> Dict[str, Any]:
        """Get buy/sell price quote from MoonPay."""
        c = await self._http()
        r = await c.get(
            f"{MOONPAY_BASE}/currencies/{currency}/price",
            params={"apiKey": self.moonpay_key, "baseCurrencyCode": fiat},
        )
        r.raise_for_status()
        return r.json()

    async def moonpay_buy_quote(
        self,
        currency: str = "sol",
        fiat_amount: float = 100.0,
        fiat_currency: str = "usd",
    ) -> Dict[str, Any]:
        """Get a buy quote from MoonPay."""
        c = await self._http()
        r = await c.get(
            f"{MOONPAY_BASE}/currencies/{currency}/buy_quote",
            params={
                "apiKey": self.moonpay_key,
                "baseCurrencyAmount": fiat_amount,
                "baseCurrencyCode": fiat_currency,
            },
        )
        r.raise_for_status()
        return r.json()

    async def moonpay_sell_quote(
        self,
        currency: str = "sol",
        crypto_amount: float = 1.0,
        fiat_currency: str = "usd",
    ) -> Dict[str, Any]:
        """Get a sell quote from MoonPay."""
        c = await self._http()
        r = await c.get(
            f"{MOONPAY_BASE}/currencies/{currency}/sell_quote",
            params={
                "apiKey": self.moonpay_key,
                "baseCurrencyAmount": crypto_amount,
                "quoteCurrencyCode": fiat_currency,
            },
        )
        r.raise_for_status()
        return r.json()

    async def moonpay_countries(self) -> List[Dict[str, Any]]:
        """List supported countries on MoonPay."""
        c = await self._http()
        r = await c.get(
            f"{MOONPAY_BASE}/countries",
            params={"apiKey": self.moonpay_key},
        )
        r.raise_for_status()
        return r.json()

    # -- Transak --------------------------------------------------------------

    async def transak_cryptocurrencies(self) -> Dict[str, Any]:
        """List supported cryptocurrencies on Transak."""
        c = await self._http()
        r = await c.get(
            f"{TRANSAK_BASE}/currencies/crypto-currencies",
            headers={"access-token": self.transak_key},
        )
        r.raise_for_status()
        return r.json()

    async def transak_fiat_currencies(self) -> Dict[str, Any]:
        """List supported fiat currencies on Transak."""
        c = await self._http()
        r = await c.get(
            f"{TRANSAK_BASE}/currencies/fiat-currencies",
            headers={"access-token": self.transak_key},
        )
        r.raise_for_status()
        return r.json()

    async def transak_price(
        self,
        fiat: str = "USD",
        crypto: str = "SOL",
        fiat_amount: float = 100.0,
        payment_method: str = "credit_debit_card",
        is_buy: bool = True,
    ) -> Dict[str, Any]:
        """Get a price quote from Transak."""
        c = await self._http()
        r = await c.get(
            f"{TRANSAK_BASE}/currencies/price",
            headers={"access-token": self.transak_key},
            params={
                "fiatCurrency": fiat,
                "cryptoCurrency": crypto,
                "fiatAmount": fiat_amount,
                "paymentMethod": payment_method,
                "isBuyOrSell": "BUY" if is_buy else "SELL",
                "network": "solana",
            },
        )
        r.raise_for_status()
        return r.json()

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
