"""
Species Connector — all living organisms on Earth.

Data sources: iNaturalist, GBIF, Catalogue of Life, EOL, ITIS, WoRMS, BOLD, MycoBank, FungiDB, GenBank.

Covers: fungi, plants, birds, mammals, reptiles, amphibians, insects, marine life, fish, microorganisms.

Created: March 15, 2026
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from mycosoft_mas.earth_search.connectors.base import BaseConnector
from mycosoft_mas.earth_search.models import (
    EarthSearchDomain,
    EarthSearchResult,
    GeoFilter,
    TemporalFilter,
)

logger = logging.getLogger(__name__)

# iNaturalist iconic taxon IDs for each life kingdom/group
INATURALIST_TAXON_IDS: Dict[EarthSearchDomain, int] = {
    EarthSearchDomain.FUNGI: 47170,
    EarthSearchDomain.PLANTS: 47126,
    EarthSearchDomain.BIRDS: 3,
    EarthSearchDomain.MAMMALS: 40151,
    EarthSearchDomain.REPTILES: 26036,
    EarthSearchDomain.AMPHIBIANS: 20978,
    EarthSearchDomain.INSECTS: 47158,
    EarthSearchDomain.FISH: 47178,
    EarthSearchDomain.MARINE_LIFE: 48460,  # Animalia broadly — narrowed by place
    EarthSearchDomain.INVERTEBRATES: 47119,
}

# GBIF kingdom keys
GBIF_KINGDOM_KEYS: Dict[EarthSearchDomain, int] = {
    EarthSearchDomain.FUNGI: 5,
    EarthSearchDomain.PLANTS: 6,
    EarthSearchDomain.MAMMALS: 1,
    EarthSearchDomain.BIRDS: 1,
    EarthSearchDomain.REPTILES: 1,
    EarthSearchDomain.AMPHIBIANS: 1,
    EarthSearchDomain.INSECTS: 1,
    EarthSearchDomain.FISH: 1,
    EarthSearchDomain.MARINE_LIFE: 1,
    EarthSearchDomain.INVERTEBRATES: 1,
    EarthSearchDomain.MICROORGANISMS: 2,
}


class SpeciesConnector(BaseConnector):
    """Unified connector for all species/biodiversity data sources."""

    source_id = "species"
    rate_limit_rps = 1.0  # conservative for public APIs

    INAT_BASE = "https://api.inaturalist.org/v1"
    GBIF_BASE = "https://api.gbif.org/v1"
    MINDEX_BASE_DEFAULT = "http://192.168.0.189:8000"

    LIFE_DOMAINS = {
        EarthSearchDomain.ALL_SPECIES, EarthSearchDomain.FUNGI,
        EarthSearchDomain.PLANTS, EarthSearchDomain.BIRDS,
        EarthSearchDomain.MAMMALS, EarthSearchDomain.REPTILES,
        EarthSearchDomain.AMPHIBIANS, EarthSearchDomain.INSECTS,
        EarthSearchDomain.MARINE_LIFE, EarthSearchDomain.FISH,
        EarthSearchDomain.MICROORGANISMS, EarthSearchDomain.INVERTEBRATES,
    }

    async def search(
        self,
        query: str,
        domains: List[EarthSearchDomain],
        geo: Optional[GeoFilter] = None,
        temporal: Optional[TemporalFilter] = None,
        limit: int = 20,
    ) -> List[EarthSearchResult]:
        relevant = [d for d in domains if d in self.LIFE_DOMAINS]
        if not relevant:
            return []

        results: List[EarthSearchResult] = []

        # 1. MINDEX local first (lowest latency)
        mindex_results = await self._search_mindex(query, limit)
        results.extend(mindex_results)

        # 2. iNaturalist (observations with geolocation)
        inat_results = await self._search_inaturalist(query, relevant, geo, limit)
        results.extend(inat_results)

        # 3. GBIF (occurrence records)
        gbif_results = await self._search_gbif(query, relevant, geo, limit)
        results.extend(gbif_results)

        return results[:limit]

    async def _search_mindex(self, query: str, limit: int) -> List[EarthSearchResult]:
        """Search local MINDEX for pre-ingested species data."""
        mindex_url = self._env("MINDEX_API_URL", self.MINDEX_BASE_DEFAULT)
        headers = {}
        api_key = self._env("MINDEX_API_KEY")
        if api_key:
            headers["X-API-Key"] = api_key

        data = await self._get(
            f"{mindex_url}/api/mindex/unified-search",
            params={"q": query, "types": "taxa,compounds,genetics,observations", "limit": limit},
            headers=headers,
        )
        if not data or not isinstance(data, dict):
            return []

        results: List[EarthSearchResult] = []
        for rtype, items in data.get("results", {}).items():
            for item in (items if isinstance(items, list) else []):
                domain = self._classify_taxon_domain(item)
                results.append(EarthSearchResult(
                    result_id=f"mindex-{uuid.uuid4().hex[:8]}",
                    domain=domain,
                    source="mindex_local",
                    title=item.get("canonical_name") or item.get("name") or query,
                    description=item.get("common_name", ""),
                    data=item,
                    lat=item.get("lat") or item.get("latitude"),
                    lng=item.get("lng") or item.get("longitude"),
                    confidence=0.95,
                    crep_layer="species",
                    mindex_id=str(item.get("id", "")),
                ))
        return results

    async def _search_inaturalist(
        self, query: str, domains: List[EarthSearchDomain],
        geo: Optional[GeoFilter], limit: int,
    ) -> List[EarthSearchResult]:
        """Search iNaturalist for observations."""
        params: Dict[str, Any] = {
            "q": query,
            "per_page": min(limit, 30),
            "order_by": "votes",
            "quality_grade": "research",
        }

        # Add taxon filter if specific domain
        taxon_ids = []
        for d in domains:
            if d in INATURALIST_TAXON_IDS:
                taxon_ids.append(str(INATURALIST_TAXON_IDS[d]))
        if taxon_ids:
            params["taxon_id"] = ",".join(taxon_ids[:5])

        # Add geo filter
        if geo:
            params["lat"] = geo.lat
            params["lng"] = geo.lng
            params["radius"] = geo.radius_km

        data = await self._get(f"{self.INAT_BASE}/observations", params=params)
        if not data:
            return []

        results: List[EarthSearchResult] = []
        for obs in data.get("results", []):
            taxon = obs.get("taxon") or {}
            loc = obs.get("location", "").split(",") if obs.get("location") else [None, None]
            lat = float(loc[0]) if loc[0] else None
            lng = float(loc[1]) if len(loc) > 1 and loc[1] else None
            photos = obs.get("photos", [])
            image_url = photos[0]["url"].replace("square", "medium") if photos else None

            results.append(EarthSearchResult(
                result_id=f"inat-{obs.get('id', uuid.uuid4().hex[:8])}",
                domain=self._classify_taxon_domain(taxon),
                source="inaturalist",
                title=taxon.get("name", query),
                description=taxon.get("preferred_common_name", ""),
                data={"observation_id": obs.get("id"), "taxon": taxon, "quality_grade": obs.get("quality_grade")},
                lat=lat,
                lng=lng,
                timestamp=obs.get("observed_on"),
                confidence=0.85 if obs.get("quality_grade") == "research" else 0.6,
                crep_layer="species",
                url=f"https://www.inaturalist.org/observations/{obs.get('id')}",
                image_url=image_url,
            ))
        return results

    async def _search_gbif(
        self, query: str, domains: List[EarthSearchDomain],
        geo: Optional[GeoFilter], limit: int,
    ) -> List[EarthSearchResult]:
        """Search GBIF for occurrence records."""
        # Species search
        data = await self._get(
            f"{self.GBIF_BASE}/species/search",
            params={"q": query, "limit": min(limit, 20)},
        )
        if not data:
            return []

        results: List[EarthSearchResult] = []
        for sp in data.get("results", []):
            results.append(EarthSearchResult(
                result_id=f"gbif-{sp.get('key', uuid.uuid4().hex[:8])}",
                domain=self._classify_gbif_kingdom(sp.get("kingdom", "")),
                source="gbif",
                title=sp.get("canonicalName") or sp.get("scientificName", query),
                description=f"{sp.get('kingdom', '')} > {sp.get('phylum', '')} > {sp.get('class', '')}",
                data={
                    "gbif_key": sp.get("key"),
                    "rank": sp.get("rank"),
                    "status": sp.get("taxonomicStatus"),
                    "kingdom": sp.get("kingdom"),
                    "phylum": sp.get("phylum"),
                    "class": sp.get("class"),
                    "order": sp.get("order"),
                    "family": sp.get("family"),
                },
                confidence=0.9,
                crep_layer="species",
                url=f"https://www.gbif.org/species/{sp.get('key')}",
            ))
        return results

    def _classify_taxon_domain(self, taxon: Dict[str, Any]) -> EarthSearchDomain:
        """Classify a taxon record into an EarthSearchDomain."""
        kingdom = (taxon.get("kingdom") or taxon.get("iconic_taxon_name") or "").lower()
        if "fungi" in kingdom:
            return EarthSearchDomain.FUNGI
        if "plantae" in kingdom or "plant" in kingdom:
            return EarthSearchDomain.PLANTS
        if "aves" in kingdom or "bird" in kingdom:
            return EarthSearchDomain.BIRDS
        if "mammalia" in kingdom or "mammal" in kingdom:
            return EarthSearchDomain.MAMMALS
        if "reptilia" in kingdom or "reptile" in kingdom:
            return EarthSearchDomain.REPTILES
        if "amphibia" in kingdom or "amphibian" in kingdom:
            return EarthSearchDomain.AMPHIBIANS
        if "insecta" in kingdom or "insect" in kingdom:
            return EarthSearchDomain.INSECTS
        if "actinopterygii" in kingdom or "fish" in kingdom:
            return EarthSearchDomain.FISH
        return EarthSearchDomain.ALL_SPECIES

    def _classify_gbif_kingdom(self, kingdom: str) -> EarthSearchDomain:
        k = kingdom.lower()
        if k == "fungi":
            return EarthSearchDomain.FUNGI
        if k == "plantae":
            return EarthSearchDomain.PLANTS
        if k == "bacteria" or k == "archaea" or k == "chromista" or k == "protozoa":
            return EarthSearchDomain.MICROORGANISMS
        if k == "animalia":
            return EarthSearchDomain.ALL_SPECIES
        return EarthSearchDomain.ALL_SPECIES
