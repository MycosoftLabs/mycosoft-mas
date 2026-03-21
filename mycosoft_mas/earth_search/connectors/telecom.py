"""
Telecom Connector — cell towers, AM/FM antennas, WiFi hotspots, internet cables, signal maps.

Data sources: OpenCelliD, WiGLE, TeleGeography, OpenStreetMap Overpass.

Created: March 15, 2026
"""

from __future__ import annotations

import logging
import math
import uuid
from typing import List, Optional

from mycosoft_mas.earth_search.connectors.base import BaseConnector
from mycosoft_mas.earth_search.models import (
    EarthSearchDomain,
    EarthSearchResult,
    GeoFilter,
    TemporalFilter,
)

logger = logging.getLogger(__name__)

TELECOM_DOMAINS = {
    EarthSearchDomain.CELL_TOWERS,
    EarthSearchDomain.AM_FM_ANTENNAS,
    EarthSearchDomain.WIFI_HOTSPOTS,
    EarthSearchDomain.INTERNET_CABLES,
    EarthSearchDomain.SIGNAL_MAPS,
}


class TelecomConnector(BaseConnector):
    """Connector for telecommunications infrastructure data."""

    source_id = "telecom"
    rate_limit_rps = 1.0

    OVERPASS_URL = "https://overpass-api.de/api/interpreter"
    SUBMARINE_CABLE_URL = "https://www.submarinecablemap.com/api/v3"

    async def search(
        self,
        query: str,
        domains: List[EarthSearchDomain],
        geo: Optional[GeoFilter] = None,
        temporal: Optional[TemporalFilter] = None,
        limit: int = 20,
    ) -> List[EarthSearchResult]:
        relevant = [d for d in domains if d in TELECOM_DOMAINS]
        if not relevant:
            return []

        results: List[EarthSearchResult] = []

        if EarthSearchDomain.CELL_TOWERS in relevant and geo:
            results.extend(await self._search_cell_towers(geo, limit))

        if EarthSearchDomain.INTERNET_CABLES in relevant:
            results.extend(await self._search_submarine_cables(query, limit))

        if EarthSearchDomain.WIFI_HOTSPOTS in relevant and geo:
            results.extend(await self._search_wifi_osm(geo, limit))

        return results[:limit]

    async def _search_cell_towers(self, geo: GeoFilter, limit: int) -> List[EarthSearchResult]:
        """Search cell towers via OpenStreetMap Overpass."""
        dlat = geo.radius_km / 111
        dlng = geo.radius_km / (111 * max(0.01, abs(math.cos(math.radians(geo.lat)))))
        bbox = f"{geo.lat - dlat},{geo.lng - dlng},{geo.lat + dlat},{geo.lng + dlng}"

        # Also try tower tag
        overpass_q2 = f'[out:json][timeout:15];(node["man_made"="mast"]["tower:type"="communication"]({bbox});node["man_made"="tower"]["tower:type"="communication"]({bbox}););out body {min(limit, 50)};'

        data = await self._post(
            self.OVERPASS_URL,
            data=f"data={overpass_q2}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if not data:
            return []

        results: List[EarthSearchResult] = []
        for elem in data.get("elements", []):
            tags = elem.get("tags", {})
            name = tags.get("name", "Communication Tower")
            results.append(
                EarthSearchResult(
                    result_id=f"tower-{elem.get('id', uuid.uuid4().hex[:8])}",
                    domain=EarthSearchDomain.CELL_TOWERS,
                    source="osm_overpass",
                    title=name,
                    description=f"Operator: {tags.get('operator', 'N/A')}, Height: {tags.get('height', 'N/A')}",
                    data={
                        "osm_id": elem.get("id"),
                        "operator": tags.get("operator"),
                        "height": tags.get("height"),
                        "tower_type": tags.get("tower:type"),
                        "communication_type": tags.get("communication:mobile_phone"),
                    },
                    lat=elem.get("lat"),
                    lng=elem.get("lon"),
                    confidence=0.85,
                    crep_layer="cell_towers",
                )
            )
        return results

    async def _search_submarine_cables(self, query: str, limit: int) -> List[EarthSearchResult]:
        """Search submarine internet cable routes."""
        data = await self._get(f"{self.SUBMARINE_CABLE_URL}/cable/all.json")
        if not data or not isinstance(data, list):
            return []

        results: List[EarthSearchResult] = []
        q_lower = query.lower()
        for cable in data:
            name = cable.get("name", "")
            if q_lower and q_lower != "*" and q_lower not in name.lower():
                continue
            results.append(
                EarthSearchResult(
                    result_id=f"cable-{cable.get('id', uuid.uuid4().hex[:8])}",
                    domain=EarthSearchDomain.INTERNET_CABLES,
                    source="telegeography",
                    title=name,
                    description=f"Length: {cable.get('length', 'N/A')} km, RFS: {cable.get('rfs', 'N/A')}",
                    data={
                        "cable_id": cable.get("id"),
                        "length_km": cable.get("length"),
                        "rfs": cable.get("rfs"),
                        "owners": cable.get("owners"),
                        "url": cable.get("url"),
                    },
                    confidence=0.9,
                    crep_layer="internet_cables",
                    url=cable.get("url"),
                )
            )
            if len(results) >= limit:
                break
        return results

    async def _search_wifi_osm(self, geo: GeoFilter, limit: int) -> List[EarthSearchResult]:
        """Search WiFi hotspots via OpenStreetMap."""
        dlat = geo.radius_km / 111
        dlng = geo.radius_km / (111 * max(0.01, abs(math.cos(math.radians(geo.lat)))))
        bbox = f"{geo.lat - dlat},{geo.lng - dlng},{geo.lat + dlat},{geo.lng + dlng}"

        overpass_q = f'[out:json][timeout:10];node["internet_access"="wlan"]({bbox});out body {min(limit, 50)};'
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
            name = tags.get("name", "WiFi Hotspot")
            results.append(
                EarthSearchResult(
                    result_id=f"wifi-{elem.get('id', uuid.uuid4().hex[:8])}",
                    domain=EarthSearchDomain.WIFI_HOTSPOTS,
                    source="osm_overpass",
                    title=name,
                    description=f"Type: {tags.get('amenity', 'N/A')}, Fee: {tags.get('internet_access:fee', 'N/A')}",
                    data={"osm_id": elem.get("id"), "tags": tags},
                    lat=elem.get("lat"),
                    lng=elem.get("lon"),
                    confidence=0.8,
                    crep_layer="wifi_hotspots",
                )
            )
        return results
