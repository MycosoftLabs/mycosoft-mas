"""
Academic / University Data Client

Provides access to scholarly data from:
- OpenAlex (replaces Microsoft Academic Graph) -- works, authors, institutions, concepts
- ORCID -- researcher identifiers, works, affiliations
- DataCite -- DOI registration, dataset discovery
- Crossref -- metadata for published works

All public APIs; ORCID requires token for member endpoints.

Env vars:
    ORCID_CLIENT_ID      -- ORCID public API client ID
    ORCID_CLIENT_SECRET   -- ORCID public API client secret
    OPENALEX_EMAIL        -- polite-pool email for OpenAlex (faster rate limit)
"""

import os
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

OPENALEX_BASE = "https://api.openalex.org"
ORCID_BASE = "https://pub.orcid.org/v3.0"
DATACITE_BASE = "https://api.datacite.org"
CROSSREF_BASE = "https://api.crossref.org"


class AcademicClient:
    """Unified client for academic data sources."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.openalex_email = self.config.get("openalex_email") or os.getenv("OPENALEX_EMAIL", "")
        self.orcid_client_id = self.config.get("orcid_client_id") or os.getenv("ORCID_CLIENT_ID", "")
        self.orcid_client_secret = self.config.get("orcid_client_secret") or os.getenv("ORCID_CLIENT_SECRET", "")
        self.timeout = self.config.get("timeout", 30)
        self._client: Optional[httpx.AsyncClient] = None

    async def _http(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def health_check(self) -> Dict[str, Any]:
        try:
            c = await self._http()
            r = await c.get(f"{OPENALEX_BASE}/works", params={"per_page": 1})
            return {
                "status": "ok" if r.status_code == 200 else "degraded",
                "openalex": r.status_code == 200,
                "ts": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _oa_params(self, extra: Optional[Dict] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if self.openalex_email:
            params["mailto"] = self.openalex_email
        if extra:
            params.update(extra)
        return params

    # -- OpenAlex -------------------------------------------------------------

    async def search_works(
        self,
        query: str,
        per_page: int = 25,
        page: int = 1,
        sort: str = "relevance_score:desc",
    ) -> Dict[str, Any]:
        c = await self._http()
        r = await c.get(
            f"{OPENALEX_BASE}/works",
            params=self._oa_params({"search": query, "per_page": per_page, "page": page, "sort": sort}),
        )
        r.raise_for_status()
        return r.json()

    async def get_work(self, work_id: str) -> Dict[str, Any]:
        """Get a single work by OpenAlex ID (e.g. W2741809807)."""
        c = await self._http()
        r = await c.get(f"{OPENALEX_BASE}/works/{work_id}", params=self._oa_params())
        r.raise_for_status()
        return r.json()

    async def search_authors(self, query: str, per_page: int = 25) -> Dict[str, Any]:
        c = await self._http()
        r = await c.get(
            f"{OPENALEX_BASE}/authors",
            params=self._oa_params({"search": query, "per_page": per_page}),
        )
        r.raise_for_status()
        return r.json()

    async def search_institutions(self, query: str, per_page: int = 25) -> Dict[str, Any]:
        c = await self._http()
        r = await c.get(
            f"{OPENALEX_BASE}/institutions",
            params=self._oa_params({"search": query, "per_page": per_page}),
        )
        r.raise_for_status()
        return r.json()

    async def search_concepts(self, query: str, per_page: int = 25) -> Dict[str, Any]:
        c = await self._http()
        r = await c.get(
            f"{OPENALEX_BASE}/concepts",
            params=self._oa_params({"search": query, "per_page": per_page}),
        )
        r.raise_for_status()
        return r.json()

    async def trending_works(self, concept: str = "mycology", per_page: int = 10) -> Dict[str, Any]:
        c = await self._http()
        r = await c.get(
            f"{OPENALEX_BASE}/works",
            params=self._oa_params({
                "filter": f"concepts.display_name.search:{concept}",
                "sort": "cited_by_count:desc",
                "per_page": per_page,
            }),
        )
        r.raise_for_status()
        return r.json()

    # -- ORCID ----------------------------------------------------------------

    async def orcid_lookup(self, orcid_id: str) -> Dict[str, Any]:
        """Get researcher profile by ORCID iD."""
        c = await self._http()
        r = await c.get(
            f"{ORCID_BASE}/{orcid_id}",
            headers={"Accept": "application/json"},
        )
        r.raise_for_status()
        return r.json()

    async def orcid_works(self, orcid_id: str) -> Dict[str, Any]:
        """Get works for an ORCID iD."""
        c = await self._http()
        r = await c.get(
            f"{ORCID_BASE}/{orcid_id}/works",
            headers={"Accept": "application/json"},
        )
        r.raise_for_status()
        return r.json()

    # -- DataCite -------------------------------------------------------------

    async def datacite_search(self, query: str, page_size: int = 25) -> Dict[str, Any]:
        c = await self._http()
        r = await c.get(
            f"{DATACITE_BASE}/dois",
            params={"query": query, "page[size]": page_size},
        )
        r.raise_for_status()
        return r.json()

    async def datacite_doi(self, doi: str) -> Dict[str, Any]:
        c = await self._http()
        r = await c.get(f"{DATACITE_BASE}/dois/{doi}")
        r.raise_for_status()
        return r.json()

    # -- Crossref -------------------------------------------------------------

    async def crossref_search(self, query: str, rows: int = 25) -> Dict[str, Any]:
        c = await self._http()
        r = await c.get(
            f"{CROSSREF_BASE}/works",
            params={"query": query, "rows": rows},
        )
        r.raise_for_status()
        return r.json()

    async def crossref_doi(self, doi: str) -> Dict[str, Any]:
        c = await self._http()
        r = await c.get(f"{CROSSREF_BASE}/works/{doi}")
        r.raise_for_status()
        return r.json()

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
