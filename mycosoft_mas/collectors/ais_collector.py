"""
AIS Collector - February 6, 2026

Collects vessel data from AIS feeds (marine traffic).
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


class AISCollector(BaseCollector):
    name = "ais"
    entity_type = "vessel"
    poll_interval_seconds = 30

    def __init__(self, api_url: Optional[str] = None):
        super().__init__()
        self.api_url = api_url or os.getenv("AIS_API_URL", "https://api.aisstream.io/v1/stream")
        self._session: Optional[aiohttp.ClientSession] = None
        self._api_key = os.getenv("AISSTREAM_API_KEY", "")

    async def initialize(self) -> None:
        self._session = aiohttp.ClientSession()

    async def cleanup(self) -> None:
        if self._session:
            await self._session.close()

    async def fetch(self) -> List[RawEvent]:
        if not self._session:
            await self.initialize()
        events: List[RawEvent] = []
        proxy_url = os.getenv("OEI_AIS_PROXY", "").strip()
        if proxy_url:
            try:
                async with self._session.get(proxy_url, timeout=aiohttp.ClientTimeout(total=25)) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()
                    events = self._parse_feed(data)
            except Exception as e:
                logger.error("AIS proxy error: " + str(e))
                raise
        elif self._api_key:
            try:
                async with self._session.get(
                    self.api_url,
                    headers={"Authorization": "Bearer " + self._api_key},
                    timeout=aiohttp.ClientTimeout(total=25),
                ) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()
                    events = self._parse_feed(data)
            except Exception as e:
                logger.error("AIS fetch error: " + str(e))
                raise
        if events:
            logger.info("AIS fetched %d vessels", len(events))
        return events

    def _parse_feed(self, data: Any) -> List[RawEvent]:
        events: List[RawEvent] = []
        now = datetime.utcnow()
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("lat") is not None and item.get("lng") is not None:
                    events.append(RawEvent(
                        source="ais", entity_id=str(item.get("mmsi", uuid.uuid4())), entity_type="vessel",
                        timestamp=now, data={"lat": float(item["lat"]), "lng": float(item["lng"]), **item}, raw_data=item,
                    ))
        elif isinstance(data, dict):
            for item in data.get("features", data.get("vessels", data.get("data", []))):
                if not isinstance(item, dict):
                    continue
                geom = item.get("geometry", {})
                props = item.get("properties", item)
                coords = geom.get("coordinates", [])
                lng = lat = None
                if len(coords) >= 2:
                    lng, lat = coords[0], coords[1]
                else:
                    lat, lng = props.get("lat"), props.get("lng") or props.get("longitude")
                if lat is not None and lng is not None:
                    events.append(RawEvent(
                        source="ais", entity_id=str(props.get("mmsi", uuid.uuid4())), entity_type="vessel",
                        timestamp=now, data={"lat": float(lat), "lng": float(lng), "mmsi": props.get("mmsi"), **props}, raw_data=item,
                    ))
        return events

    async def transform(self, raw: RawEvent) -> TimelineEvent:
        data = raw.data
        return TimelineEvent(
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, "ais:" + str(data.get("mmsi", raw.entity_id)))),
            entity_type="vessel", timestamp=raw.timestamp, lat=data["lat"], lng=data["lng"], altitude=None,
            properties={"mmsi": data.get("mmsi"), "name": data.get("name"), "speed": data.get("speed"), "heading": data.get("heading")},
            source="ais", quality_score=calculate_quality_score(data, "vessel", "ais", raw.timestamp),
        )
