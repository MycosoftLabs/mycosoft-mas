# CREP Phase 5: Additional Data Collectors - February 6, 2026

## Overview

Phase 5 core is implemented in `mycosoft_mas/collectors/` (OpenSky, USGS, NORAD, orchestrator, circuit breaker, audit log). This document adds **AIS (vessels)** and **NOAA (weather)** collectors per the Implementation Architecture.

**Copy the code below into the MAS repo** (paths relative to repo root):

- `mycosoft_mas/collectors/ais_collector.py` ← content in section "AIS Collector"
- `mycosoft_mas/collectors/noaa_collector.py` ← content in section "NOAA Collector"

Then:

1. In `mycosoft_mas/collectors/__init__.py`, add:
   - `from .ais_collector import AISCollector`
   - `from .noaa_collector import NOAACollector`
   - Export `"AISCollector"` and `"NOAACollector"` in `__all__`.

2. In `mycosoft_mas/collectors/orchestrator.py`, in `start_default_collectors()`, add:
   - `from .ais_collector import AISCollector`
   - `from .noaa_collector import NOAACollector`
   - `orch.register(AISCollector())`
   - `orch.register(NOAACollector())`

---

## AIS Collector

**File:** `mycosoft_mas/collectors/ais_collector.py`

```python
"""
AIS Collector - February 6, 2026

Collects vessel data from AIS feeds (marine traffic).
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
                logger.error(f"AIS proxy error: {e}")
                raise
        elif self._api_key:
            try:
                async with self._session.get(
                    self.api_url,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    timeout=aiohttp.ClientTimeout(total=25),
                ) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()
                    events = self._parse_feed(data)
            except Exception as e:
                logger.error(f"AIS fetch error: {e}")
                raise
        if events:
            logger.info(f"AIS fetched {len(events)} vessels")
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
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"ais:{data.get('mmsi', raw.entity_id)}")),
            entity_type="vessel", timestamp=raw.timestamp, lat=data["lat"], lng=data["lng"], altitude=None,
            properties={"mmsi": data.get("mmsi"), "name": data.get("name"), "speed": data.get("speed"), "heading": data.get("heading")},
            source="ais", quality_score=calculate_quality_score(data, "vessel", "ais", raw.timestamp),
        )
```

---

## NOAA Collector

**File:** `mycosoft_mas/collectors/noaa_collector.py`

```python
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
    poll_interval_seconds = 300  # 5 min

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
                    logger.warning(f"NOAA alerts returned {resp.status}")
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
                logger.info(f"NOAA fetched {len(events)} alerts")
        except Exception as e:
            logger.error(f"NOAA fetch error: {e}")
            raise
        return events

    async def transform(self, raw: RawEvent) -> TimelineEvent:
        data = raw.data
        return TimelineEvent(
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"noaa:{raw.entity_id}")),
            entity_type="weather", timestamp=raw.timestamp, lat=data["lat"], lng=data["lng"], altitude=None,
            properties={
                "event": data.get("event"), "severity": data.get("severity"),
                "headline": data.get("headline"), "areaDesc": data.get("areaDesc"),
            },
            source="noaa", quality_score=calculate_quality_score(data, "weather", "noaa", raw.timestamp),
        )
```

---

## Phase 6 (Performance) – Already Implemented

- **WebSocket pub/sub:** `mycosoft_mas/realtime/pubsub.py` – `WebSocketHub`, Redis pub/sub, channels `aircraft:{region}`, `vessels:{region}`, `earthquakes:all`, etc.
- **Health checks:** `mycosoft_mas/monitoring/health_check.py` – database, Redis, collectors; liveness/readiness.
- **Metrics:** `mycosoft_mas/monitoring/metrics.py` – Prometheus-style counters/gauges.

**Expose in FastAPI (if not already):**

- `GET /health` → `get_health_checker().check_all()` (full component status)
- `GET /ready` → `get_health_checker().readiness()` (liveness/readiness for Kubernetes)
- `GET /metrics` → metrics registry export (Prometheus scrape)
- `WebSocket /ws/timeline` (or `/ws/realtime`) → `get_hub().connect()`, then client sends subscribe message with channels (e.g. `aircraft:global`, `vessels:global`). Ingesters call `get_hub().publish(channel, payload)` so clients receive live updates.

---

## Summary

| Phase | Item | Status |
|-------|------|--------|
| 5 | Base, OpenSky, USGS, NORAD, orchestrator, quality_scorer | Done |
| 5 | AIS collector (vessels) | Add via this doc |
| 5 | NOAA collector (weather) | Add via this doc |
| 6 | Pub/sub, health, metrics | Done |
