"""
NOAA CO-OPS Collector - March 14, 2026

Collects water level data from NOAA Tides and Currents CO-OPS API.
Use for: port, coast, flooding, maritime context in CREP and worldstate.
API: https://api.tidesandcurrents.noaa.gov/api/prod/datagetter
"""

import logging
import uuid
from datetime import datetime
from typing import List, Optional, Tuple

import aiohttp

from .base_collector import BaseCollector, RawEvent, TimelineEvent
from .quality_scorer import calculate_quality_score

logger = logging.getLogger(__name__)

# Default water level stations: station_id -> (lat, lng, name)
DEFAULT_STATIONS: List[Tuple[str, float, float, str]] = [
    ("9414290", 37.8063, -122.4659, "San Francisco"),
    ("8518750", 40.7006, -74.0142, "The Battery NY"),
    ("8724580", 24.5556, -81.8081, "Key West FL"),
    ("8651370", 36.1833, -75.7464, "Duck NC"),
    ("1612340", 21.3069, -157.8667, "Honolulu HI"),
]


class NOAA_COOPSCollector(BaseCollector):
    """
    Collects water level (tide) data from NOAA CO-OPS.
    """

    name = "noaa_coops"
    entity_type = "environmental_field"
    poll_interval_seconds = 1800  # 30 min - tides change slowly

    def __init__(self, stations: Optional[List[Tuple[str, float, float, str]]] = None):
        super().__init__()
        self.stations = stations or DEFAULT_STATIONS
        self.base_url = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize(self) -> None:
        self._session = aiohttp.ClientSession(
            headers={"User-Agent": "(Mycosoft CREP, contact@mycosoft.com)"}
        )

    async def cleanup(self) -> None:
        if self._session:
            await self._session.close()

    async def fetch(self) -> List[RawEvent]:
        """Fetch latest water levels from NOAA CO-OPS for configured stations."""
        if not self._session:
            await self.initialize()

        events: List[RawEvent] = []

        for station_id, lat, lng, name in self.stations:
            params = {
                "date": "latest",
                "station": station_id,
                "product": "water_level",
                "datum": "MLLW",
                "time_zone": "gmt",
                "units": "metric",
                "format": "json",
                "application": "Mycosoft",
            }

            try:
                async with self._session.get(
                    self.base_url, params=params, timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    if resp.status != 200:
                        logger.warning(
                            "NOAA CO-OPS station %s error: %s", station_id, resp.status
                        )
                        continue

                    data = await resp.json()
                    data_points = data.get("data", [])

                    if not data_points:
                        # No data or error - try to include error message
                        err = data.get("error", {})
                        if isinstance(err, dict) and err.get("message"):
                            logger.warning(
                                "NOAA CO-OPS station %s: %s",
                                station_id,
                                err.get("message"),
                            )
                        continue

                    # Use most recent reading
                    pt = data_points[0]
                    t_str = pt.get("t", "")
                    v_raw = pt.get("v")
                    try:
                        value = float(v_raw) if v_raw is not None else None
                    except (TypeError, ValueError):
                        value = None

                    ts = datetime.utcnow()
                    if t_str:
                        try:
                            ts = datetime.fromisoformat(
                                t_str.replace("Z", "+00:00")
                            ).replace(tzinfo=None)
                        except Exception:
                            pass

                    if value is not None:
                        entity_id = f"{station_id}:{t_str}:{v_raw}"
                        events.append(
                            RawEvent(
                                source="noaa_coops",
                                entity_id=entity_id,
                                entity_type="environmental_field",
                                timestamp=ts,
                                data={
                                    "lat": lat,
                                    "lng": lng,
                                    "value": value,
                                    "parameter": "water_level_m",
                                    "station_id": station_id,
                                    "station_name": name,
                                    "datum": "MLLW",
                                    "units": "meters",
                                },
                                raw_data=pt,
                            )
                        )

            except Exception as e:
                logger.warning(
                    "NOAA CO-OPS fetch error for station %s: %s", station_id, e
                )
                continue

        if events:
            logger.info("NOAA CO-OPS fetched %d water level readings", len(events))
        return events

    async def transform(self, raw: RawEvent) -> TimelineEvent:
        """Transform NOAA CO-OPS reading to timeline event."""
        data = raw.data
        return TimelineEvent(
            id=str(
                uuid.uuid5(
                    uuid.NAMESPACE_DNS,
                    f"noaa_coops:{raw.entity_id}",
                )
            ),
            entity_type="environmental_field",
            timestamp=raw.timestamp,
            lat=data["lat"],
            lng=data["lng"],
            altitude=None,
            properties={
                "parameter": data.get("parameter"),
                "value": data.get("value"),
                "station_id": data.get("station_id"),
                "station_name": data.get("station_name"),
                "datum": data.get("datum"),
                "units": data.get("units"),
            },
            source="noaa_coops",
            quality_score=calculate_quality_score(
                data, "environmental_field", "noaa_coops", raw.timestamp
            ),
        )
