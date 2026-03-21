"""
SBIR.gov Integration Client.

SBIR/STTR solicitation, awards, and firm search.
Public API - no authentication required.

Environment Variables:
    SBIR_BASE_URL: Override base URL (default: https://api.www.sbir.gov/public/api)
"""

import logging
import os
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

DEFAULT_BASE = "https://api.www.sbir.gov/public/api"

VALID_AGENCIES = frozenset(
    {
        "DHS",
        "DOT",
        "ED",
        "DOC",
        "EPA",
        "USDA",
        "DOE",
        "NSF",
        "NASA",
        "HHS",
        "DOD",
    }
)


class SbirClient:
    """Client for SBIR.gov solicitations and awards."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.base_url = (
            self.config.get("base_url") or os.environ.get("SBIR_BASE_URL", DEFAULT_BASE)
        ).rstrip("/")
        self.timeout = self.config.get("timeout", 30)
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"Accept": "application/json"},
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def search_solicitations(
        self,
        keyword: Optional[str] = None,
        agency: Optional[str] = None,
        open_only: bool = False,
        closed_only: bool = False,
        rows: int = 25,
        start: int = 0,
    ) -> Dict[str, Any]:
        """
        Search SBIR/STTR solicitations.
        GET /solicitations?keyword=...&agency=...&open=1&rows=25&start=0
        """
        try:
            client = await self._get_client()
            params: Dict[str, Any] = {"rows": min(rows, 50), "start": start}
            if keyword:
                params["keyword"] = keyword
            if agency and agency.upper() in VALID_AGENCIES:
                params["agency"] = agency.upper()
            if open_only:
                params["open"] = 1
            if closed_only:
                params["closed"] = 1

            r = await client.get("/solicitations", params=params)
            if r.is_success:
                data = r.json()
                items = (
                    data
                    if isinstance(data, list)
                    else data.get("solicitations", data.get("data", []))
                )
                return {"status": "success", "solicitations": items, "count": len(items)}
            return {
                "status": "error",
                "status_code": r.status_code,
                "solicitations": [],
                "count": 0,
            }
        except Exception as e:
            logger.warning("SBIR search_solicitations failed: %s", e)
            return {"status": "error", "error": str(e), "solicitations": [], "count": 0}

    async def get_open_solicitations(
        self, agency: Optional[str] = None, rows: int = 25
    ) -> Dict[str, Any]:
        """Get all open solicitations."""
        return await self.search_solicitations(agency=agency, open_only=True, rows=rows, start=0)

    async def get_closed_solicitations(
        self, agency: Optional[str] = None, rows: int = 25
    ) -> Dict[str, Any]:
        """Get all closed solicitations."""
        return await self.search_solicitations(agency=agency, closed_only=True, rows=rows, start=0)

    async def search_awards(
        self,
        agency: Optional[str] = None,
        company: Optional[str] = None,
        year: Optional[int] = None,
        limit: int = 25,
    ) -> Dict[str, Any]:
        """
        Search SBIR/STTR awards.
        GET /awards with agency, company, year params.
        """
        try:
            client = await self._get_client()
            params: Dict[str, Any] = {}
            if agency:
                params["agency"] = agency
            if company:
                params["company"] = company
            if year:
                params["year"] = year
            params["limit"] = limit

            r = await client.get("/awards", params=params)
            if r.is_success:
                data = r.json()
                items = data if isinstance(data, list) else data.get("awards", data.get("data", []))
                return {"status": "success", "awards": items, "count": len(items)}
            return {"status": "error", "status_code": r.status_code, "awards": [], "count": 0}
        except Exception as e:
            logger.warning("SBIR search_awards failed: %s", e)
            return {"status": "error", "error": str(e), "awards": [], "count": 0}

    async def search_firms(self, query: str, limit: int = 25) -> Dict[str, Any]:
        """Search firms that have won SBIR/STTR awards."""
        try:
            client = await self._get_client()
            r = await client.get("/firm", params={"q": query, "limit": limit})
            if r.is_success:
                data = r.json()
                items = data if isinstance(data, list) else data.get("firms", data.get("data", []))
                return {"status": "success", "firms": items, "count": len(items)}
            return {"status": "error", "status_code": r.status_code, "firms": [], "count": 0}
        except Exception as e:
            logger.warning("SBIR search_firms failed: %s", e)
            return {"status": "error", "error": str(e), "firms": [], "count": 0}

    async def health_check(self) -> Dict[str, Any]:
        """Check SBIR.gov API connectivity."""
        try:
            r = await self.search_solicitations(keyword="sbir", rows=1)
            return {
                "status": "connected" if r.get("status") == "success" else "error",
                "base_url": self.base_url,
            }
        except Exception as e:
            return {"status": "error", "error": str(e), "base_url": self.base_url}
