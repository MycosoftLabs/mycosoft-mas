"""
Patent / IP Intelligence Client

Provides access to patent databases:
- USPTO PatentsView API -- US patent search, citations, assignees
- EPO Open Patent Services (OPS) -- European patent search
- WIPO -- international patent data
- Google Patents (via SerpApi or direct)

Env vars:
    EPO_CONSUMER_KEY     -- EPO OPS consumer key
    EPO_CONSUMER_SECRET  -- EPO OPS consumer secret
"""

import os
import logging
import base64
from typing import Any, Dict, List, Optional
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

USPTO_BASE = "https://api.patentsview.org/patents/query"
USPTO_CPC_BASE = "https://api.patentsview.org"
EPO_AUTH_URL = "https://ops.epo.org/3.2/auth/accesstoken"
EPO_BASE = "https://ops.epo.org/3.2/rest-services"
WIPO_BASE = "https://patentscope.wipo.int/search/en/result.jsf"


class PatentClient:
    """Patent and IP intelligence across USPTO, EPO, and WIPO."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.epo_key = self.config.get("epo_consumer_key") or os.getenv("EPO_CONSUMER_KEY", "")
        self.epo_secret = self.config.get("epo_consumer_secret") or os.getenv("EPO_CONSUMER_SECRET", "")
        self.timeout = self.config.get("timeout", 30)
        self._client: Optional[httpx.AsyncClient] = None
        self._epo_token: Optional[str] = None

    async def _http(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def health_check(self) -> Dict[str, Any]:
        try:
            c = await self._http()
            r = await c.post(
                USPTO_BASE,
                json={"q": {"_text_any": {"patent_title": "test"}}, "f": ["patent_number"], "o": {"per_page": 1}},
            )
            return {
                "status": "ok" if r.status_code == 200 else "degraded",
                "uspto": r.status_code == 200,
                "epo_key_set": bool(self.epo_key),
                "ts": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # -- USPTO PatentsView ----------------------------------------------------

    async def search_patents(
        self,
        query: str,
        fields: Optional[List[str]] = None,
        per_page: int = 25,
        page: int = 1,
    ) -> Dict[str, Any]:
        """Search US patents by text query."""
        c = await self._http()
        default_fields = [
            "patent_number", "patent_title", "patent_date",
            "patent_abstract", "assignee_organization",
        ]
        body = {
            "q": {"_text_any": {"patent_title": query}},
            "f": fields or default_fields,
            "o": {"per_page": per_page, "page": page},
            "s": [{"patent_date": "desc"}],
        }
        r = await c.post(USPTO_BASE, json=body)
        r.raise_for_status()
        return r.json()

    async def patent_by_number(self, patent_number: str) -> Dict[str, Any]:
        """Get patent details by number."""
        c = await self._http()
        body = {
            "q": {"patent_number": patent_number},
            "f": [
                "patent_number", "patent_title", "patent_date", "patent_abstract",
                "assignee_organization", "inventor_first_name", "inventor_last_name",
                "citedby_patent_number",
            ],
        }
        r = await c.post(USPTO_BASE, json=body)
        r.raise_for_status()
        return r.json()

    async def search_by_assignee(self, assignee: str, per_page: int = 25) -> Dict[str, Any]:
        """Search patents by assignee organization."""
        c = await self._http()
        body = {
            "q": {"_text_any": {"assignee_organization": assignee}},
            "f": ["patent_number", "patent_title", "patent_date", "assignee_organization"],
            "o": {"per_page": per_page},
            "s": [{"patent_date": "desc"}],
        }
        r = await c.post(USPTO_BASE, json=body)
        r.raise_for_status()
        return r.json()

    async def patent_citations(self, patent_number: str) -> Dict[str, Any]:
        """Get citations for a patent."""
        c = await self._http()
        body = {
            "q": {"patent_number": patent_number},
            "f": ["patent_number", "citedby_patent_number", "citedby_patent_title", "citedby_patent_date"],
        }
        r = await c.post(USPTO_BASE, json=body)
        r.raise_for_status()
        return r.json()

    # -- EPO Open Patent Services ---------------------------------------------

    async def _epo_auth(self) -> str:
        """Authenticate with EPO OPS and get bearer token."""
        if self._epo_token:
            return self._epo_token
        if not self.epo_key or not self.epo_secret:
            raise ValueError("EPO_CONSUMER_KEY and EPO_CONSUMER_SECRET required")
        c = await self._http()
        creds = base64.b64encode(f"{self.epo_key}:{self.epo_secret}".encode()).decode()
        r = await c.post(
            EPO_AUTH_URL,
            headers={"Authorization": f"Basic {creds}", "Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": "client_credentials"},
        )
        r.raise_for_status()
        self._epo_token = r.json()["access_token"]
        return self._epo_token

    async def epo_search(self, query: str, range_begin: int = 1, range_end: int = 25) -> Dict[str, Any]:
        """Search European patents via EPO OPS."""
        token = await self._epo_auth()
        c = await self._http()
        r = await c.get(
            f"{EPO_BASE}/published-data/search",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "X-OPS-Range": f"{range_begin}-{range_end}",
            },
            params={"q": query},
        )
        r.raise_for_status()
        return r.json()

    async def epo_publication(self, doc_type: str, doc_number: str, kind: str = "A1") -> Dict[str, Any]:
        """Get EPO publication details."""
        token = await self._epo_auth()
        c = await self._http()
        r = await c.get(
            f"{EPO_BASE}/published-data/publication/epodoc/{doc_type}.{doc_number}.{kind}/biblio",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        )
        r.raise_for_status()
        return r.json()

    # -- WIPO PatentScope -----------------------------------------------------

    async def wipo_search(self, query: str) -> Dict[str, Any]:
        """Search WIPO PatentScope (returns link; no public JSON API)."""
        return {
            "provider": "WIPO PatentScope",
            "query": query,
            "url": f"https://patentscope.wipo.int/search/en/result.jsf?query={query}",
            "note": "WIPO does not offer a public JSON REST API; use the URL for browser access.",
        }

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
