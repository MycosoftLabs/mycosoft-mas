"""
PayPal Integration Client.

Payments, invoicing, mass payouts, subscription management.
Used by FinancialOperationsAgent and business automation.

Environment Variables:
    PAYPAL_CLIENT_ID: Client ID from PayPal Developer Dashboard
    PAYPAL_CLIENT_SECRET: Client secret
"""

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

PAYPAL_API_BASE_SANDBOX = "https://api-m.sandbox.paypal.com"
PAYPAL_API_BASE_LIVE = "https://api-m.paypal.com"


class PayPalClient:
    """Client for PayPal REST API."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.client_id = self.config.get(
            "client_id", os.environ.get("PAYPAL_CLIENT_ID", "")
        )
        self.client_secret = self.config.get(
            "client_secret", os.environ.get("PAYPAL_CLIENT_SECRET", "")
        )
        self.sandbox = self.config.get("sandbox", True)
        self.base_url = (
            PAYPAL_API_BASE_SANDBOX if self.sandbox else PAYPAL_API_BASE_LIVE
        )
        self.timeout = self.config.get("timeout", 30)
        self._client: Optional[httpx.AsyncClient] = None
        self._access_token: Optional[str] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client

    async def _ensure_token(self) -> bool:
        if self._access_token:
            return True
        if not self.client_id or not self.client_secret:
            return False
        client = await self._get_client()
        try:
            r = await client.post(
                "/v1/oauth2/token",
                data={"grant_type": "client_credentials"},
                auth=(self.client_id, self.client_secret),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if r.is_success:
                data = r.json()
                self._access_token = data.get("access_token")
                return bool(self._access_token)
            return False
        except Exception as e:
            logger.warning("PayPal auth failed: %s", e)
            return False

    def _headers(self) -> Dict[str, str]:
        h: Dict[str, str] = {"Content-Type": "application/json"}
        if self._access_token:
            h["Authorization"] = f"Bearer {self._access_token}"
        return h

    async def close(self) -> None:
        self._access_token = None
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def create_order(
        self,
        amount: str,
        currency: str = "USD",
        description: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create an order (amount as string, e.g. '10.00')."""
        if not await self._ensure_token():
            return None
        client = await self._get_client()
        body = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "amount": {"currency_code": currency, "value": amount},
                    "description": description or "",
                }
            ],
        }
        try:
            r = await client.post(
                "/v2/checkout/orders",
                json=body,
                headers=self._headers(),
            )
            if r.is_success:
                return r.json()
            return None
        except Exception as e:
            logger.warning("PayPal create_order failed: %s", e)
            return None

    async def list_invoices(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List invoices."""
        if not await self._ensure_token():
            return []
        client = await self._get_client()
        try:
            r = await client.get(
                "/v2/invoicing/invoices",
                params={"page_size": min(limit, 20)},
                headers=self._headers(),
            )
            if r.is_success:
                return r.json().get("items", [])
            return []
        except Exception as e:
            logger.warning("PayPal list_invoices failed: %s", e)
            return []

    async def create_invoice(
        self,
        recipient_email: str,
        amount: str,
        currency: str = "USD",
        description: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a draft invoice."""
        if not await self._ensure_token():
            return None
        client = await self._get_client()
        body = {
            "detail": {"currency_code": currency, "note": description or ""},
            "invoicer": {},
            "primary_recipients": [
                {
                    "billing_info": {"email_address": recipient_email},
                    "shipping_info": {"name": {"full_name": ""}},
                }
            ],
            "items": [
                {
                    "name": description or "Item",
                    "quantity": "1",
                    "unit_amount": {"currency_code": currency, "value": amount},
                }
            ],
        }
        try:
            r = await client.post(
                "/v2/invoicing/invoices",
                json=body,
                headers=self._headers(),
            )
            if r.is_success:
                return r.json()
            return None
        except Exception as e:
            logger.warning("PayPal create_invoice failed: %s", e)
            return None

    async def health_check(self) -> Dict[str, Any]:
        """Verify connectivity to PayPal API."""
        if not self.client_id or not self.client_secret:
            return {"status": "unconfigured", "error": "Missing PayPal credentials"}
        if await self._ensure_token():
            return {"status": "healthy"}
        return {"status": "unhealthy", "error": "Failed to obtain access token"}
