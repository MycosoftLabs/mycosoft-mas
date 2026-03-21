"""
GAO/IG Report Monitor Client.

GAO reports via GovInfo API (historical archive). Inspector General reports
via RSS feeds. Congressional testimony tracking via GovInfo.

Environment Variables:
    GOVINFO_API_KEY: GovInfo/GPO API key (optional; improves rate limits)
    GAO_BASE_URL: Override GovInfo base (default: https://api.govinfo.gov)
"""

import logging
import os
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

DEFAULT_BASE = "https://api.govinfo.gov"
GAO_COLLECTION = "gaoreports"

# Known IG RSS feeds for monitoring
IG_RSS_FEEDS = {
    "federal_reserve_oig": "https://oig.federalreserve.gov/feeds/oig.xml",
    "ssa_oig": "https://oig.ssa.gov/rss/audits.xml",
    "hhs_oig": "https://oig.hhs.gov/feeds/oig-news.xml",
    "dod_oig": "https://www.dodig.mil/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=804&Category=1085",
}


class GaoClient:
    """Client for GAO reports (GovInfo) and Inspector General RSS feeds."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.api_key = self.config.get("api_key") or os.environ.get("GOVINFO_API_KEY", "")
        self.base_url = (
            self.config.get("base_url") or os.environ.get("GAO_BASE_URL", DEFAULT_BASE)
        ).rstrip("/")
        self.timeout = self.config.get("timeout", 30)
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            params: Dict[str, str] = {}
            if self.api_key:
                params["api_key"] = self.api_key
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                params=params if params else None,
                timeout=self.timeout,
                headers={"Accept": "application/json"},
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def search_gao_reports(
        self,
        collection: str = GAO_COLLECTION,
        page_size: int = 50,
        offset_mark: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search GAO reports via GovInfo collections API.
        Returns packages (report metadata) from the GAO collection.
        Note: GovInfo GAO archive covers FY93–Sep 2008; newer reports at gao.gov.
        """
        try:
            client = await self._get_client()
            params: Dict[str, Any] = {"pageSize": page_size}
            if offset_mark:
                params["offsetMark"] = offset_mark
            r = await client.get(
                f"/collections/{collection}",
                params=params,
            )
            r.raise_for_status()
            data = r.json()
            return {
                "status": "ok",
                "count": len(data.get("packages", [])),
                "next_offset": data.get("nextPageToken"),
                "packages": data.get("packages", []),
            }
        except httpx.HTTPStatusError as e:
            logger.warning("GAO collection fetch failed: %s", e)
            return {
                "status": "error",
                "message": str(e),
                "packages": [],
            }
        except Exception as e:
            logger.exception("GAO search error: %s", e)
            return {"status": "error", "message": str(e), "packages": []}

    async def get_gao_package(self, package_id: str) -> Dict[str, Any]:
        """Get a single GAO report package summary from GovInfo."""
        try:
            client = await self._get_client()
            r = await client.get(f"/packages/{package_id}/summary")
            r.raise_for_status()
            return {"status": "ok", "package": r.json()}
        except httpx.HTTPStatusError as e:
            return {"status": "error", "message": str(e), "package": None}
        except Exception as e:
            logger.exception("GAO package fetch error: %s", e)
            return {"status": "error", "message": str(e), "package": None}

    async def fetch_ig_rss(
        self,
        feed_key: Optional[str] = None,
        feed_url: Optional[str] = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Fetch and parse an Inspector General RSS feed.
        Pass feed_key (e.g. 'federal_reserve_oig') or feed_url.
        """
        url = feed_url
        if not url:
            url = IG_RSS_FEEDS.get(feed_key or "", "") if feed_key else None
        if not url:
            return {
                "status": "error",
                "message": "Provide feed_key or feed_url",
                "items": [],
            }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as h:
                r = await h.get(url)
                r.raise_for_status()
                root = ET.fromstring(r.text)
        except Exception as e:
            logger.warning("IG RSS fetch failed %s: %s", url, e)
            return {"status": "error", "message": str(e), "items": []}

        ns = {"atom": "http://www.w3.org/2005/Atom", "dc": "http://purl.org/dc/elements/1.1/"}
        items: List[Dict[str, Any]] = []
        # RSS 2.0
        for item in root.findall(".//item")[:limit]:
            entry = {}
            t = item.find("title")
            if t is not None and t.text:
                entry["title"] = t.text
            lk = item.find("link")
            if lk is not None:
                entry["link"] = lk.text or (lk.get("href") if lk.get("href") else "")
            desc = item.find("description")
            if desc is not None and desc.text:
                entry["description"] = (
                    desc.text[:500] + "..." if len(desc.text) > 500 else desc.text
                )
            pub = item.find("pubDate")
            if pub is not None and pub.text:
                entry["pubDate"] = pub.text
            items.append(entry)
        # Atom fallback
        if not items:
            for entry in root.findall(".//atom:entry", ns)[:limit]:
                e = {}
                t = entry.find("atom:title", ns)
                if t is not None and t.text:
                    e["title"] = t.text
                link = entry.find("atom:link", ns)
                if link is not None and link.get("href"):
                    e["link"] = link.get("href", "")
                up = entry.find("atom:updated", ns)
                if up is not None and up.text:
                    e["pubDate"] = up.text
                items.append(e)
        return {"status": "ok", "feed_url": url, "items": items}

    async def list_ig_feeds(self) -> Dict[str, str]:
        """Return mapping of available IG RSS feed keys to URLs."""
        return dict(IG_RSS_FEEDS)

    async def health_check(self) -> Dict[str, Any]:
        """Verify GovInfo API and RSS connectivity."""
        ok = True
        msg = []
        try:
            client = await self._get_client()
            r = await client.get("/collections", params={"pageSize": 1})
            ok = ok and r.status_code == 200
        except Exception as e:
            ok = False
            msg.append(f"GovInfo: {e}")
        return {"status": "healthy" if ok else "degraded", "details": msg or ["ok"]}
