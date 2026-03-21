"""
Stripe Integration Client.

Payment processing, subscriptions, invoicing, customer management.
Used by FinancialOperationsAgent and business automation.

Environment Variables:
    STRIPE_SECRET_KEY: Secret key from Stripe Dashboard
    STRIPE_WEBHOOK_SECRET: Webhook signing secret (optional)
"""

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

STRIPE_API_BASE = "https://api.stripe.com/v1"


class StripeClient:
    """Client for Stripe REST API."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.secret_key = self.config.get("secret_key", os.environ.get("STRIPE_SECRET_KEY", ""))
        self.webhook_secret = self.config.get(
            "webhook_secret", os.environ.get("STRIPE_WEBHOOK_SECRET", "")
        )
        self.timeout = self.config.get("timeout", 30)
        self._client: Optional[httpx.AsyncClient] = None

    def _auth(self) -> Optional[httpx.BasicAuth]:
        if not self.secret_key:
            return None
        return httpx.BasicAuth(self.secret_key, "")

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=STRIPE_API_BASE,
                auth=self._auth(),
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def _form_encode(self, data: Dict[str, Any]) -> Dict[str, str]:
        out: Dict[str, str] = {}
        for k, v in data.items():
            if v is None:
                continue
            if isinstance(v, dict):
                for sk, sv in v.items():
                    out[f"{k}[{sk}]"] = str(sv)
            elif isinstance(v, list):
                for i, item in enumerate(v):
                    if isinstance(item, dict):
                        for sk, sv in item.items():
                            out[f"{k}[{i}][{sk}]"] = str(sv)
                    else:
                        out[f"{k}[{i}]"] = str(item)
            else:
                out[k] = str(v)
        return out

    async def create_payment_intent(
        self,
        amount: int,
        currency: str = "usd",
        customer: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a PaymentIntent (amount in cents)."""
        if not self.secret_key:
            return None
        client = await self._get_client()
        data: Dict[str, Any] = {"amount": amount, "currency": currency}
        if customer:
            data["customer"] = customer
        if metadata:
            data["metadata"] = metadata
        try:
            r = await client.post("payment_intents", data=self._form_encode(data))
            if r.is_success:
                return r.json()
            return None
        except Exception as e:
            logger.warning("Stripe create_payment_intent failed: %s", e)
            return None

    async def list_customers(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List customers."""
        if not self.secret_key:
            return []
        client = await self._get_client()
        try:
            r = await client.get("customers", params={"limit": min(limit, 100)})
            if r.is_success:
                return r.json().get("data", [])
            return []
        except Exception as e:
            logger.warning("Stripe list_customers failed: %s", e)
            return []

    async def list_subscriptions(
        self, customer: Optional[str] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """List subscriptions."""
        if not self.secret_key:
            return []
        client = await self._get_client()
        params: Dict[str, Any] = {"limit": min(limit, 100)}
        if customer:
            params["customer"] = customer
        try:
            r = await client.get("subscriptions", params=params)
            if r.is_success:
                return r.json().get("data", [])
            return []
        except Exception as e:
            logger.warning("Stripe list_subscriptions failed: %s", e)
            return []

    async def list_invoices(
        self, customer: Optional[str] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """List invoices."""
        if not self.secret_key:
            return []
        client = await self._get_client()
        params: Dict[str, Any] = {"limit": min(limit, 100)}
        if customer:
            params["customer"] = customer
        try:
            r = await client.get("invoices", params=params)
            if r.is_success:
                return r.json().get("data", [])
            return []
        except Exception as e:
            logger.warning("Stripe list_invoices failed: %s", e)
            return []

    async def create_invoice(
        self,
        customer: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a draft invoice."""
        if not self.secret_key:
            return None
        client = await self._get_client()
        data: Dict[str, Any] = {"customer": customer}
        if description:
            data["description"] = description
        if metadata:
            data["metadata"] = metadata
        try:
            r = await client.post("invoices", data=self._form_encode(data))
            if r.is_success:
                return r.json()
            return None
        except Exception as e:
            logger.warning("Stripe create_invoice failed: %s", e)
            return None

    async def retrieve_checkout_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a Checkout Session by ID (e.g. cs_xxx). Used to verify payment and read metadata."""
        if not self.secret_key or not session_id:
            return None
        client = await self._get_client()
        try:
            r = await client.get(f"checkout/sessions/{session_id}")
            if r.is_success:
                return r.json()
            return None
        except Exception as e:
            logger.warning("Stripe retrieve_checkout_session failed: %s", e)
            return None

    async def health_check(self) -> Dict[str, Any]:
        """Verify connectivity to Stripe API."""
        if not self.secret_key:
            return {"status": "unconfigured", "error": "Missing STRIPE_SECRET_KEY"}
        try:
            client = await self._get_client()
            r = await client.get("balance")
            if r.is_success:
                return {"status": "healthy"}
            return {"status": "unhealthy", "error": r.text[:200]}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
