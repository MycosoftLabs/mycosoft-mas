"""
Transport Connector — flights, vessels, airports, shipping ports, spaceports, railways.

Data sources: CREP (ADS-B/AIS), OurAirports, World Port Index, Launch Library 2.

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

TRANSPORT_DOMAINS = {
    EarthSearchDomain.FLIGHTS, EarthSearchDomain.VESSELS,
    EarthSearchDomain.AIRPORTS, EarthSearchDomain.SHIPPING_PORTS,
    EarthSearchDomain.SPACEPORTS, EarthSearchDomain.RAILWAYS,
}


class TransportConnector(BaseConnector):
    """Connector for global transportation and logistics data."""

    source_id = "transport"
    rate_limit_rps = 2.0

    CREP_BASE = "http://192.168.0.187:3000/api/crep"
    LAUNCH_LIBRARY_BASE = "https://ll.thespacedevs.com/2.2.0"

    async def search(
        self,
        query: str,
        domains: List[EarthSearchDomain],
        geo: Optional[GeoFilter] = None,
        temporal: Optional[TemporalFilter] = None,
        limit: int = 20,
    ) -> List[EarthSearchResult]:
        relevant = [d for d in domains if d in TRANSPORT_DOMAINS]
        if not relevant:
            return []

        results: List[EarthSearchResult] = []

        if EarthSearchDomain.FLIGHTS in relevant:
            results.extend(await self._search_flights(geo, limit))

        if EarthSearchDomain.VESSELS in relevant:
            results.extend(await self._search_vessels(geo, limit))

        if EarthSearchDomain.AIRPORTS in relevant:
            results.extend(await self._search_airports(query, geo, limit))

        if EarthSearchDomain.SPACEPORTS in relevant or EarthSearchDomain.LAUNCHES in domains:
            results.extend(await self._search_launches(query, limit))

        return results[:limit]

    async def _search_flights(self, geo: Optional[GeoFilter], limit: int) -> List[EarthSearchResult]:
        """Get real-time flight data from CREP (ADS-B)."""
        url = f"{self.CREP_BASE}/flights"
        params: Dict[str, Any] = {}
        if geo:
            url = f"{self.CREP_BASE}/flights/region"
            params = {"lat": geo.lat, "lon": geo.lng, "radius": geo.radius_km}

        data = await self._get(url, params=params)
        if not data:
            return []

        aircraft_list = data.get("aircraft", data) if isinstance(data, dict) else data
        if not isinstance(aircraft_list, list):
            aircraft_list = []

        results: List[EarthSearchResult] = []
        for ac in aircraft_list[:limit]:
            callsign = ac.get("callsign") or ac.get("flight") or "Unknown"
            results.append(EarthSearchResult(
                result_id=f"flight-{ac.get('hex', uuid.uuid4().hex[:8])}",
                domain=EarthSearchDomain.FLIGHTS,
                source="crep_flights",
                title=f"Flight {callsign}",
                description=f"Alt: {ac.get('alt_baro', '?')}ft, Speed: {ac.get('gs', '?')}kt, Heading: {ac.get('track', '?')}°",
                data={
                    "icao": ac.get("hex"),
                    "callsign": callsign,
                    "altitude_ft": ac.get("alt_baro"),
                    "ground_speed_kt": ac.get("gs"),
                    "heading": ac.get("track"),
                    "squawk": ac.get("squawk"),
                    "aircraft_type": ac.get("t"),
                    "registration": ac.get("r"),
                    "category": ac.get("category"),
                },
                lat=ac.get("lat"),
                lng=ac.get("lon"),
                confidence=0.95,
                crep_layer="flights",
                crep_entity_id=ac.get("hex"),
            ))
        return results

    async def _search_vessels(self, geo: Optional[GeoFilter], limit: int) -> List[EarthSearchResult]:
        """Get real-time vessel data from CREP (AIS)."""
        url = f"{self.CREP_BASE}/marine"
        params: Dict[str, Any] = {}
        if geo:
            url = f"{self.CREP_BASE}/marine/region"
            params = {"lat": geo.lat, "lon": geo.lng, "radius": geo.radius_km}

        data = await self._get(url, params=params)
        if not data:
            return []

        vessels = data.get("vessels", data) if isinstance(data, dict) else data
        if not isinstance(vessels, list):
            vessels = []

        results: List[EarthSearchResult] = []
        for v in vessels[:limit]:
            name = v.get("name") or v.get("shipname") or "Unknown Vessel"
            results.append(EarthSearchResult(
                result_id=f"vessel-{v.get('mmsi', uuid.uuid4().hex[:8])}",
                domain=EarthSearchDomain.VESSELS,
                source="crep_marine",
                title=f"Vessel {name}",
                description=f"Type: {v.get('ship_type', '?')}, Speed: {v.get('speed', '?')}kt, Course: {v.get('course', '?')}°",
                data={
                    "mmsi": v.get("mmsi"),
                    "imo": v.get("imo"),
                    "ship_type": v.get("ship_type"),
                    "speed_kt": v.get("speed"),
                    "course": v.get("course"),
                    "destination": v.get("destination"),
                    "flag": v.get("flag"),
                    "length": v.get("length"),
                },
                lat=v.get("lat"),
                lng=v.get("lon") or v.get("lng"),
                confidence=0.9,
                crep_layer="vessels",
                crep_entity_id=str(v.get("mmsi", "")),
            ))
        return results

    async def _search_airports(self, query: str, geo: Optional[GeoFilter], limit: int) -> List[EarthSearchResult]:
        """Search airports using OurAirports data via OpenStreetMap Overpass as fallback."""
        # Use Overpass API to find airports
        bbox = ""
        if geo:
            dlat = geo.radius_km / 111
            dlng = geo.radius_km / (111 * max(0.01, abs(__import__("math").cos(__import__("math").radians(geo.lat)))))
            bbox = f"{geo.lat - dlat},{geo.lng - dlng},{geo.lat + dlat},{geo.lng + dlng}"
        else:
            bbox = "-90,-180,90,180"

        overpass_query = f'[out:json][timeout:10];node["aeroway"="aerodrome"]({bbox});out body {min(limit, 20)};'
        data = await self._post(
            "https://overpass-api.de/api/interpreter",
            data=f"data={overpass_query}",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if not data:
            return []

        results: List[EarthSearchResult] = []
        for elem in data.get("elements", []):
            tags = elem.get("tags", {})
            name = tags.get("name", "Unknown Airport")
            if query.lower() not in name.lower() and query.lower() not in tags.get("iata", "").lower():
                if query and query != "*":
                    continue
            results.append(EarthSearchResult(
                result_id=f"airport-{elem.get('id', uuid.uuid4().hex[:8])}",
                domain=EarthSearchDomain.AIRPORTS,
                source="osm_overpass",
                title=name,
                description=f"IATA: {tags.get('iata', 'N/A')}, ICAO: {tags.get('icao', 'N/A')}",
                data={
                    "iata": tags.get("iata"),
                    "icao": tags.get("icao"),
                    "type": tags.get("aeroway"),
                    "operator": tags.get("operator"),
                },
                lat=elem.get("lat"),
                lng=elem.get("lon"),
                confidence=0.9,
                crep_layer="airports",
            ))
        return results

    async def _search_launches(self, query: str, limit: int) -> List[EarthSearchResult]:
        """Search upcoming rocket launches and launch sites."""
        data = await self._get(
            f"{self.LAUNCH_LIBRARY_BASE}/launch/upcoming/",
            params={"search": query, "limit": min(limit, 10), "mode": "detailed"},
        )
        if not data:
            return []

        results: List[EarthSearchResult] = []
        for launch in data.get("results", []):
            pad = launch.get("pad", {})
            loc = pad.get("location", {})
            results.append(EarthSearchResult(
                result_id=f"launch-{launch.get('id', uuid.uuid4().hex[:8])}",
                domain=EarthSearchDomain.LAUNCHES,
                source="spacex_launches",
                title=launch.get("name", query),
                description=f"Status: {launch.get('status', {}).get('name', '?')}, Provider: {launch.get('launch_service_provider', {}).get('name', '?')}",
                data={
                    "launch_id": launch.get("id"),
                    "status": launch.get("status", {}).get("name"),
                    "net": launch.get("net"),
                    "rocket": launch.get("rocket", {}).get("configuration", {}).get("name"),
                    "mission": launch.get("mission", {}).get("name") if launch.get("mission") else None,
                    "pad": pad.get("name"),
                    "location": loc.get("name"),
                },
                lat=float(pad.get("latitude", 0)) if pad.get("latitude") else None,
                lng=float(pad.get("longitude", 0)) if pad.get("longitude") else None,
                timestamp=launch.get("net"),
                confidence=0.85,
                crep_layer="launches",
                url=launch.get("url"),
                image_url=launch.get("image"),
            ))
        return results
