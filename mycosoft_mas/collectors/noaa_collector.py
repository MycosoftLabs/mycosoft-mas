"""
NOAA Collector - February 6, 2026

Collects weather alerts and storm data from NWS API.
"""

import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp

from .base_collector import BaseCollector, RawEvent, TimelineEvent
from .quality_scorer import calculate_quality_score

logger = logging.getLogger(__name__)


class NOAACollector(BaseCollector):
    name = "noaa"
    entity_type = "weather"
    poll_interval_seconds = 300

    def __init__(self):
        super().__init__()
        self.base_url = os.getenv("NWS_API_URL", "https://api.weather.gov")
        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize(self) -> None:
        self._session = aiohttp.ClientSession(
            headers={"User-Agent": "(Mycosoft CREP, contact@mycosoft.com)"}
        )

    async def cleanup(self) -> None:
        if self._session:
            await self._session.close()

    async def fetch(self) -> List[RawEvent]:
        if not self._session:
            await self.initialize()
        events: List[RawEvent] = []
        try:
            async with self._session.get(
                f"{self.base_url}/alerts/active?status=actual&message_type=alert",
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                if resp.status != 200:
                    logger.warning("NOAA alerts returned %s", resp.status)
                    return []
                data = await resp.json()
                for feat in data.get("features", []):
                    props = feat.get("properties", {})
                    geom = feat.get("geometry", {})
                    coords = geom.get("coordinates", []) if geom else []
                    lat = lng = None
                    if coords and coords[0]:
                        ring = coords[0] if isinstance(coords[0][0], (list, tuple)) else coords
                        if ring:
                            first = ring[0] if isinstance(ring[0], (list, tuple)) else ring
                            lng, lat = first[0], first[1]
                    if lat is None:
                        lat, lng = 0.0, 0.0
                    events.append(RawEvent(
                        source="noaa",
                        entity_id=props.get("id", str(uuid.uuid4())),
                        entity_type="weather",
                        timestamp=datetime.utcnow(),
                        data={
                            "lat": lat, "lng": lng,
                            "event": props.get("event"),
                            "severity": props.get("severity"),
                            "headline": props.get("headline"),
                            "description": props.get("description"),
                            "areaDesc": props.get("areaDesc"),
                        },
                        raw_data=feat,
                    ))
            if events:
                logger.info("NOAA fetched %d alerts", len(events))
        except Exception as e:
            logger.error("NOAA fetch error: %s", e)
            raise
        return events

    async def transform(self, raw: RawEvent) -> TimelineEvent:
        data = raw.data
        return TimelineEvent(
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, "noaa:" + raw.entity_id)),
            entity_type="weather", timestamp=raw.timestamp, lat=data["lat"], lng=data["lng"], altitude=None,
            properties={
                "event": data.get("event"), "severity": data.get("severity"),
                "headline": data.get("headline"), "areaDesc": data.get("areaDesc"),
            },
            source="noaa", quality_score=calculate_quality_score(data, "weather", "noaa", raw.timestamp),
        )
