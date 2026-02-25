"""
EarthLIVE Seismic Collector - USGS Earthquake API

Fetches real earthquake data from USGS.
https://earthquake.usgs.gov/earthquakes/feed/v1.0/

Created: February 25, 2026
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

USGS_BASE = "https://earthquake.usgs.gov/earthquakes/feed/v1.0"
USGS_QUERY = "https://earthquake.usgs.gov/fdsnws/event/1/query"


async def fetch_usgs_earthquakes(
    feed: str = "all_hour",
    limit: int = 20,
) -> Dict[str, Any]:
    """
    Fetch recent earthquakes from USGS.
    feed: all_hour, all_day, all_week, significant_hour, significant_day, etc.
    """
    try:
        import httpx
    except ImportError:
        logger.warning("httpx not installed; EarthLIVE seismic collector unavailable")
        return {"type": "FeatureCollection", "features": []}

    url = f"{USGS_BASE}/summary/{feed}.geojson"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                url,
                headers={"Accept": "application/json", "User-Agent": "Mycosoft-EarthLIVE/1.0"},
            )
            resp.raise_for_status()
            data = resp.json()
            features = data.get("features", [])[:limit]
            return {
                "type": "FeatureCollection",
                "metadata": data.get("metadata", {}),
                "features": features,
            }
    except Exception as e:
        logger.warning("USGS fetch failed: %s", e)
        return {"type": "FeatureCollection", "features": []}


class SeismicCollector:
    """Collect seismic data from USGS."""

    def __init__(self, feed: str = "all_day", limit: int = 20):
        self.feed = feed
        self.limit = limit

    async def collect(self) -> Dict[str, Any]:
        """Collect recent earthquakes."""
        data = await fetch_usgs_earthquakes(feed=self.feed, limit=self.limit)
        features = data.get("features", [])

        events = []
        for f in features:
            props = f.get("properties", {})
            geom = f.get("geometry", {})
            coords = geom.get("coordinates", [0, 0, 0])
            events.append({
                "id": f.get("id"),
                "magnitude": props.get("mag"),
                "place": props.get("place"),
                "time_ms": props.get("time"),
                "latitude": coords[1] if len(coords) > 1 else None,
                "longitude": coords[0] if len(coords) > 0 else None,
                "depth_km": coords[2] if len(coords) > 2 else None,
                "title": props.get("title"),
                "url": props.get("url"),
            })

        return {
            "source": "usgs",
            "feed": self.feed,
            "count": len(events),
            "events": events,
            "metadata": data.get("metadata", {}),
        }
