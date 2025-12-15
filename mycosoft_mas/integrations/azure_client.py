"""
Azure Integration Client

This client connects to Azure Resource Manager (ARM) using client-credential
flow to perform lightweight management operations such as listing
subscriptions and resource groups. It is intentionally minimal and uses
standard Azure OAuth2 endpoints without adding new dependencies.

Environment Variables:
    AZURE_TENANT_ID: Azure AD tenant ID (required)
    AZURE_CLIENT_ID: Azure application (client) ID (required)
    AZURE_CLIENT_SECRET: Azure application client secret (required)
    AZURE_SUBSCRIPTION_ID: Default subscription ID (optional but recommended)
    AZURE_SCOPE: Optional scope (default: https://management.azure.com/.default)

Typical Usage:
    from mycosoft_mas.integrations.azure_client import AzureClient

    async with AzureClient() as azure:
        health = await azure.health_check()
        rgs = await azure.list_resource_groups()
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import httpx

logger = logging.getLogger(__name__)


class AzureClient:
    """Minimal Azure Resource Manager client using client credentials."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Azure client.

        Args:
            config: Optional configuration dictionary with:
                tenant_id, client_id, client_secret, subscription_id,
                scope, timeout, max_retries
        """
        self.config = config or {}

        # Auth settings
        self.tenant_id = self.config.get("tenant_id") or os.getenv("AZURE_TENANT_ID", "")
        self.client_id = self.config.get("client_id") or os.getenv("AZURE_CLIENT_ID", "")
        self.client_secret = self.config.get("client_secret") or os.getenv("AZURE_CLIENT_SECRET", "")
        self.subscription_id = self.config.get("subscription_id") or os.getenv("AZURE_SUBSCRIPTION_ID", "")
        self.scope = self.config.get("scope") or os.getenv("AZURE_SCOPE", "https://management.azure.com/.default")

        # Connection settings
        self.timeout = self.config.get("timeout", 30)
        self.max_retries = self.config.get("max_retries", 3)

        self._http_client: Optional[httpx.AsyncClient] = None
        self._token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None

        self.logger = logging.getLogger(__name__)
        self.logger.info("Azure client initialized")

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Create or reuse HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=self.timeout, follow_redirects=True)
        return self._http_client

    async def _get_token(self) -> str:
        """Acquire an access token via client credentials."""
        if self._token and self._token_expiry and datetime.utcnow() < self._token_expiry:
            return self._token

        if not all([self.tenant_id, self.client_id, self.client_secret]):
            raise ValueError("Azure credentials missing (tenant_id, client_id, client_secret required)")

        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
            "scope": self.scope,
        }

        client = await self._get_http_client()
        resp = await client.post(token_url, data=data)
        resp.raise_for_status()
        payload = resp.json()

        self._token = payload.get("access_token")
        expires_in = int(payload.get("expires_in", 3600))
        self._token_expiry = datetime.utcnow() + timedelta(seconds=expires_in - 60)

        if not self._token:
            raise RuntimeError("Failed to acquire Azure access token")

        return self._token

    async def _auth_headers(self) -> Dict[str, str]:
        token = await self._get_token()
        return {"Authorization": f"Bearer {token}"}

    async def list_subscriptions(self) -> List[Dict[str, Any]]:
        """List Azure subscriptions for the credential."""
        client = await self._get_http_client()
        headers = await self._auth_headers()
        url = "https://management.azure.com/subscriptions?api-version=2021-01-01"

        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data.get("value", [])

    async def list_resource_groups(self, subscription_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List resource groups for a subscription."""
        sub = subscription_id or self.subscription_id
        if not sub:
            raise ValueError("subscription_id is required")

        client = await self._get_http_client()
        headers = await self._auth_headers()
        url = f"https://management.azure.com/subscriptions/{sub}/resourcegroups?api-version=2021-04-01"

        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data.get("value", [])

    async def health_check(self) -> Dict[str, Any]:
        """Check Azure connectivity by acquiring a token and (optionally) listing resource groups."""
        health = {"status": "unknown", "timestamp": datetime.utcnow().isoformat()}

        try:
            await self._get_token()
            health["token"] = "ok"
        except Exception as e:
            health["status"] = "error"
            health["error"] = f"token: {e}"
            return health

        # If subscription configured, try a lightweight RG list
        if self.subscription_id:
            try:
                await self.list_resource_groups(subscription_id=self.subscription_id)
                health["resource_groups"] = "ok"
                health["status"] = "ok"
            except Exception as e:
                health["status"] = "error"
                health["error"] = f"resource_groups: {e}"
        else:
            health["status"] = "ok"
            health["note"] = "subscription_id not configured; skipped RG check"

        return health

    async def close(self):
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        self.logger.info("Azure client connections closed")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

