"""
Space Connector — satellites, space weather, solar flares, debris, launches, NASA/NOAA feeds.

Data sources: CREP Satellites, NOAA SWPC, NASA DONKI, SOHO/STEREO data.

Created: March 15, 2026
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from mycosoft_mas.earth_search.connectors.base import BaseConnector
from mycosoft_mas.earth_search.models import (
    EarthSearchDomain,
    EarthSearchResult,
    GeoFilter,
    TemporalFilter,
)

logger = logging.getLogger(__name__)

SPACE_DOMAINS = {
    EarthSearchDomain.SATELLITES,
    EarthSearchDomain.SPACE_WEATHER,
    EarthSearchDomain.SOLAR_FLARES,
    EarthSearchDomain.SPACE_DEBRIS,
    EarthSearchDomain.LAUNCHES,
    EarthSearchDomain.NASA_FEEDS,
    EarthSearchDomain.NOAA_FEEDS,
}


class SpaceConnector(BaseConnector):
    """Connector for space situational awareness — satellites, space weather, solar activity."""

    source_id = "space"
    rate_limit_rps = 2.0

    CREP_BASE = "http://192.168.0.187:3000/api/crep"
    SWPC_BASE = "https://services.swpc.noaa.gov/json"
    DONKI_BASE = "https://api.nasa.gov/DONKI"

    async def search(
        self,
        query: str,
        domains: List[EarthSearchDomain],
        geo: Optional[GeoFilter] = None,
        temporal: Optional[TemporalFilter] = None,
        limit: int = 20,
    ) -> List[EarthSearchResult]:
        relevant = [d for d in domains if d in SPACE_DOMAINS]
        if not relevant:
            return []

        results: List[EarthSearchResult] = []

        if EarthSearchDomain.SATELLITES in relevant:
            results.extend(await self._search_satellites(limit))

        if (
            EarthSearchDomain.SOLAR_FLARES in relevant
            or EarthSearchDomain.SPACE_WEATHER in relevant
        ):
            results.extend(await self._search_solar_flares(temporal, limit))
            results.extend(await self._search_geomagnetic(limit))

        return results[:limit]

    async def _search_satellites(self, limit: int) -> List[EarthSearchResult]:
        """Get satellite positions from CREP."""
        data = await self._get(f"{self.CREP_BASE}/satellites")
        if not data:
            return []

        sats = data.get("satellites", data) if isinstance(data, dict) else data
        if not isinstance(sats, list):
            return []

        results: List[EarthSearchResult] = []
        for sat in sats[:limit]:
            name = sat.get("name") or sat.get("satname") or "Unknown Satellite"
            results.append(
                EarthSearchResult(
                    result_id=f"sat-{sat.get('norad_id', sat.get('satid', uuid.uuid4().hex[:8]))}",
                    domain=EarthSearchDomain.SATELLITES,
                    source="crep_satellites",
                    title=name,
                    description=f"NORAD: {sat.get('norad_id', sat.get('satid', '?'))}, Alt: {sat.get('satalt', '?')} km",
                    data={
                        "norad_id": sat.get("norad_id") or sat.get("satid"),
                        "altitude_km": sat.get("satalt"),
                        "velocity_kms": sat.get("satvel"),
                        "inclination": sat.get("inclination"),
                        "period_min": sat.get("period"),
                        "launch_date": sat.get("launchDate"),
                        "intl_designator": sat.get("intDesignator"),
                    },
                    lat=sat.get("satlat") or sat.get("lat"),
                    lng=sat.get("satlng") or sat.get("lng"),
                    confidence=0.9,
                    crep_layer="satellites",
                    crep_entity_id=str(sat.get("norad_id", sat.get("satid", ""))),
                )
            )
        return results

    async def _search_solar_flares(
        self, temporal: Optional[TemporalFilter], limit: int
    ) -> List[EarthSearchResult]:
        """Get solar flare events from NOAA SWPC and NASA DONKI."""
        results: List[EarthSearchResult] = []

        # NOAA SWPC solar flare alerts
        data = await self._get(f"{self.SWPC_BASE}/solar_flare_5_day.json")
        if data and isinstance(data, list):
            for flare in data[:limit]:
                results.append(
                    EarthSearchResult(
                        result_id=f"flare-{uuid.uuid4().hex[:8]}",
                        domain=EarthSearchDomain.SOLAR_FLARES,
                        source="noaa_swpc",
                        title=f"Solar Flare {flare.get('classType', '?')}",
                        description=f"Begin: {flare.get('beginTime', '?')}, Peak: {flare.get('peakTime', '?')}",
                        data={
                            "class_type": flare.get("classType"),
                            "begin_time": flare.get("beginTime"),
                            "peak_time": flare.get("peakTime"),
                            "end_time": flare.get("endTime"),
                            "source_location": flare.get("sourceLocation"),
                            "active_region": flare.get("activeRegionNum"),
                        },
                        confidence=0.95,
                        crep_layer="space_weather",
                    )
                )

        # NASA DONKI
        nasa_key = self._env("NASA_API_KEY", "DEMO_KEY")
        now = datetime.now(timezone.utc)
        start = (
            temporal.start if temporal and temporal.start else now - timedelta(days=30)
        ).strftime("%Y-%m-%d")
        donki = await self._get(
            f"{self.DONKI_BASE}/FLR",
            params={"startDate": start, "api_key": nasa_key},
        )
        if donki and isinstance(donki, list):
            for flare in donki[:limit]:
                results.append(
                    EarthSearchResult(
                        result_id=f"donki-{uuid.uuid4().hex[:8]}",
                        domain=EarthSearchDomain.SOLAR_FLARES,
                        source="nasa_donki",
                        title=f"Solar Flare {flare.get('classType', '?')} — DONKI",
                        description=f"Begin: {flare.get('beginTime', '?')}, Peak: {flare.get('peakTime', '?')}",
                        data={
                            "class_type": flare.get("classType"),
                            "begin_time": flare.get("beginTime"),
                            "peak_time": flare.get("peakTime"),
                            "end_time": flare.get("endTime"),
                            "source_location": flare.get("sourceLocation"),
                            "linked_events": flare.get("linkedEvents"),
                        },
                        confidence=0.95,
                        crep_layer="space_weather",
                        url=flare.get("link"),
                    )
                )

        return results

    async def _search_geomagnetic(self, limit: int) -> List[EarthSearchResult]:
        """Get geomagnetic storm data from NOAA SWPC."""
        data = await self._get(f"{self.SWPC_BASE}/planetary_k_index_1m.json")
        if not data or not isinstance(data, list):
            return []

        # Get the latest few entries
        recent = data[-min(limit, 10) :]
        results: List[EarthSearchResult] = []
        for entry in recent:
            kp = entry.get("kp_index", 0)
            results.append(
                EarthSearchResult(
                    result_id=f"kp-{uuid.uuid4().hex[:8]}",
                    domain=EarthSearchDomain.SPACE_WEATHER,
                    source="noaa_swpc",
                    title=f"Kp Index: {kp}",
                    description=f"Time: {entry.get('time_tag', '?')}",
                    data={
                        "kp_index": kp,
                        "time_tag": entry.get("time_tag"),
                        "estimated_kp": entry.get("estimated_kp"),
                    },
                    confidence=0.95,
                    crep_layer="space_weather",
                )
            )
        return results
