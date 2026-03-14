"""
Overpass / OpenStreetMap Collector - March 14, 2026

Collects infrastructure assets (ports, dams, waterways, rail, roads, power) from OSM via Overpass API.
Use for: infrastructure graph in MINDEX and CREP.
API: https://overpass-api.de/api/interpreter (POST with Overpass QL)
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp

from .base_collector import BaseCollector, RawEvent, TimelineEvent
from .quality_scorer import calculate_quality_score

logger = logging.getLogger(__name__)

# Default bbox: continental US (configurable)
DEFAULT_SOUTH = 24.0
DEFAULT_NORTH = 50.0
DEFAULT_WEST = -125.0
DEFAULT_EAST = -66.0


class OverpassCollector(BaseCollector):
    """
    Collects infrastructure nodes from OpenStreetMap via Overpass API.
    Queries ports (harbour), dams, waterways, rail, major roads, power.
    """

    name = "overpass"
    entity_type = "infrastructure_asset"
    poll_interval_seconds = 3600  # 1 hour - OSM changes slowly

    def __init__(
        self,
        south: float = DEFAULT_SOUTH,
        north: float = DEFAULT_NORTH,
        west: float = DEFAULT_WEST,
        east: float = DEFAULT_EAST,
    ):
        super().__init__()
        self.bbox = (south, west, north, east)
        self.api_url = "https://overpass-api.de/api/interpreter"
        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize(self) -> None:
        self._session = aiohttp.ClientSession(
            headers={"User-Agent": "(Mycosoft CREP, contact@mycosoft.com)"}
        )

    async def cleanup(self) -> None:
        if self._session:
            await self._session.close()

    def _build_query(self) -> str:
        s, w, n, e = self.bbox
        # Query: nodes and ways with key infrastructure tags in bbox
        return f"""
[out:json][timeout:25];
(
  node["waterway"="dam"]({s},{w},{n},{e});
  node["harbour"="yes"]({s},{w},{n},{e});
  node["seamark:type"]({s},{w},{n},{e});
  way["waterway"="dam"]({s},{w},{n},{e});
  way["waterway"="weir"]({s},{w},{n},{e});
  node["power"]({s},{w},{n},{e});
  node["railway"="station"]({s},{w},{n},{e});
  node["aeroway"="aerodrome"]({s},{w},{n},{e});
);
out center;
"""

    def _extract_coords(self, el: Dict[str, Any]) -> Optional[tuple]:
        lat = el.get("lat")
        lon = el.get("lon")
        if lat is not None and lon is not None:
            return (float(lat), float(lon))
        c = el.get("center", {})
        lat = c.get("lat")
        lon = c.get("lon")
        if lat is not None and lon is not None:
            return (float(lat), float(lon))
        b = el.get("bounds", {})
        if b:
            return (
                (float(b.get("minlat", 0)) + float(b.get("maxlat", 0))) / 2,
                (float(b.get("minlon", 0)) + float(b.get("maxlon", 0))) / 2,
            )
        return None

    def _asset_type(self, tags: Dict[str, Any]) -> str:
        if tags.get("waterway") == "dam":
            return "dam"
        if tags.get("waterway") == "weir":
            return "weir"
        if tags.get("harbour") == "yes" or tags.get("seamark:type"):
            return "port"
        if tags.get("power"):
            return "power"
        if tags.get("railway") == "station":
            return "rail_station"
        if tags.get("aeroway") == "aerodrome":
            return "airport"
        return "infrastructure"

    async def fetch(self) -> List[RawEvent]:
        """Fetch infrastructure elements from Overpass."""
        if not self._session:
            await self.initialize()

        query = self._build_query()

        try:
            async with self._session.post(
                self.api_url,
                data={"data": query},
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                if resp.status != 200:
                    logger.error("Overpass error: %s", resp.status)
                    return []

                data = await resp.json()
                events: List[RawEvent] = []
                seen: set = set()

                for el in data.get("elements", []):
                    coords = self._extract_coords(el)
                    if not coords:
                        continue
                    lat, lng = coords
                    tags = el.get("tags", {})
                    osm_id = el.get("id")
                    osm_type = el.get("type", "node")
                    key = f"{osm_type}:{osm_id}"
                    if key in seen:
                        continue
                    seen.add(key)
                    name = tags.get("name") or tags.get("ref") or ""
                    asset_type = self._asset_type(tags)

                    events.append(
                        RawEvent(
                            source="overpass",
                            entity_id=key,
                            entity_type="infrastructure_asset",
                            timestamp=datetime.utcnow(),
                            data={
                                "lat": lat,
                                "lng": lng,
                                "asset_type": asset_type,
                                "osm_id": osm_id,
                                "osm_type": osm_type,
                                "name": name,
                                "tags": tags,
                            },
                            raw_data=el,
                        )
                    )

                if events:
                    logger.info("Overpass fetched %d infrastructure assets", len(events))
                return events

        except Exception as e:
            logger.error("Overpass fetch error: %s", e)
            raise

    async def transform(self, raw: RawEvent) -> TimelineEvent:
        """Transform Overpass element to timeline event."""
        data = raw.data
        return TimelineEvent(
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"overpass:{raw.entity_id}")),
            entity_type="infrastructure_asset",
            timestamp=raw.timestamp,
            lat=data["lat"],
            lng=data["lng"],
            altitude=None,
            properties={
                "asset_type": data.get("asset_type"),
                "osm_id": data.get("osm_id"),
                "osm_type": data.get("osm_type"),
                "name": data.get("name"),
                "tags": data.get("tags", {}),
            },
            source="overpass",
            quality_score=calculate_quality_score(
                data, "infrastructure_asset", "overpass", raw.timestamp
            ),
        )
