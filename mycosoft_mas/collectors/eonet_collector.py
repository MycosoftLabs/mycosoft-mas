"""
NASA EONET Collector - March 14, 2026

Collects natural hazard events (fires, storms, volcanoes, severe events) from NASA EONET.
Use for: CREP hazard layers, MYCA event awareness, MINDEX event history.
API: https://eonet.gsfc.nasa.gov/api/v3/events
"""

import logging
import uuid
from datetime import datetime
from typing import List, Optional

import aiohttp

from .base_collector import BaseCollector, RawEvent, TimelineEvent
from .quality_scorer import calculate_quality_score

logger = logging.getLogger(__name__)


class EONETCollector(BaseCollector):
    """
    Collects natural hazard events from NASA EONET (Earth Observatory Natural Event Tracker).
    """

    name = "eonet"
    entity_type = "hazard"
    poll_interval_seconds = 900  # 15 min - EONET updates less frequently

    def __init__(self, limit: int = 100, status: str = "open"):
        super().__init__()
        self.limit = limit
        self.status = status
        self.base_url = "https://eonet.gsfc.nasa.gov/api/v3/events"
        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize(self) -> None:
        self._session = aiohttp.ClientSession(
            headers={"User-Agent": "(Mycosoft CREP, contact@mycosoft.com)"}
        )

    async def cleanup(self) -> None:
        if self._session:
            await self._session.close()

    async def fetch(self) -> List[RawEvent]:
        """Fetch open natural events from NASA EONET."""
        if not self._session:
            await self.initialize()

        params = {"limit": self.limit, "status": self.status}

        try:
            async with self._session.get(
                self.base_url, params=params, timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status != 200:
                    logger.error("EONET error: %s", resp.status)
                    return []

                data = await resp.json()
                events: List[RawEvent] = []

                for ev in data.get("events", []):
                    geoms = ev.get("geometry", [])
                    if not geoms:
                        continue
                    g = geoms[0]
                    coords = g.get("coordinates", [0, 0])
                    lng, lat = float(coords[0]), float(coords[1])
                    date_str = g.get("date")
                    ts = datetime.utcnow()
                    if date_str:
                        try:
                            ts = datetime.fromisoformat(date_str.replace("Z", "+00:00")).replace(
                                tzinfo=None
                            )
                        except Exception:
                            pass
                    cats = ev.get("categories", [])
                    cat_id = cats[0]["id"] if cats else "unknown"
                    cat_title = cats[0].get("title", cat_id) if cats else "Unknown"
                    mag_val = g.get("magnitudeValue")
                    mag_unit = g.get("magnitudeUnit", "")
                    sources_list = ev.get("sources", [])
                    source_url = sources_list[0].get("url", "") if sources_list else ""

                    events.append(
                        RawEvent(
                            source="eonet",
                            entity_id=ev.get("id", str(uuid.uuid4())),
                            entity_type="hazard",
                            timestamp=ts,
                            data={
                                "lat": lat,
                                "lng": lng,
                                "title": ev.get("title"),
                                "description": ev.get("description"),
                                "category_id": cat_id,
                                "category_title": cat_title,
                                "magnitude_value": mag_val,
                                "magnitude_unit": mag_unit,
                                "link": ev.get("link"),
                                "source_url": source_url,
                                "closed": ev.get("closed"),
                            },
                            raw_data=ev,
                        )
                    )

                if events:
                    logger.info("EONET fetched %d hazard events", len(events))
                return events

        except Exception as e:
            logger.error("EONET fetch error: %s", e)
            raise

    async def transform(self, raw: RawEvent) -> TimelineEvent:
        """Transform EONET event to timeline event."""
        data = raw.data
        return TimelineEvent(
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"eonet:{raw.entity_id}")),
            entity_type="hazard",
            timestamp=raw.timestamp,
            lat=data["lat"],
            lng=data["lng"],
            altitude=None,
            properties={
                "title": data.get("title"),
                "description": data.get("description"),
                "category_id": data.get("category_id"),
                "category_title": data.get("category_title"),
                "magnitude_value": data.get("magnitude_value"),
                "magnitude_unit": data.get("magnitude_unit"),
                "link": data.get("link"),
                "source_url": data.get("source_url"),
            },
            source="eonet",
            quality_score=calculate_quality_score(data, "hazard", "eonet", raw.timestamp),
        )
