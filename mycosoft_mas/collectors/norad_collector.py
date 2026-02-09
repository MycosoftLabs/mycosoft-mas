"""
NORAD Collector - February 6, 2026

Collects satellite TLE data from Space-Track.
"""

import logging
import os
import uuid
from datetime import datetime
from typing import List, Optional

import aiohttp

from .base_collector import BaseCollector, RawEvent, TimelineEvent
from .quality_scorer import calculate_quality_score

logger = logging.getLogger(__name__)


class NORADCollector(BaseCollector):
    """
    Collects satellite TLE data from Space-Track.org.
    
    Requires registration for API access.
    """
    
    name = "norad"
    entity_type = "satellite"
    poll_interval_seconds = 3600  # Update hourly
    
    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
        super().__init__()
        self.username = username or os.getenv("SPACETRACK_USERNAME")
        self.password = password or os.getenv("SPACETRACK_PASSWORD")
        self.base_url = "https://www.space-track.org"
        self._session: Optional[aiohttp.ClientSession] = None
        self._authenticated = False
    
    async def initialize(self) -> None:
        self._session = aiohttp.ClientSession()
    
    async def cleanup(self) -> None:
        if self._session:
            await self._session.close()
    
    async def _authenticate(self) -> bool:
        """Authenticate with Space-Track."""
        if not self.username or not self.password:
            logger.warning("NORAD: No credentials, using CelesTrak fallback")
            return False
        
        try:
            async with self._session.post(
                f"{self.base_url}/ajaxauth/login",
                data={"identity": self.username, "password": self.password}
            ) as resp:
                if resp.status == 200:
                    self._authenticated = True
                    return True
                logger.error(f"Space-Track auth failed: {resp.status}")
                return False
        except Exception as e:
            logger.error(f"Space-Track auth error: {e}")
            return False
    
    async def fetch(self) -> List[RawEvent]:
        """Fetch TLEs from Space-Track or CelesTrak."""
        if not self._session:
            await self.initialize()
        
        # Try Space-Track first
        if self.username and not self._authenticated:
            await self._authenticate()
        
        events = []
        
        if self._authenticated:
            events = await self._fetch_spacetrack()
        else:
            events = await self._fetch_celestrak()
        
        logger.info(f"NORAD fetched {len(events)} satellites")
        return events
    
    async def _fetch_celestrak(self) -> List[RawEvent]:
        """Fallback to CelesTrak for TLEs."""
        url = "https://celestrak.org/NORAD/elements/gp.php"
        
        events = []
        catalogs = ["stations", "active", "starlink"]  # Major categories
        
        for catalog in catalogs:
            try:
                async with self._session.get(
                    url,
                    params={"GROUP": catalog, "FORMAT": "json"},
                    timeout=30
                ) as resp:
                    if resp.status != 200:
                        continue
                    
                    data = await resp.json()
                    
                    for sat in data:
                        events.append(RawEvent(
                            source="celestrak",
                            entity_id=str(sat.get("NORAD_CAT_ID")),
                            entity_type="satellite",
                            timestamp=datetime.utcnow(),
                            data={
                                "norad_id": sat.get("NORAD_CAT_ID"),
                                "name": sat.get("OBJECT_NAME"),
                                "object_type": sat.get("OBJECT_TYPE"),
                                "epoch": sat.get("EPOCH"),
                                "mean_motion": sat.get("MEAN_MOTION"),
                                "eccentricity": sat.get("ECCENTRICITY"),
                                "inclination": sat.get("INCLINATION"),
                                "ra_of_asc_node": sat.get("RA_OF_ASC_NODE"),
                                "arg_of_pericenter": sat.get("ARG_OF_PERICENTER"),
                                "mean_anomaly": sat.get("MEAN_ANOMALY"),
                                "tle_line1": sat.get("TLE_LINE1"),
                                "tle_line2": sat.get("TLE_LINE2"),
                            },
                            raw_data=sat
                        ))
            except Exception as e:
                logger.warning(f"CelesTrak {catalog} error: {e}")
        
        return events
    
    async def _fetch_spacetrack(self) -> List[RawEvent]:
        """Fetch from Space-Track API."""
        url = f"{self.base_url}/basicspacedata/query/class/gp/EPOCH/%3Enow-1/orderby/NORAD_CAT_ID/format/json"
        
        try:
            async with self._session.get(url, timeout=60) as resp:
                if resp.status != 200:
                    return await self._fetch_celestrak()
                
                data = await resp.json()
                
                events = []
                for sat in data[:1000]:  # Limit to 1000
                    events.append(RawEvent(
                        source="spacetrack",
                        entity_id=str(sat.get("NORAD_CAT_ID")),
                        entity_type="satellite",
                        timestamp=datetime.utcnow(),
                        data={
                            "norad_id": sat.get("NORAD_CAT_ID"),
                            "name": sat.get("OBJECT_NAME"),
                            "object_type": sat.get("OBJECT_TYPE"),
                            "epoch": sat.get("EPOCH"),
                            "mean_motion": float(sat.get("MEAN_MOTION", 0)),
                            "eccentricity": float(sat.get("ECCENTRICITY", 0)),
                            "inclination": float(sat.get("INCLINATION", 0)),
                            "ra_of_asc_node": float(sat.get("RA_OF_ASC_NODE", 0)),
                            "arg_of_pericenter": float(sat.get("ARG_OF_PERICENTER", 0)),
                            "mean_anomaly": float(sat.get("MEAN_ANOMALY", 0)),
                            "tle_line1": sat.get("TLE_LINE1"),
                            "tle_line2": sat.get("TLE_LINE2"),
                        },
                        raw_data=sat
                    ))
                
                return events
                
        except Exception as e:
            logger.error(f"Space-Track error: {e}")
            return await self._fetch_celestrak()
    
    async def transform(self, raw: RawEvent) -> TimelineEvent:
        """Transform TLE data to timeline event."""
        data = raw.data
        
        # Calculate approximate position from orbital elements
        # For accurate position, use SGP4 propagation
        lat, lng, alt = self._estimate_position(data)
        
        return TimelineEvent(
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"norad:{data['norad_id']}")),
            entity_type="satellite",
            timestamp=raw.timestamp,
            lat=lat,
            lng=lng,
            altitude=alt,
            properties={
                "norad_id": data["norad_id"],
                "name": data["name"],
                "object_type": data.get("object_type"),
                "epoch": data.get("epoch"),
                "inclination": data.get("inclination"),
                "eccentricity": data.get("eccentricity"),
                "mean_motion": data.get("mean_motion"),
                "tle_line1": data.get("tle_line1"),
                "tle_line2": data.get("tle_line2"),
            },
            source=raw.source,
            quality_score=calculate_quality_score(data, "satellite", "norad", raw.timestamp)
        )
    
    def _estimate_position(self, data: dict) -> tuple:
        """
        Estimate position from orbital elements.
        For accurate position, use SGP4 library.
        """
        # Simplified estimate - for visualization only
        inc = data.get("inclination", 0)
        raan = data.get("ra_of_asc_node", 0)
        
        # Very rough approximation
        lat = inc * 0.5  # Bounded by inclination
        lng = (raan + (datetime.utcnow().timestamp() / 86400 * 360)) % 360 - 180
        
        # Estimate altitude from mean motion
        mm = data.get("mean_motion", 15)  # Revs per day
        if mm > 0:
            # Higher mean motion = lower orbit
            alt = 400000 / (mm / 15)  # Very rough meters
        else:
            alt = 400000
        
        return lat, lng, alt