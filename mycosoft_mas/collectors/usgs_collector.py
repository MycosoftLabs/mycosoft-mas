"""
USGS Collector - February 6, 2026

Collects earthquake data from USGS.
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

import aiohttp

from .base_collector import BaseCollector, RawEvent, TimelineEvent
from .quality_scorer import calculate_quality_score

logger = logging.getLogger(__name__)


class USGSCollector(BaseCollector):
    """
    Collects earthquake data from USGS Earthquake Hazards API.
    
    API: https://earthquake.usgs.gov/fdsnws/event/1/
    """
    
    name = "usgs"
    entity_type = "earthquake"
    poll_interval_seconds = 60  # Check every minute
    
    def __init__(self, min_magnitude: float = 2.5):
        super().__init__()
        self.min_magnitude = min_magnitude
        self.base_url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
        self._session: Optional[aiohttp.ClientSession] = None
        self._last_fetch_time: Optional[datetime] = None
    
    async def initialize(self) -> None:
        self._session = aiohttp.ClientSession()
    
    async def cleanup(self) -> None:
        if self._session:
            await self._session.close()
    
    async def fetch(self) -> List[RawEvent]:
        """Fetch recent earthquakes from USGS."""
        if not self._session:
            await self.initialize()
        
        # Query for last hour if first fetch, otherwise since last fetch
        end_time = datetime.utcnow()
        if self._last_fetch_time:
            start_time = self._last_fetch_time - timedelta(minutes=5)  # Overlap for safety
        else:
            start_time = end_time - timedelta(hours=1)
        
        params = {
            "format": "geojson",
            "starttime": start_time.isoformat(),
            "endtime": end_time.isoformat(),
            "minmagnitude": self.min_magnitude,
            "orderby": "time",
        }
        
        try:
            async with self._session.get(self.base_url, params=params, timeout=30) as resp:
                if resp.status != 200:
                    logger.error(f"USGS error: {resp.status}")
                    return []
                
                data = await resp.json()
                self._last_fetch_time = end_time
                
                events = []
                for feature in data.get("features", []):
                    props = feature.get("properties", {})
                    geom = feature.get("geometry", {})
                    coords = geom.get("coordinates", [0, 0, 0])
                    
                    events.append(RawEvent(
                        source="usgs",
                        entity_id=feature.get("id", str(uuid.uuid4())),
                        entity_type="earthquake",
                        timestamp=datetime.utcfromtimestamp(props.get("time", 0) / 1000),
                        data={
                            "lng": coords[0],
                            "lat": coords[1],
                            "depth": coords[2],
                            "magnitude": props.get("mag"),
                            "mag_type": props.get("magType"),
                            "place": props.get("place"),
                            "url": props.get("url"),
                            "felt": props.get("felt"),
                            "alert": props.get("alert"),
                            "status": props.get("status"),
                            "tsunami": props.get("tsunami"),
                            "sig": props.get("sig"),
                            "net": props.get("net"),
                        },
                        raw_data=feature
                    ))
                
                logger.info(f"USGS fetched {len(events)} earthquakes")
                return events
                
        except Exception as e:
            logger.error(f"USGS fetch error: {e}")
            raise
    
    async def transform(self, raw: RawEvent) -> TimelineEvent:
        """Transform USGS data to timeline event."""
        data = raw.data
        
        return TimelineEvent(
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"usgs:{raw.entity_id}")),
            entity_type="earthquake",
            timestamp=raw.timestamp,
            lat=data["lat"],
            lng=data["lng"],
            altitude=-data.get("depth", 0) * 1000,  # Convert to negative meters
            properties={
                "magnitude": data["magnitude"],
                "mag_type": data.get("mag_type"),
                "depth_km": data.get("depth"),
                "place": data.get("place"),
                "url": data.get("url"),
                "felt": data.get("felt"),
                "alert": data.get("alert"),
                "tsunami": data.get("tsunami"),
                "significance": data.get("sig"),
            },
            source="usgs",
            quality_score=calculate_quality_score(data, "earthquake", "usgs", raw.timestamp)
        )