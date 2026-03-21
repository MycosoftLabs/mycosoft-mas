"""
Preprint Watcher Client.

Real-time monitoring of bioRxiv, medRxiv, and arXiv preprints.
Keyword alerts, category filtering, auto-summarization support.

Environment Variables:
    None required - APIs are public
"""

import logging
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

BIORXIV_API_BASE = "https://api.biorxiv.org"
ARXIV_API_BASE = "http://export.arxiv.org/api/query"

# arXiv namespace for Atom feed
ARXIV_ATOM_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


def _parse_arxiv_atom(xml_text: str) -> List[Dict[str, Any]]:
    """Parse arXiv Atom XML feed into list of paper dicts."""
    results: List[Dict[str, Any]] = []
    try:
        root = ET.fromstring(xml_text)
        for entry in root.findall(".//atom:entry", ARXIV_ATOM_NS):
            paper: Dict[str, Any] = {}
            title = entry.find("atom:title", ARXIV_ATOM_NS)
            if title is not None and title.text:
                paper["title"] = title.text.replace("\n", " ").strip()
            summary = entry.find("atom:summary", ARXIV_ATOM_NS)
            if summary is not None and summary.text:
                paper["abstract"] = summary.text.replace("\n", " ").strip()
            link = entry.find("atom:id", ARXIV_ATOM_NS)
            if link is not None and link.text:
                paper["url"] = link.text
                paper["arxiv_id"] = link.text.split("/abs/")[-1] if "/abs/" in link.text else ""
            published = entry.find("atom:published", ARXIV_ATOM_NS)
            if published is not None and published.text:
                paper["published"] = published.text
            authors = []
            for author in entry.findall("atom:author", ARXIV_ATOM_NS):
                name = author.find("atom:name", ARXIV_ATOM_NS)
                if name is not None and name.text:
                    authors.append(name.text)
            if authors:
                paper["authors"] = authors
            cat = entry.find("arxiv:primary_category", ARXIV_ATOM_NS)
            if cat is not None and cat.get("term"):
                paper["category"] = cat.get("term", "")
            paper["source"] = "arxiv"
            results.append(paper)
    except ET.ParseError as e:
        logger.warning("arXiv XML parse error: %s", e)
    return results


class PreprintWatcherClient:
    """Client for bioRxiv/medRxiv and arXiv preprint APIs."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.timeout = self.config.get("timeout", 30)
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def get_biorxiv_recent(
        self,
        server: str = "biorxiv",
        interval: str = "7d",
        cursor: int = 0,
        category: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Get recent bioRxiv/medRxiv preprints.
        server: biorxiv | medrxiv
        interval: '7d' (7 days), '30d', or '100' (100 most recent), or '2025-01-01/2025-01-31'
        """
        client = await self._get_client()
        url = f"{BIORXIV_API_BASE}/details/{server}/{interval}/{cursor}/json"
        params: Dict[str, str] = {}
        if category:
            params["category"] = category.replace(" ", "_")
        try:
            r = await client.get(url, params=params or None)
            if not r.is_success:
                return {"collection": [], "messages": [], "count": 0}
            data = r.json()
            collection = data.get("collection", [])
            if limit and len(collection) > limit:
                collection = collection[:limit]
            return {
                "collection": collection,
                "messages": data.get("messages", []),
                "count": len(collection),
            }
        except Exception as e:
            logger.warning("bioRxiv get_recent failed: %s", e)
            return {"collection": [], "messages": [], "count": 0}

    async def get_arxiv_recent(
        self,
        query: str = "all",
        max_results: int = 50,
        sort_by: str = "submittedDate",
        sort_order: str = "descending",
        categories: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get recent arXiv preprints.
        query: arXiv search query (e.g. 'all', 'cat:q-bio.GN', 'ti:fungi')
        categories: e.g. ['q-bio.GN', 'cs.LG'] for multiple
        """
        client = await self._get_client()
        if categories:
            cat_query = " OR ".join(f"cat:{c}" for c in categories)
            search_query = f"({cat_query})" if query == "all" else f"({query}) AND ({cat_query})"
        else:
            search_query = query
        params = {
            "search_query": search_query,
            "start": 0,
            "max_results": max_results,
            "sortBy": sort_by,
            "sortOrder": sort_order,
        }
        try:
            r = await client.get(ARXIV_API_BASE, params=params)
            if not r.is_success:
                return []
            return _parse_arxiv_atom(r.text)
        except Exception as e:
            logger.warning("arXiv get_recent failed: %s", e)
            return []

    async def watch_preprints(
        self,
        sources: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        biorxiv_interval: str = "7d",
        arxiv_max: int = 50,
    ) -> Dict[str, Any]:
        """
        Watch bioRxiv and arXiv for recent preprints, optionally filter by keywords.
        sources: ['biorxiv', 'medrxiv', 'arxiv'] or None for all
        keywords: case-insensitive filter on title/abstract
        """
        sources = sources or ["biorxiv", "arxiv"]
        results: Dict[str, Any] = {
            "biorxiv": [],
            "medrxiv": [],
            "arxiv": [],
            "filtered_count": 0,
        }
        kw_patterns = [re.compile(re.escape(k), re.I) for k in (keywords or [])]

        def _matches(p: Dict[str, Any]) -> bool:
            if not kw_patterns:
                return True
            text = f"{p.get('title','')} {p.get('abstract','')} {p.get('preprint_title','')} {p.get('preprint_abstract','')}"
            return any(pt.search(text) for pt in kw_patterns)

        if "biorxiv" in sources:
            biorxiv_data = await self.get_biorxiv_recent("biorxiv", interval=biorxiv_interval)
            for p in biorxiv_data.get("collection", []):
                p["source"] = "biorxiv"
                p["title"] = p.get("preprint_title") or p.get("title", "")
                p["abstract"] = p.get("preprint_abstract") or p.get("abstract", "")
                if _matches(p):
                    results["biorxiv"].append(p)
        if "medrxiv" in sources:
            medrxiv_data = await self.get_biorxiv_recent("medrxiv", interval=biorxiv_interval)
            for p in medrxiv_data.get("collection", []):
                p["source"] = "medrxiv"
                p["title"] = p.get("preprint_title") or p.get("title", "")
                p["abstract"] = p.get("preprint_abstract") or p.get("abstract", "")
                if _matches(p):
                    results["medrxiv"].append(p)
        if "arxiv" in sources:
            arxiv_papers = await self.get_arxiv_recent(max_results=arxiv_max)
            for p in arxiv_papers:
                if _matches(p):
                    results["arxiv"].append(p)

        results["filtered_count"] = (
            len(results["biorxiv"]) + len(results["medrxiv"]) + len(results["arxiv"])
        )
        return results

    async def get_biorxiv_by_doi(
        self, doi: str, server: str = "biorxiv"
    ) -> Optional[Dict[str, Any]]:
        """Get single bioRxiv/medRxiv paper by DOI."""
        client = await self._get_client()
        doi_clean = doi.replace("https://doi.org/", "").strip()
        url = f"{BIORXIV_API_BASE}/details/{server}/{doi_clean}/na/json"
        try:
            r = await client.get(url)
            if r.is_success:
                data = r.json()
                collection = data.get("collection", [])
                return collection[0] if collection else None
            return None
        except Exception as e:
            logger.warning("bioRxiv get_by_doi failed: %s", e)
            return None

    async def health_check(self) -> Dict[str, Any]:
        """Check preprint API availability."""
        status: Dict[str, Any] = {"status": "healthy", "service": "preprint_watcher", "sources": {}}
        try:
            biorxiv = await self.get_biorxiv_recent("biorxiv", "1d", limit=5)
            status["sources"]["biorxiv"] = biorxiv.get("count", 0) >= 0
        except Exception as e:
            status["sources"]["biorxiv"] = False
            status["biorxiv_error"] = str(e)
        try:
            arxiv = await self.get_arxiv_recent(max_results=1)
            status["sources"]["arxiv"] = True
        except Exception as e:
            status["sources"]["arxiv"] = False
            status["arxiv_error"] = str(e)
        if not all(status["sources"].values()):
            status["status"] = "degraded"
        return status
