"""
NASA FIRMS Collector - March 14, 2026

Collects wildfire hotspots from NASA FIRMS (Fire Information for Resource Management).
Use for: CREP hazard overlays, MYCA event grounding, Earth2 event context.
API: https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/{SOURCE}/{AREA}/{DAYS}
Requires FIRMS_API_KEY or MAP_KEY env var. Returns empty (degraded) if no key.
"""

import csv
import io
import logging
import os
import uuid
from datetime import datetime
from typing import List, Optional

import aiohttp

from .base_collector import BaseCollector, RawEvent, TimelineEvent
from .quality_scorer import calculate_quality_score

logger = logging.getLogger(__name__)


class FIRMSCollector(BaseCollector):
    """
    Collects wildfire hotspot detections from NASA FIRMS.
    """

    name = "firms"
    entity_type = "hazard"
    poll_interval_seconds = 3600  # 1 hour - NRT updates periodically

    def __init__(self, bbox: str = "world", days: int = 1):
        super().__init__()
        self.bbox = bbox  # "world" or "west,south,east,north"
        self.days = min(5, max(1, days))
        self.base_url = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
        self._session: Optional[aiohttp.ClientSession] = None
        self._api_key: Optional[str] = None

    async def initialize(self) -> None:
        self._api_key = os.environ.get("FIRMS_API_KEY") or os.environ.get("MAP_KEY")
        self._session = aiohttp.ClientSession(
            headers={"User-Agent": "(Mycosoft CREP, contact@mycosoft.com)"}
        )

    async def cleanup(self) -> None:
        if self._session:
            await self._session.close()

    async def fetch(self) -> List[RawEvent]:
        """Fetch wildfire hotspots from NASA FIRMS. Returns [] if no API key."""
        if not self._session:
            await self.initialize()

        if not self._api_key:
            logger.debug(
                "FIRMS collector: no FIRMS_API_KEY or MAP_KEY - returning empty (degraded)"
            )
            return []

        # VIIRS_SNPP_NRT - near real-time
        url = f"{self.base_url}/{self._api_key}/VIIRS_SNPP_NRT/" f"{self.bbox}/{self.days}"

        events: List[RawEvent] = []

        try:
            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status != 200:
                    logger.warning("FIRMS error: %s", resp.status)
                    return []

                text = await resp.text()
                if not text.strip():
                    return []

                reader = csv.DictReader(io.StringIO(text))
                for row in reader:
                    try:
                        lat = float(row.get("latitude", 0))
                        lng = float(row.get("longitude", 0))
                    except (TypeError, ValueError):
                        continue

                    acq_date = row.get("acq_date", "")
                    acq_time = row.get("acq_time", "0000")
                    brightness = row.get("brightness")
                    confidence = row.get("confidence")
                    frp = row.get("frp")

                    ts = datetime.utcnow()
                    if acq_date and acq_time:
                        try:
                            # acq_time is HHMM
                            h = int(acq_time[:2]) if len(acq_time) >= 2 else 0
                            m = int(acq_time[2:4]) if len(acq_time) >= 4 else 0
                            ts = datetime.strptime(
                                f"{acq_date} {h:02d}:{m:02d}:00",
                                "%Y-%m-%d %H:%M:%S",
                            )
                        except Exception:
                            pass

                    try:
                        bright_val = float(brightness) if brightness else None
                    except (TypeError, ValueError):
                        bright_val = None

                    try:
                        frp_val = float(frp) if frp else None
                    except (TypeError, ValueError):
                        frp_val = None

                    entity_id = (
                        f"{row.get('latitude')}:{row.get('longitude')}:"
                        f"{acq_date}:{acq_time}:{row.get('bright_t31', '')}"
                    )
                    events.append(
                        RawEvent(
                            source="firms",
                            entity_id=entity_id,
                            entity_type="hazard",
                            timestamp=ts,
                            data={
                                "lat": lat,
                                "lng": lng,
                                "title": "Wildfire hotspot",
                                "category_id": "wildfire",
                                "brightness": bright_val,
                                "confidence": confidence,
                                "frp": frp_val,
                                "acq_date": acq_date,
                                "acq_time": acq_time,
                                "satellite": row.get("satellite"),
                            },
                            raw_data=row,
                        )
                    )

        except Exception as e:
            logger.error("FIRMS fetch error: %s", e)
            raise

        if events:
            logger.info("FIRMS fetched %d wildfire hotspots", len(events))
        return events

    async def transform(self, raw: RawEvent) -> TimelineEvent:
        """Transform FIRMS hotspot to timeline event."""
        data = raw.data
        return TimelineEvent(
            id=str(
                uuid.uuid5(
                    uuid.NAMESPACE_DNS,
                    f"firms:{raw.entity_id}",
                )
            ),
            entity_type="hazard",
            timestamp=raw.timestamp,
            lat=data["lat"],
            lng=data["lng"],
            altitude=None,
            properties={
                "title": data.get("title"),
                "category_id": data.get("category_id"),
                "brightness": data.get("brightness"),
                "confidence": data.get("confidence"),
                "frp": data.get("frp"),
                "acq_date": data.get("acq_date"),
                "satellite": data.get("satellite"),
            },
            source="firms",
            quality_score=calculate_quality_score(data, "hazard", "firms", raw.timestamp),
        )
