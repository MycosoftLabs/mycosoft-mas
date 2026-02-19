"""
NCBI (National Center for Biotechnology Information) Integration Client.

Provides access to PubMed, GenBank, and other NCBI E-utilities.
Used by: ResearchAgent, MycologyBioAgent, MINDEX sync scripts.

Environment Variables:
    NCBI_API_KEY: API key from https://www.ncbi.nlm.nih.gov/account/settings/
                  (optional; 10 req/sec with key vs 3 without)
"""

import os
import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

NCBI_EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


class NCBIClient:
    """Client for NCBI E-utilities (PubMed, GenBank, etc.)."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.api_key = self.config.get("api_key", os.getenv("NCBI_API_KEY", ""))
        self.timeout = self.config.get("timeout", 30)
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            params = {"retmode": "json"}
            if self.api_key:
                params["api_key"] = self.api_key
            self._client = httpx.AsyncClient(timeout=self.timeout, params=params)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def search_pubmed(self, query: str, retmax: int = 20) -> List[str]:
        """Search PubMed; return list of PMIDs."""
        client = await self._get_client()
        params = {"db": "pubmed", "term": query, "retmax": retmax}
        if self.api_key:
            params["api_key"] = self.api_key
        try:
            r = await client.get(f"{NCBI_EUTILS_BASE}/esearch.fcgi", params=params)
            r.raise_for_status()
            data = r.json()
            return data.get("esearchresult", {}).get("idlist", [])
        except Exception as e:
            logger.warning("NCBI PubMed search failed: %s", e)
            return []

    async def fetch_pubmed_summary(self, pmids: List[str]) -> List[Dict[str, Any]]:
        """Fetch PubMed summaries for given PMIDs."""
        if not pmids:
            return []
        client = await self._get_client()
        params = {"db": "pubmed", "id": ",".join(pmids)}
        if self.api_key:
            params["api_key"] = self.api_key
        try:
            r = await client.get(f"{NCBI_EUTILS_BASE}/esummary.fcgi", params=params)
            r.raise_for_status()
            data = r.json()
            result = data.get("result", {})
            return [result[k] for k in pmids if k in result and isinstance(result[k], dict)]
        except Exception as e:
            logger.warning("NCBI esummary failed: %s", e)
            return []

    async def search_genbank(self, query: str, retmax: int = 20) -> List[str]:
        """Search GenBank nucleotide; return list of IDs."""
        client = await self._get_client()
        params = {"db": "nucleotide", "term": query, "retmax": retmax}
        if self.api_key:
            params["api_key"] = self.api_key
        try:
            r = await client.get(f"{NCBI_EUTILS_BASE}/esearch.fcgi", params=params)
            r.raise_for_status()
            data = r.json()
            return data.get("esearchresult", {}).get("idlist", [])
        except Exception as e:
            logger.warning("NCBI GenBank search failed: %s", e)
            return []
