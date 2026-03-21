"""
Infrastructure Connector — factories, power plants, mining, oil/gas, dams, water treatment, pollution.

Data sources: OpenStreetMap Overpass, US EPA FRS, Global Energy Monitor.

Created: March 15, 2026
"""

from __future__ import annotations

import logging
import math
import uuid
from typing import Dict, List, Optional

from mycosoft_mas.earth_search.connectors.base import BaseConnector
from mycosoft_mas.earth_search.models import (
    EarthSearchDomain,
    EarthSearchResult,
    GeoFilter,
    TemporalFilter,
)

logger = logging.getLogger(__name__)

INFRA_DOMAINS = {
    EarthSearchDomain.FACTORIES,
    EarthSearchDomain.POWER_PLANTS,
    EarthSearchDomain.MINING,
    EarthSearchDomain.OIL_GAS,
    EarthSearchDomain.DAMS,
    EarthSearchDomain.WATER_TREATMENT,
    EarthSearchDomain.RIVERS,
    EarthSearchDomain.POLLUTION_SOURCES,
}

# OSM tag mapping per domain
OSM_TAGS: Dict[EarthSearchDomain, str] = {
    EarthSearchDomain.FACTORIES: '["man_made"="works"]',
    EarthSearchDomain.POWER_PLANTS: '["power"="plant"]',
    EarthSearchDomain.MINING: '["landuse"="quarry"]',
    EarthSearchDomain.OIL_GAS: '["man_made"="petroleum_well"]',
    EarthSearchDomain.DAMS: '["waterway"="dam"]',
    EarthSearchDomain.WATER_TREATMENT: '["man_made"="wastewater_plant"]',
    EarthSearchDomain.RIVERS: '["waterway"="river"]',
}


class InfrastructureConnector(BaseConnector):
    """Connector for industrial infrastructure and pollution source data."""

    source_id = "infrastructure"
    rate_limit_rps = 1.0  # Overpass is rate-limited

    OVERPASS_URL = "https://overpass-api.de/api/interpreter"
    EPA_FRS_URL = "https://ofmpub.epa.gov/frs_public2/frs_rest_services.get_facilities"

    async def search(
        self,
        query: str,
        domains: List[EarthSearchDomain],
        geo: Optional[GeoFilter] = None,
        temporal: Optional[TemporalFilter] = None,
        limit: int = 20,
    ) -> List[EarthSearchResult]:
        relevant = [d for d in domains if d in INFRA_DOMAINS]
        if not relevant:
            return []

        results: List[EarthSearchResult] = []

        # OSM Overpass queries for infrastructure
        for domain in relevant:
            if domain in OSM_TAGS and geo:
                osm_results = await self._search_overpass(domain, geo, limit)
                results.extend(osm_results)

        # EPA pollution sources (US only)
        if EarthSearchDomain.POLLUTION_SOURCES in relevant and geo:
            results.extend(await self._search_epa_facilities(geo, limit))

        return results[:limit]

    async def _search_overpass(
        self,
        domain: EarthSearchDomain,
        geo: GeoFilter,
        limit: int,
    ) -> List[EarthSearchResult]:
        """Query OpenStreetMap Overpass for infrastructure features."""
        tag = OSM_TAGS.get(domain, "")
        if not tag:
            return []

        dlat = geo.radius_km / 111
        dlng = geo.radius_km / (111 * max(0.01, abs(math.cos(math.radians(geo.lat)))))
        bbox = f"{geo.lat - dlat},{geo.lng - dlng},{geo.lat + dlat},{geo.lng + dlng}"

        overpass_q = f"[out:json][timeout:15];(node{tag}({bbox});way{tag}({bbox}););out center {min(limit, 50)};"
        data = await self._post(
            self.OVERPASS_URL,
            data=f"data={overpass_q}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if not data:
            return []

        results: List[EarthSearchResult] = []
        for elem in data.get("elements", []):
            tags = elem.get("tags", {})
            lat = elem.get("lat") or elem.get("center", {}).get("lat")
            lng = elem.get("lon") or elem.get("center", {}).get("lon")
            name = tags.get("name", f"{domain.value.replace('_', ' ').title()}")

            results.append(
                EarthSearchResult(
                    result_id=f"osm-{elem.get('id', uuid.uuid4().hex[:8])}",
                    domain=domain,
                    source="osm_overpass",
                    title=name,
                    description=f"Type: {domain.value}, Operator: {tags.get('operator', 'N/A')}",
                    data={
                        "osm_id": elem.get("id"),
                        "osm_type": elem.get("type"),
                        "tags": tags,
                        "operator": tags.get("operator"),
                        "capacity": tags.get("plant:output:electricity") or tags.get("capacity"),
                        "fuel": tags.get("generator:source") or tags.get("plant:source"),
                    },
                    lat=lat,
                    lng=lng,
                    confidence=0.85,
                    crep_layer=domain.value,
                )
            )
        return results

    async def _search_epa_facilities(self, geo: GeoFilter, limit: int) -> List[EarthSearchResult]:
        """Search US EPA Facility Registry for pollution-emitting sites."""
        # EPA FRS accepts lat/lon bounding box
        dlat = geo.radius_km / 111
        dlng = geo.radius_km / (111 * max(0.01, abs(math.cos(math.radians(geo.lat)))))

        params = {
            "output": "JSON",
            "latitude83_start": str(geo.lat - dlat),
            "latitude83_end": str(geo.lat + dlat),
            "longitude83_start": str(geo.lng - dlng),
            "longitude83_end": str(geo.lng + dlng),
        }
        data = await self._get(self.EPA_FRS_URL, params=params)
        if not data:
            return []

        facilities = data.get("Results", {}).get("FRSFacility", [])
        if not isinstance(facilities, list):
            return []

        results: List[EarthSearchResult] = []
        for fac in facilities[:limit]:
            results.append(
                EarthSearchResult(
                    result_id=f"epa-{fac.get('RegistryId', uuid.uuid4().hex[:8])}",
                    domain=EarthSearchDomain.POLLUTION_SOURCES,
                    source="epa_frs",
                    title=fac.get("PrimaryName", "Unknown Facility"),
                    description=f"City: {fac.get('CityName', '')}, State: {fac.get('StateCode', '')}",
                    data={
                        "registry_id": fac.get("RegistryId"),
                        "programs": fac.get("EnvironmentalInterestCount"),
                        "naics": fac.get("NaicsCode"),
                        "sic": fac.get("SicCode"),
                        "address": fac.get("LocationAddress"),
                        "city": fac.get("CityName"),
                        "state": fac.get("StateCode"),
                        "zip": fac.get("PostalCode"),
                    },
                    lat=float(fac["Latitude83"]) if fac.get("Latitude83") else None,
                    lng=float(fac["Longitude83"]) if fac.get("Longitude83") else None,
                    confidence=0.9,
                    crep_layer="pollution_sources",
                )
            )
        return results
