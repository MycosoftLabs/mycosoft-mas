"""
QuickBooks Online Integration Client.

Invoicing, expenses, P&L reports, payroll, bank reconciliation.
Used by FinancialOperationsAgent and CFOAgent.

Environment Variables:
    QUICKBOOKS_CLIENT_ID: OAuth2 client ID from Intuit Developer
    QUICKBOOKS_CLIENT_SECRET: OAuth2 client secret
    QUICKBOOKS_REALM_ID: Company/realm ID (e.g. 1234567890)
    QUICKBOOKS_ACCESS_TOKEN: OAuth2 access token (or use refresh)
    QUICKBOOKS_REFRESH_TOKEN: OAuth2 refresh token for token refresh
"""

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

QB_API_BASE = "https://quickbooks.api.intuit.com/v3"
QB_TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"


class QuickBooksClient:
    """Client for QuickBooks Online REST API."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.client_id = self.config.get("client_id", os.environ.get("QUICKBOOKS_CLIENT_ID", ""))
        self.client_secret = self.config.get(
            "client_secret", os.environ.get("QUICKBOOKS_CLIENT_SECRET", "")
        )
        self.realm_id = self.config.get("realm_id", os.environ.get("QUICKBOOKS_REALM_ID", ""))
        self.access_token = self.config.get(
            "access_token", os.environ.get("QUICKBOOKS_ACCESS_TOKEN", "")
        )
        self.refresh_token = self.config.get(
            "refresh_token", os.environ.get("QUICKBOOKS_REFRESH_TOKEN", "")
        )
        self.timeout = self.config.get("timeout", 30)
        self._client: Optional[httpx.AsyncClient] = None

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=f"{QB_API_BASE}/company/{self.realm_id}",
                headers=self._headers(),
                timeout=self.timeout,
            )
        return self._client

    async def _ensure_token(self) -> None:
        """Refresh access token if needed (simplified; production would check expiry)."""
        if not self.access_token and self.refresh_token and self.client_id and self.client_secret:
            async with httpx.AsyncClient() as c:
                r = await c.post(
                    QB_TOKEN_URL,
                    auth=(self.client_id, self.client_secret),
                    data={"grant_type": "refresh_token", "refresh_token": self.refresh_token},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                if r.is_success:
                    data = r.json()
                    self.access_token = data.get("access_token", "")
                    if self._client:
                        self._client.headers["Authorization"] = f"Bearer {self.access_token}"

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _query(self, sql: str) -> List[Dict[str, Any]]:
        """Execute a QuickBooks SQL-like query. Returns list of entities."""
        if not self.access_token or not self.realm_id:
            logger.warning("QuickBooks client: missing QUICKBOOKS_ACCESS_TOKEN or QUICKBOOKS_REALM_ID")
            return []
        await self._ensure_token()
        client = await self._get_client()
        try:
            r = await client.get("/query", params={"query": sql, "minorversion": 65})
            r.raise_for_status()
            data = r.json()
            qr = data.get("QueryResponse", {})
            for key, val in qr.items():
                if isinstance(val, list):
                    return val
                if isinstance(val, dict):
                    return [val]
            return []
        except Exception as e:
            logger.warning("QuickBooks query failed: %s", e)
            return []

    async def list_invoices(
        self, limit: int = 20, offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List invoices."""
        if not self.access_token or not self.realm_id:
            return []
        await self._ensure_token()
        client = await self._get_client()
        try:
            r = await client.get(
                "/invoice",
                params={"minorversion": 65, "startposition": offset, "maxresults": limit},
            )
            r.raise_for_status()
            data = r.json()
            return data.get("QueryResponse", {}).get("Invoice", [])
        except Exception as e:
            logger.warning("QuickBooks list_invoices failed: %s", e)
            return []

    async def create_invoice(
        self,
        customer_ref: str,
        line_items: List[Dict[str, Any]],
        due_date: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create an invoice."""
        if not self.access_token or not self.realm_id:
            return None
        await self._ensure_token()
        client = await self._get_client()
        body = {
            "CustomerRef": {"value": customer_ref},
            "Line": line_items,
        }
        if due_date:
            body["DueDate"] = due_date
        try:
            r = await client.post("/invoice", json=body, params={"minorversion": 65})
            r.raise_for_status()
            data = r.json()
            return data.get("Invoice")
        except Exception as e:
            logger.warning("QuickBooks create_invoice failed: %s", e)
            return None

    async def list_expenses(
        self, limit: int = 50, start_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List purchase/expense transactions."""
        sql = "SELECT * FROM Purchase"
        if start_date:
            sql += f" WHERE TxnDate >= '{start_date}'"
        sql += f" MAXRESULTS {limit}"
        return await self._query(sql)

    async def get_profit_and_loss(
        self, start_date: str, end_date: str,
    ) -> Optional[Dict[str, Any]]:
        """Get P&L report for date range."""
        if not self.access_token or not self.realm_id:
            return None
        await self._ensure_token()
        client = await self._get_client()
        try:
            r = await client.get(
                "/reports/ProfitAndLoss",
                params={
                    "minorversion": 65,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.warning("QuickBooks P&L failed: %s", e)
            return None

    async def get_balance_sheet(self, as_of_date: str) -> Optional[Dict[str, Any]]:
        """Get balance sheet as of date."""
        if not self.access_token or not self.realm_id:
            return None
        await self._ensure_token()
        client = await self._get_client()
        try:
            r = await client.get(
                "/reports/BalanceSheet",
                params={"minorversion": 65, "accounting_period": as_of_date},
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.warning("QuickBooks BalanceSheet failed: %s", e)
            return None

    async def list_customers(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List customers."""
        if not self.access_token or not self.realm_id:
            return []
        await self._ensure_token()
        client = await self._get_client()
        try:
            r = await client.get(
                "/query",
                params={
                    "query": f"SELECT * FROM Customer MAXRESULTS {limit}",
                    "minorversion": 65,
                },
            )
            r.raise_for_status()
            data = r.json()
            qr = data.get("QueryResponse", {})
            return qr.get("Customer", [])
        except Exception as e:
            logger.warning("QuickBooks list_customers failed: %s", e)
            return []

    async def health_check(self) -> Dict[str, Any]:
        """Verify connectivity to QuickBooks API."""
        if not self.access_token or not self.realm_id:
            return {"status": "unconfigured", "error": "Missing credentials"}
        try:
            await self._ensure_token()
            client = await self._get_client()
            r = await client.get(
                "/query",
                params={"query": "SELECT COUNT(*) FROM Customer", "minorversion": 65},
            )
            if r.is_success:
                return {"status": "healthy"}
            return {"status": "unhealthy", "error": r.text[:200]}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
