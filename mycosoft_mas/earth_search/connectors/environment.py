"""
Environment Connector — earthquakes, volcanoes, wildfires, storms, lightning, tornadoes, floods, tsunamis.

Data sources: USGS, Smithsonian GVP, NASA FIRMS, NOAA NHC/Storm Events.

Created: March 15, 2026
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from mycosoft_mas.earth_search.connectors.base import BaseConnector
from mycosoft_mas.earth_search.models import (
    EarthSearchDomain,
    EarthSearchResult,
    GeoFilter,
    TemporalFilter,
)

logger = logging.getLogger(__name__)

ENV_DOMAINS = {
    EarthSearchDomain.EARTHQUAKES, EarthSearchDomain.VOLCANOES,
    EarthSearchDomain.WILDFIRES, EarthSearchDomain.STORMS,
    EarthSearchDomain.LIGHTNING, EarthSearchDomain.TORNADOES,
    EarthSearchDomain.FLOODS, EarthSearchDomain.TSUNAMIS,
}


class EnvironmentConnector(BaseConnector):
    """Connector for environmental hazard and natural disaster data."""

    source_id = "environment"
    rate_limit_rps = 2.0

    USGS_BASE = "https://earthquake.usgs.gov/fdsnws/event/1"
    FIRMS_BASE = "https://firms.modaps.eosdis.nasa.gov/api/area"
    EONET_BASE = "https://eonet.gsfc.nasa.gov/api/v3"

    async def search(
        self,
        query: str,
        domains: List[EarthSearchDomain],
        geo: Optional[GeoFilter] = None,
        temporal: Optional[TemporalFilter] = None,
        limit: int = 20,
    ) -> List[EarthSearchResult]:
        relevant = [d for d in domains if d in ENV_DOMAINS]
        if not relevant:
            return []

        results: List[EarthSearchResult] = []

        if EarthSearchDomain.EARTHQUAKES in relevant:
            results.extend(await self._search_earthquakes(query, geo, temporal, limit))

        if EarthSearchDomain.WILDFIRES in relevant:
            results.extend(await self._search_wildfires(geo, limit))

        # NASA EONET covers volcanoes, storms, floods, etc.
        eonet_domains = relevant.copy()
        if any(d in eonet_domains for d in [
            EarthSearchDomain.VOLCANOES, EarthSearchDomain.STORMS,
            EarthSearchDomain.FLOODS, EarthSearchDomain.TSUNAMIS,
        ]):
            results.extend(await self._search_eonet(query, eonet_domains, limit))

        return results[:limit]

    async def _search_earthquakes(
        self, query: str, geo: Optional[GeoFilter],
        temporal: Optional[TemporalFilter], limit: int,
    ) -> List[EarthSearchResult]:
        """Query USGS earthquake API."""
        now = datetime.now(timezone.utc)
        start = (temporal.start if temporal and temporal.start else now - timedelta(days=7)).strftime("%Y-%m-%d")
        end = (temporal.end if temporal and temporal.end else now).strftime("%Y-%m-%d")

        params: Dict[str, Any] = {
            "format": "geojson",
            "starttime": start,
            "endtime": end,
            "limit": min(limit, 100),
            "orderby": "time",
        }
        if geo:
            params["latitude"] = geo.lat
            params["longitude"] = geo.lng
            params["maxradiuskm"] = geo.radius_km

        data = await self._get(f"{self.USGS_BASE}/query", params=params)
        if not data:
            return []

        results: List[EarthSearchResult] = []
        for feat in data.get("features", []):
            props = feat.get("properties", {})
            coords = feat.get("geometry", {}).get("coordinates", [None, None])
            results.append(EarthSearchResult(
                result_id=f"usgs-{feat.get('id', uuid.uuid4().hex[:8])}",
                domain=EarthSearchDomain.EARTHQUAKES,
                source="usgs_earthquake",
                title=props.get("title", f"M{props.get('mag', '?')} Earthquake"),
                description=props.get("place", ""),
                data={
                    "magnitude": props.get("mag"),
                    "depth_km": coords[2] if len(coords) > 2 else None,
                    "tsunami": props.get("tsunami"),
                    "alert": props.get("alert"),
                    "felt": props.get("felt"),
                    "cdi": props.get("cdi"),
                    "mmi": props.get("mmi"),
                    "type": props.get("type"),
                },
                lat=coords[1] if len(coords) > 1 else None,
                lng=coords[0] if coords else None,
                timestamp=datetime.fromtimestamp(props["time"] / 1000, tz=timezone.utc).isoformat() if props.get("time") else None,
                confidence=0.99,
                crep_layer="earthquakes",
                url=props.get("url"),
            ))
        return results

    async def _search_wildfires(self, geo: Optional[GeoFilter], limit: int) -> List[EarthSearchResult]:
        """Query NASA FIRMS for active fire detections."""
        firms_key = self._env("NASA_FIRMS_KEY", "DEMO_KEY")
        # Default: global, last 24h, VIIRS
        source = "VIIRS_SNPP_NRT"
        area_url = f"{self.FIRMS_BASE}/csv/{firms_key}/{source}/world/1"

        if geo:
            area_url = f"{self.FIRMS_BASE}/csv/{firms_key}/{source}/{geo.lat},{geo.lng},{geo.radius_km / 111}/1"

        # Use JSON endpoint
        json_url = area_url.replace("/csv/", "/json/")
        data = await self._get(json_url)
        if not data or not isinstance(data, list):
            return []

        results: List[EarthSearchResult] = []
        for fire in data[:limit]:
            results.append(EarthSearchResult(
                result_id=f"firms-{uuid.uuid4().hex[:8]}",
                domain=EarthSearchDomain.WILDFIRES,
                source="firms_wildfires",
                title=f"Active Fire — FRP {fire.get('frp', '?')} MW",
                description=f"Confidence: {fire.get('confidence', '?')}%, Brightness: {fire.get('bright_ti4', '?')}K",
                data={
                    "frp": fire.get("frp"),
                    "brightness": fire.get("bright_ti4"),
                    "confidence": fire.get("confidence"),
                    "satellite": fire.get("satellite"),
                    "instrument": fire.get("instrument"),
                    "daynight": fire.get("daynight"),
                },
                lat=fire.get("latitude"),
                lng=fire.get("longitude"),
                timestamp=f"{fire.get('acq_date', '')}T{fire.get('acq_time', '0000')[:2]}:{fire.get('acq_time', '0000')[2:]}:00Z",
                confidence=float(fire.get("confidence", 50)) / 100,
                crep_layer="wildfires",
            ))
        return results

    async def _search_eonet(
        self, query: str, domains: List[EarthSearchDomain], limit: int,
    ) -> List[EarthSearchResult]:
        """Search NASA EONET for natural events (volcanoes, storms, floods, etc)."""
        # Map domains to EONET categories
        cat_map = {
            EarthSearchDomain.VOLCANOES: "volcanoes",
            EarthSearchDomain.STORMS: "severeStorms",
            EarthSearchDomain.FLOODS: "floods",
            EarthSearchDomain.TSUNAMIS: "floods",
        }
        categories = list(set(cat_map.get(d, "") for d in domains if d in cat_map))
        categories = [c for c in categories if c]

        params: Dict[str, Any] = {"limit": min(limit, 50), "status": "open"}
        if categories:
            params["category"] = ",".join(categories)

        data = await self._get(f"{self.EONET_BASE}/events", params=params)
        if not data:
            return []

        results: List[EarthSearchResult] = []
        for event in data.get("events", []):
            cats = [c.get("id", "") for c in event.get("categories", [])]
            domain = EarthSearchDomain.STORMS  # default
            if "volcanoes" in cats:
                domain = EarthSearchDomain.VOLCANOES
            elif "floods" in cats:
                domain = EarthSearchDomain.FLOODS

            geom = event.get("geometry", [{}])
            coords = geom[-1].get("coordinates", [None, None]) if geom else [None, None]

            results.append(EarthSearchResult(
                result_id=f"eonet-{event.get('id', uuid.uuid4().hex[:8])}",
                domain=domain,
                source="nasa_eonet",
                title=event.get("title", query),
                description=f"Categories: {', '.join(cats)}",
                data={"eonet_id": event.get("id"), "categories": cats, "sources": event.get("sources", [])},
                lat=coords[1] if len(coords) > 1 else None,
                lng=coords[0] if coords else None,
                confidence=0.9,
                crep_layer=domain.value,
                url=event.get("link"),
            ))
        return results
