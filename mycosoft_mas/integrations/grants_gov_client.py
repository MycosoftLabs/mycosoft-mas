"""
Grants.gov Integration Client.

Public REST API for grant opportunity search and retrieval.
No authentication required.

Environment Variables:
    GRANTS_GOV_BASE_URL: Override base URL (default: https://api.grants.gov)
"""

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

DEFAULT_BASE = "https://api.grants.gov"


class GrantsGovClient:
    """Client for Grants.gov opportunity search and fetch."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.base_url = (
            self.config.get("base_url") or os.environ.get("GRANTS_GOV_BASE_URL", DEFAULT_BASE)
        ).rstrip("/")
        self.timeout = self.config.get("timeout", 30)
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def search(
        self,
        keyword: Optional[str] = None,
        opp_statuses: Optional[List[str]] = None,
        agencies: Optional[List[str]] = None,
        funding_categories: Optional[List[str]] = None,
        rows: int = 10,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Search grant opportunities via Search2 API.
        POST https://api.grants.gov/v1/api/search2
        """
        try:
            client = await self._get_client()
            payload: Dict[str, Any] = {"rows": rows, "offset": offset}
            if keyword:
                payload["keyword"] = keyword
            if opp_statuses:
                payload["oppStatuses"] = "|".join(opp_statuses)  # forecasted|posted|closed
            if agencies:
                payload["agencies"] = "|".join(agencies)
            if funding_categories:
                payload["fundingCategories"] = "|".join(funding_categories)

            url = f"{self.base_url}/v1/api/search2"
            r = await client.post(url, json=payload)
            if r.is_success:
                data = r.json()
                return {
                    "status": "success",
                    "hitCount": data.get("hitCount", 0),
                    "opportunities": data.get("opportunities", []),
                    "filterOptions": data.get("filterOptions", {}),
                }
            return {
                "status": "error",
                "status_code": r.status_code,
                "detail": r.text[:500],
                "opportunities": [],
                "hitCount": 0,
            }
        except Exception as e:
            logger.warning("Grants.gov search failed: %s", e)
            return {"status": "error", "error": str(e), "opportunities": [], "hitCount": 0}

    async def fetch_opportunity(self, opportunity_id: str) -> Dict[str, Any]:
        """
        Fetch detailed opportunity by ID.
        POST https://api.grants.gov/v1/api/fetchOpportunity
        """
        try:
            client = await self._get_client()
            url = f"{self.base_url}/v1/api/fetchOpportunity"
            r = await client.post(url, json={"opportunityId": opportunity_id})
            if r.is_success:
                data = r.json()
                return {"status": "success", "data": data}
            return {"status": "error", "status_code": r.status_code, "detail": r.text[:500]}
        except Exception as e:
            logger.warning("Grants.gov fetch_opportunity failed: %s", e)
            return {"status": "error", "error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        """Check Grants.gov API connectivity (no auth required)."""
        try:
            client = await self._get_client()
            r = await client.get("/v1/api/health", timeout=10)
            return {
                "status": "connected" if r.is_success else "error",
                "base_url": self.base_url,
                "status_code": r.status_code,
            }
        except Exception as e:
            return {"status": "error", "error": str(e), "base_url": self.base_url}
