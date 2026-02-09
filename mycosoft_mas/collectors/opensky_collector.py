"""
OpenSky Collector - February 6, 2026

Collects aircraft data from OpenSky Network.
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp

from .base_collector import BaseCollector, RawEvent, TimelineEvent
from .quality_scorer import calculate_quality_score

logger = logging.getLogger(__name__)


class OpenSkyCollector(BaseCollector):
    """
    Collects live aircraft positions from OpenSky Network.
    
    API: https://opensky-network.org/apidoc/rest.html
    """
    
    name = "opensky"
    entity_type = "aircraft"
    poll_interval_seconds = 10  # Free tier rate limit
    
    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        super().__init__()
        self.username = username or os.getenv("OPENSKY_USERNAME")
        self.password = password or os.getenv("OPENSKY_PASSWORD")
        self.base_url = "https://opensky-network.org/api"
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Bounding box for queries (can be configured)
        self.bbox: Optional[tuple] = None  # (lamin, lamax, lomin, lomax)
    
    async def initialize(self) -> None:
        auth = None
        if self.username and self.password:
            auth = aiohttp.BasicAuth(self.username, self.password)
        
        self._session = aiohttp.ClientSession(auth=auth)
    
    async def cleanup(self) -> None:
        if self._session:
            await self._session.close()
    
    async def fetch(self) -> List[RawEvent]:
        """Fetch aircraft states from OpenSky."""
        if not self._session:
            await self.initialize()
        
        url = f"{self.base_url}/states/all"
        params = {}
        
        if self.bbox:
            params["lamin"] = self.bbox[0]
            params["lamax"] = self.bbox[1]
            params["lomin"] = self.bbox[2]
            params["lomax"] = self.bbox[3]
        
        try:
            async with self._session.get(url, params=params, timeout=30) as resp:
                if resp.status == 429:
                    logger.warning("OpenSky rate limited")
                    await asyncio.sleep(60)
                    return []
                
                if resp.status != 200:
                    logger.error(f"OpenSky error: {resp.status}")
                    return []
                
                data = await resp.json()
                
                events = []
                states = data.get("states", [])
                
                for state in states:
                    if state[5] is None or state[6] is None:
                        continue  # Skip without position
                    
                    events.append(RawEvent(
                        source="opensky",
                        entity_id=state[0] or str(uuid.uuid4()),  # ICAO24
                        entity_type="aircraft",
                        timestamp=datetime.utcfromtimestamp(data.get("time", datetime.utcnow().timestamp())),
                        data={
                            "icao24": state[0],
                            "callsign": (state[1] or "").strip(),
                            "origin_country": state[2],
                            "time_position": state[3],
                            "last_contact": state[4],
                            "lng": state[5],
                            "lat": state[6],
                            "altitude": state[7] or state[13],  # baro_altitude or geo_altitude
                            "on_ground": state[8],
                            "velocity": state[9],
                            "heading": state[10],
                            "vertical_rate": state[11],
                            "squawk": state[14],
                        },
                        raw_data=state
                    ))
                
                logger.info(f"OpenSky fetched {len(events)} aircraft")
                return events
                
        except Exception as e:
            logger.error(f"OpenSky fetch error: {e}")
            raise
    
    async def transform(self, raw: RawEvent) -> TimelineEvent:
        """Transform OpenSky data to timeline event."""
        data = raw.data
        
        return TimelineEvent(
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"opensky:{data['icao24']}")),
            entity_type="aircraft",
            timestamp=raw.timestamp,
            lat=data["lat"],
            lng=data["lng"],
            altitude=data.get("altitude"),
            properties={
                "icao24": data["icao24"],
                "callsign": data["callsign"],
                "origin_country": data["origin_country"],
                "velocity": data.get("velocity"),
                "heading": data.get("heading"),
                "vertical_rate": data.get("vertical_rate"),
                "on_ground": data.get("on_ground", False),
                "squawk": data.get("squawk"),
            },
            source="opensky",
            quality_score=calculate_quality_score(data, "aircraft", "opensky", raw.timestamp)
        )