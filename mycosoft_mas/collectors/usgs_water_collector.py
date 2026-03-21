"""
USGS Water Data Collector - March 14, 2026

Collects streamflow and gage height from USGS NWIS Instantaneous Values API.
Use for: rivers, dams, watershed awareness in CREP and worldstate.
API: https://waterservices.usgs.gov/nwis/iv/
"""

import logging
import uuid
from datetime import datetime
from typing import List, Optional

import aiohttp

from .base_collector import BaseCollector, RawEvent, TimelineEvent
from .quality_scorer import calculate_quality_score

logger = logging.getLogger(__name__)

# Default stream gage site IDs (USGS 8-digit codes)
# 01646500: Potomac at Washington DC, 01447800: Delaware at Trenton NJ
DEFAULT_SITES = ["01646500", "01447800"]


class USGSWaterCollector(BaseCollector):
    """
    Collects streamflow (00060 cfs) and gage height (00065 ft) from USGS NWIS.
    """

    name = "usgs_water"
    entity_type = "environmental_field"
    poll_interval_seconds = 3600  # 1 hour - streamflow changes less frequently

    def __init__(self, site_ids: Optional[List[str]] = None):
        super().__init__()
        self.site_ids = site_ids or DEFAULT_SITES
        self.base_url = "https://waterservices.usgs.gov/nwis/iv/"
        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize(self) -> None:
        self._session = aiohttp.ClientSession(
            headers={"User-Agent": "(Mycosoft CREP, contact@mycosoft.com)"}
        )

    async def cleanup(self) -> None:
        if self._session:
            await self._session.close()

    async def fetch(self) -> List[RawEvent]:
        """Fetch streamflow and gage height from USGS NWIS IV."""
        if not self._session:
            await self.initialize()

        # parameterCd: 00060=streamflow cfs, 00065=gage height ft
        params = {
            "format": "json",
            "sites": ",".join(self.site_ids),
            "parameterCd": "00060,00065",
            "siteStatus": "all",
        }

        events: List[RawEvent] = []

        try:
            async with self._session.get(
                self.base_url, params=params, timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status != 200:
                    logger.error("USGS Water error: %s", resp.status)
                    return []

                data = await resp.json()
                value_data = data.get("value", {})
                time_series = value_data.get("timeSeries", [])

                for ts_obj in time_series:
                    source_info = ts_obj.get("sourceInfo", {})
                    geo = source_info.get("geolocation", {})
                    geo_loc = geo.get("geogLocation", {})

                    lat = geo_loc.get("latitude")
                    lng = geo_loc.get("longitude")
                    if lat is None or lng is None:
                        continue

                    try:
                        lat = float(lat)
                        lng = float(lng)
                    except (TypeError, ValueError):
                        continue

                    site_code = source_info.get("siteCode", [{}])[0].get("value", "unknown")
                    site_name = source_info.get("siteName", site_code)

                    variable = ts_obj.get("variable", {})
                    var_code = variable.get("variableCode", [{}])[0].get("value", "unknown")
                    unit = variable.get("unit", {}).get("unitCode", "")

                    values = ts_obj.get("values", [])
                    if not values:
                        continue
                    val_list = values[0].get("value", [])
                    if not val_list:
                        continue

                    v = val_list[0]
                    date_str = v.get("dateTime", "")
                    val_str = v.get("value")
                    try:
                        value = float(val_str) if val_str is not None else None
                    except (TypeError, ValueError):
                        value = None

                    ts = datetime.utcnow()
                    if date_str:
                        try:
                            ts = datetime.fromisoformat(date_str.replace("Z", "+00:00")).replace(
                                tzinfo=None
                            )
                        except Exception:
                            pass

                    if value is not None:
                        param_name = "streamflow_cfs" if var_code == "00060" else "gage_height_ft"
                        entity_id = f"{site_code}:{var_code}:{date_str}:{val_str}"
                        events.append(
                            RawEvent(
                                source="usgs_water",
                                entity_id=entity_id,
                                entity_type="environmental_field",
                                timestamp=ts,
                                data={
                                    "lat": lat,
                                    "lng": lng,
                                    "value": value,
                                    "parameter": param_name,
                                    "site_code": site_code,
                                    "site_name": site_name,
                                    "variable_code": var_code,
                                    "units": unit,
                                },
                                raw_data=v,
                            )
                        )

        except Exception as e:
            logger.error("USGS Water fetch error: %s", e)
            raise

        if events:
            logger.info("USGS Water fetched %d stream/gage readings", len(events))
        return events

    async def transform(self, raw: RawEvent) -> TimelineEvent:
        """Transform USGS Water reading to timeline event."""
        data = raw.data
        return TimelineEvent(
            id=str(
                uuid.uuid5(
                    uuid.NAMESPACE_DNS,
                    f"usgs_water:{raw.entity_id}",
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
                "site_code": data.get("site_code"),
                "site_name": data.get("site_name"),
                "variable_code": data.get("variable_code"),
                "units": data.get("units"),
            },
            source="usgs_water",
            quality_score=calculate_quality_score(
                data, "environmental_field", "usgs_water", raw.timestamp
            ),
        )
