"""
Biodiversity Client

Access to global biodiversity databases:
- BOLD Systems -- DNA barcoding (Barcode of Life Data)
- Encyclopedia of Life (EOL) -- species pages, media
- Catalogue of Life (CoL) -- authoritative species checklist
- ITIS (Integrated Taxonomic Information System) -- US taxonomy
- WoRMS (World Register of Marine Species) -- marine taxonomy

All public APIs, no keys required.
"""

import os
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

BOLD_BASE = "https://v3.boldsystems.org/index.php/API_Public"
EOL_BASE = "https://eol.org/api"
COL_BASE = "https://api.checklistbank.org"
ITIS_BASE = "https://www.itis.gov/ITISWebService/jsonservice"
WORMS_BASE = "https://www.marinespecies.org/rest"


class BiodiversityClient:
    """Unified client for global biodiversity databases."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.timeout = self.config.get("timeout", 30)
        self._client: Optional[httpx.AsyncClient] = None

    async def _http(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def health_check(self) -> Dict[str, Any]:
        try:
            c = await self._http()
            r = await c.get(f"{ITIS_BASE}/searchByCommonName", params={"srchKey": "mushroom"})
            return {
                "status": "ok" if r.status_code == 200 else "degraded",
                "itis": r.status_code == 200,
                "ts": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # -- BOLD Systems (DNA Barcoding) -----------------------------------------

    async def bold_specimen_search(
        self, taxon: str, geo: Optional[str] = None, format: str = "json"
    ) -> Any:
        """Search BOLD specimen data by taxon name."""
        c = await self._http()
        params: Dict[str, Any] = {"taxon": taxon, "format": format}
        if geo:
            params["geo"] = geo
        r = await c.get(f"{BOLD_BASE}/specimen", params=params)
        r.raise_for_status()
        return r.json() if format == "json" else r.text

    async def bold_sequence_search(self, taxon: str) -> str:
        """Get FASTA sequences from BOLD for a taxon."""
        c = await self._http()
        r = await c.get(f"{BOLD_BASE}/sequence", params={"taxon": taxon})
        r.raise_for_status()
        return r.text

    async def bold_stats(self, taxon: str) -> Any:
        """Get barcode statistics for a taxon."""
        c = await self._http()
        r = await c.get(f"{BOLD_BASE}/stats", params={"taxon": taxon, "format": "json"})
        r.raise_for_status()
        return r.json()

    # -- Encyclopedia of Life (EOL) -------------------------------------------

    async def eol_search(self, query: str, page: int = 1) -> Dict[str, Any]:
        """Search EOL for species pages."""
        c = await self._http()
        r = await c.get(
            f"{EOL_BASE}/search/1.0.json",
            params={"q": query, "page": page},
        )
        r.raise_for_status()
        return r.json()

    async def eol_pages(self, eol_id: int) -> Dict[str, Any]:
        """Get EOL species page with details."""
        c = await self._http()
        r = await c.get(
            f"{EOL_BASE}/pages/1.0/{eol_id}.json",
            params={"details": "true", "images_per_page": 5},
        )
        r.raise_for_status()
        return r.json()

    # -- Catalogue of Life (CoL) via ChecklistBank ----------------------------

    async def col_search(self, query: str, limit: int = 20) -> Dict[str, Any]:
        """Search Catalogue of Life for taxa."""
        c = await self._http()
        r = await c.get(
            f"{COL_BASE}/nameusage/search",
            params={"q": query, "limit": limit, "datasetKey": 3},  # 3 = COL
        )
        r.raise_for_status()
        return r.json()

    async def col_taxon(self, taxon_id: str) -> Dict[str, Any]:
        """Get taxon details from COL."""
        c = await self._http()
        r = await c.get(f"{COL_BASE}/dataset/3/nameusage/{taxon_id}")
        r.raise_for_status()
        return r.json()

    # -- ITIS -----------------------------------------------------------------

    async def itis_search_scientific(self, name: str) -> Dict[str, Any]:
        """Search ITIS by scientific name."""
        c = await self._http()
        r = await c.get(f"{ITIS_BASE}/searchByScientificName", params={"srchKey": name})
        r.raise_for_status()
        return r.json()

    async def itis_search_common(self, name: str) -> Dict[str, Any]:
        """Search ITIS by common name."""
        c = await self._http()
        r = await c.get(f"{ITIS_BASE}/searchByCommonName", params={"srchKey": name})
        r.raise_for_status()
        return r.json()

    async def itis_hierarchy(self, tsn: int) -> Dict[str, Any]:
        """Get full taxonomy hierarchy for a TSN."""
        c = await self._http()
        r = await c.get(f"{ITIS_BASE}/getFullHierarchyFromTSN", params={"tsn": tsn})
        r.raise_for_status()
        return r.json()

    # -- WoRMS (Marine Species) -----------------------------------------------

    async def worms_search(self, name: str, marine_only: bool = True) -> List[Dict[str, Any]]:
        """Search WoRMS for marine species."""
        c = await self._http()
        r = await c.get(
            f"{WORMS_BASE}/AphiaRecordsByName/{name}",
            params={"like": "true", "marine_only": str(marine_only).lower()},
        )
        r.raise_for_status()
        return r.json()

    async def worms_record(self, aphia_id: int) -> Dict[str, Any]:
        """Get WoRMS species record by AphiaID."""
        c = await self._http()
        r = await c.get(f"{WORMS_BASE}/AphiaRecordByAphiaID/{aphia_id}")
        r.raise_for_status()
        return r.json()

    async def worms_classification(self, aphia_id: int) -> Dict[str, Any]:
        """Get full classification for a WoRMS AphiaID."""
        c = await self._http()
        r = await c.get(f"{WORMS_BASE}/AphiaClassificationByAphiaID/{aphia_id}")
        r.raise_for_status()
        return r.json()

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
