"""
Crypto Tax / Accounting Client

Provides access to crypto tax reporting services:
- CoinTracker -- portfolio tracking, tax reports
- TaxBit -- enterprise crypto tax compliance
- Manual transaction aggregation and cost-basis calculation

Env vars:
    COINTRACKER_API_KEY    -- CoinTracker API key
    TAXBIT_API_KEY         -- TaxBit API key
"""

import logging
import os
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

COINTRACKER_BASE = "https://api.cointracker.io/v1"
TAXBIT_BASE = "https://api.taxbit.com/v1"


class CryptoTaxClient:
    """Crypto tax and accounting client."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.cointracker_key = self.config.get("cointracker_api_key") or os.getenv(
            "COINTRACKER_API_KEY", ""
        )
        self.taxbit_key = self.config.get("taxbit_api_key") or os.getenv("TAXBIT_API_KEY", "")
        self.timeout = self.config.get("timeout", 30)
        self._client: Optional[httpx.AsyncClient] = None

    async def _http(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def health_check(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "cointracker_key_set": bool(self.cointracker_key),
            "taxbit_key_set": bool(self.taxbit_key),
            "ts": datetime.utcnow().isoformat(),
        }

    # -- CoinTracker ----------------------------------------------------------

    async def cointracker_portfolio(self) -> Dict[str, Any]:
        """Get portfolio summary from CoinTracker."""
        c = await self._http()
        r = await c.get(
            f"{COINTRACKER_BASE}/portfolio",
            headers={"Authorization": f"Bearer {self.cointracker_key}"},
        )
        r.raise_for_status()
        return r.json()

    async def cointracker_transactions(self, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        """Get transaction history from CoinTracker."""
        c = await self._http()
        r = await c.get(
            f"{COINTRACKER_BASE}/transactions",
            headers={"Authorization": f"Bearer {self.cointracker_key}"},
            params={"page": page, "per_page": per_page},
        )
        r.raise_for_status()
        return r.json()

    async def cointracker_tax_report(self, year: int = 2025) -> Dict[str, Any]:
        """Get tax report summary from CoinTracker."""
        c = await self._http()
        r = await c.get(
            f"{COINTRACKER_BASE}/tax-reports/{year}",
            headers={"Authorization": f"Bearer {self.cointracker_key}"},
        )
        r.raise_for_status()
        return r.json()

    async def cointracker_gains(self, year: int = 2025) -> Dict[str, Any]:
        """Get capital gains summary."""
        c = await self._http()
        r = await c.get(
            f"{COINTRACKER_BASE}/gains",
            headers={"Authorization": f"Bearer {self.cointracker_key}"},
            params={"year": year},
        )
        r.raise_for_status()
        return r.json()

    # -- TaxBit ---------------------------------------------------------------

    async def taxbit_accounts(self) -> Dict[str, Any]:
        """List connected accounts in TaxBit."""
        c = await self._http()
        r = await c.get(
            f"{TAXBIT_BASE}/accounts",
            headers={"Authorization": f"Bearer {self.taxbit_key}"},
        )
        r.raise_for_status()
        return r.json()

    async def taxbit_transactions(
        self, account_id: Optional[str] = None, limit: int = 50
    ) -> Dict[str, Any]:
        """Get transactions from TaxBit."""
        c = await self._http()
        params: Dict[str, Any] = {"limit": limit}
        if account_id:
            params["account_id"] = account_id
        r = await c.get(
            f"{TAXBIT_BASE}/transactions",
            headers={"Authorization": f"Bearer {self.taxbit_key}"},
            params=params,
        )
        r.raise_for_status()
        return r.json()

    async def taxbit_tax_forms(self, year: int = 2025) -> Dict[str, Any]:
        """Get tax forms (8949, etc.) from TaxBit."""
        c = await self._http()
        r = await c.get(
            f"{TAXBIT_BASE}/tax-forms",
            headers={"Authorization": f"Bearer {self.taxbit_key}"},
            params={"year": year},
        )
        r.raise_for_status()
        return r.json()

    # -- Local Cost Basis Calculation -----------------------------------------

    @staticmethod
    def calculate_fifo_gains(
        transactions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Calculate capital gains using FIFO method from a list of transactions.
        Each transaction: {"type": "buy"|"sell", "asset": "SOL", "amount": 10.0, "price_usd": 150.0, "date": "2025-01-15"}
        """
        lots: Dict[str, List] = defaultdict(list)
        gains = []
        total_gain = 0.0

        sorted_txs = sorted(transactions, key=lambda x: x.get("date", ""))

        for tx in sorted_txs:
            asset = tx.get("asset", "")
            amount = tx.get("amount", 0.0)
            price = tx.get("price_usd", 0.0)
            tx_type = tx.get("type", "")
            date = tx.get("date", "")

            if tx_type == "buy":
                lots[asset].append({"amount": amount, "price": price, "date": date})
            elif tx_type == "sell":
                remaining = amount
                proceeds = amount * price
                cost_basis = 0.0

                while remaining > 0 and lots[asset]:
                    lot = lots[asset][0]
                    used = min(remaining, lot["amount"])
                    cost_basis += used * lot["price"]
                    lot["amount"] -= used
                    remaining -= used
                    if lot["amount"] <= 0:
                        lots[asset].pop(0)

                gain = proceeds - cost_basis
                total_gain += gain
                gains.append(
                    {
                        "asset": asset,
                        "amount": amount,
                        "proceeds": round(proceeds, 2),
                        "cost_basis": round(cost_basis, 2),
                        "gain": round(gain, 2),
                        "date": date,
                    }
                )

        return {
            "method": "FIFO",
            "total_gain_usd": round(total_gain, 2),
            "transactions_processed": len(gains),
            "gains": gains,
        }

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
