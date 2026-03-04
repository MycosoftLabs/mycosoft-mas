"""
SAM.gov Integration Client.

Contract Opportunities API, Entity Management, CAGE/DUNS lookup.
Public tier: 10 req/day with API key; Entity User: 1000 req/day after registration.

Environment Variables:
    SAM_GOV_API_KEY: SAM.gov API key (optional for limited public access)
    SAM_GOV_BASE_URL: Override base URL (default: https://api.sam.gov)
"""

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

DEFAULT_BASE = "https://api.sam.gov"


class SamGovClient:
    """Client for SAM.gov Contract Opportunities and Entity Management."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.api_key = (
            self.config.get("api_key") or os.environ.get("SAM_GOV_API_KEY", "")
        )
        self.base_url = (
            self.config.get("base_url") or os.environ.get("SAM_GOV_BASE_URL", DEFAULT_BASE)
        ).rstrip("/")
        self.timeout = self.config.get("timeout", 30)
        self._client: Optional[httpx.AsyncClient] = None

    def _is_configured(self) -> bool:
        return bool(self.api_key)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            params = {}
            if self.api_key:
                params["api_key"] = self.api_key
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                params=params,
                timeout=self.timeout,
                headers={"Accept": "application/json"},
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def search_opportunities(
        self,
        keyword: Optional[str] = None,
        posted_from: Optional[str] = None,
        posted_to: Optional[str] = None,
        notice_type: Optional[str] = None,
        set_aside: Optional[str] = None,
        limit: int = 25,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Search Contract Opportunities. Requires API key."""
        if not self._is_configured():
            return {
                "status": "not_configured",
                "message": "SAM_GOV_API_KEY required for search",
                "opportunities": [],
            }
        try:
            client = await self._get_client()
            params: Dict[str, Any] = {"limit": limit, "offset": offset}
            if keyword:
                params["q"] = keyword
            if posted_from:
                params["postedFrom"] = posted_from
            if posted_to:
                params["postedTo"] = posted_to
            if notice_type:
                params["noticeType"] = notice_type
            if set_aside:
                params["setAside"] = set_aside
            params["api_key"] = self.api_key

            url = f"{self.base_url}/prod/opportunity/v2/search"
            r = await client.get(url, params=params)
            if r.is_success:
                data = r.json()
                return {
                    "status": "success",
                    "opportunities": data.get("opportunitiesData", []),
                    "total": data.get("totalRecords", 0),
                }
            return {
                "status": "error",
                "status_code": r.status_code,
                "detail": r.text[:500],
                "opportunities": [],
            }
        except Exception as e:
            logger.warning("SAM.gov search_opportunities failed: %s", e)
            return {"status": "error", "error": str(e), "opportunities": []}

    async def get_opportunity_by_id(self, opportunity_id: str) -> Dict[str, Any]:
        """Get a single opportunity by ID."""
        if not self._is_configured():
            return {"status": "not_configured", "message": "SAM_GOV_API_KEY required"}
        try:
            client = await self._get_client()
            url = f"{self.base_url}/prod/opportunity/v2/opportunity/{opportunity_id}"
            r = await client.get(url, params={"api_key": self.api_key})
            if r.is_success:
                return {"status": "success", "data": r.json()}
            return {"status": "error", "status_code": r.status_code, "detail": r.text[:500]}
        except Exception as e:
            logger.warning("SAM.gov get_opportunity_by_id failed: %s", e)
            return {"status": "error", "error": str(e)}

    async def entity_lookup(
        self, uei: Optional[str] = None, cage: Optional[str] = None
    ) -> Dict[str, Any]:
        """Look up entity by UEI or CAGE code."""
        if not self._is_configured():
            return {"status": "not_configured", "message": "SAM_GOV_API_KEY required"}
        if not uei and not cage:
            return {"status": "error", "message": "Provide uei or cage"}
        try:
            client = await self._get_client()
            params: Dict[str, Any] = {"api_key": self.api_key}
            if uei:
                params["ueiSAM"] = uei
            if cage:
                params["cageCode"] = cage
            r = await client.get(f"{self.base_url}/prod/entities", params=params)
            if r.is_success:
                return {"status": "success", "data": r.json()}
            return {"status": "error", "status_code": r.status_code, "detail": r.text[:500]}
        except Exception as e:
            logger.warning("SAM.gov entity_lookup failed: %s", e)
            return {"status": "error", "error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        """Check SAM.gov API connectivity."""
        return {
            "status": "configured" if self._is_configured() else "not_configured",
            "base_url": self.base_url,
            "has_api_key": bool(self.api_key),
        }
