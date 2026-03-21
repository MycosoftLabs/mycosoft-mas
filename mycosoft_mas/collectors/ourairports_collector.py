"""
OurAirports Collector - March 14, 2026

Collects airport metadata from OurAirports open data (CSV).
Use for: aviation entity enrichment in MINDEX and CREP.
Data: https://davidmegginson.github.io/ourairports-data/airports.csv
      https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/airports.csv
"""

import csv
import io
import logging
import uuid
from datetime import datetime
from typing import List, Optional

import aiohttp

from .base_collector import BaseCollector, RawEvent, TimelineEvent
from .quality_scorer import calculate_quality_score

logger = logging.getLogger(__name__)

DATA_URLS = [
    "https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/airports.csv",
    "https://davidmegginson.github.io/ourairports-data/airports.csv",
]


class OurAirportsCollector(BaseCollector):
    """
    Collects airport metadata from OurAirports CSV.
    Emits infrastructure_asset events for airports.
    Handles 503/unavailable gracefully - returns empty on failure.
    """

    name = "ourairports"
    entity_type = "infrastructure_asset"
    poll_interval_seconds = 86400  # 24h - data updates nightly

    def __init__(self, max_airports: int = 5000):
        super().__init__()
        self.max_airports = max_airports
        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize(self) -> None:
        self._session = aiohttp.ClientSession(
            headers={"User-Agent": "(Mycosoft CREP, contact@mycosoft.com)"}
        )

    async def cleanup(self) -> None:
        if self._session:
            await self._session.close()

    async def fetch(self) -> List[RawEvent]:
        """Fetch airport data from OurAirports CSV."""
        if not self._session:
            await self.initialize()

        for url in DATA_URLS:
            try:
                async with self._session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    if resp.status in (503, 502, 500, 404):
                        logger.warning(
                            "OurAirports %s returned %s, trying next URL",
                            url,
                            resp.status,
                        )
                        continue

                    if resp.status != 200:
                        continue

                    text = await resp.text()
                    events = self._parse_csv(text)
                    if events:
                        logger.info(
                            "OurAirports fetched %d airports from %s",
                            len(events),
                            url,
                        )
                    return events

            except aiohttp.ClientError as e:
                logger.warning("OurAirports fetch from %s failed: %s", url, e)
                continue
            except Exception as e:
                logger.error("OurAirports parse error: %s", e)
                raise

        logger.warning("OurAirports: all URLs unavailable, returning empty")
        return []

    def _parse_csv(self, text: str) -> List[RawEvent]:
        """Parse OurAirports CSV into RawEvents."""
        events: List[RawEvent] = []
        reader = csv.DictReader(io.StringIO(text))

        for row in reader:
            try:
                lat_str = row.get("latitude_deg", "").strip()
                lon_str = row.get("longitude_deg", "").strip()
                if not lat_str or not lon_str:
                    continue
                lat = float(lat_str)
                lng = float(lon_str)

                ident = row.get("ident", "").strip() or row.get("local_code", "").strip()
                name = row.get("name", "").strip()
                airport_type = row.get("type", "").strip()
                iso_country = row.get("iso_country", "").strip()
                iso_region = row.get("iso_region", "").strip()
                elevation = row.get("elevation_ft", "")
                icao = row.get("ident", "").strip()
                iata = row.get("iata_code", "").strip()

                entity_id = ident or str(uuid.uuid4())
                events.append(
                    RawEvent(
                        source="ourairports",
                        entity_id=entity_id,
                        entity_type="infrastructure_asset",
                        timestamp=datetime.utcnow(),
                        data={
                            "lat": lat,
                            "lng": lng,
                            "asset_type": "airport",
                            "name": name,
                            "icao": icao,
                            "iata": iata,
                            "airport_type": airport_type,
                            "iso_country": iso_country,
                            "iso_region": iso_region,
                            "elevation_ft": (
                                int(elevation) if elevation and elevation != "\\N" else None
                            ),
                        },
                        raw_data=dict(row),
                    )
                )

                if len(events) >= self.max_airports:
                    break

            except (ValueError, KeyError) as e:
                logger.debug("OurAirports skip row: %s", e)
                continue

        return events

    async def transform(self, raw: RawEvent) -> TimelineEvent:
        """Transform OurAirports row to timeline event."""
        data = raw.data
        return TimelineEvent(
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"ourairports:{raw.entity_id}")),
            entity_type="infrastructure_asset",
            timestamp=raw.timestamp,
            lat=data["lat"],
            lng=data["lng"],
            altitude=data.get("elevation_ft"),
            properties={
                "asset_type": "airport",
                "name": data.get("name"),
                "icao": data.get("icao"),
                "iata": data.get("iata"),
                "airport_type": data.get("airport_type"),
                "iso_country": data.get("iso_country"),
                "iso_region": data.get("iso_region"),
            },
            source="ourairports",
            quality_score=calculate_quality_score(
                data, "infrastructure_asset", "ourairports", raw.timestamp
            ),
        )
