"""
Base Collector - February 6, 2026

Abstract base class for all data collectors.
"""

import asyncio
import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from hashlib import sha1
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# MINDEX earth/ingest layer names (transport.aircraft, transport.vessels, etc.)
ENTITY_LAYER_MAP: Dict[str, str] = {
    "aircraft": "aircraft",
    "vessel": "vessels",
    "satellite": "satellites",
    "earthquake": "earthquakes",
}

EARTH_INGEST_BATCH_SIZE = 200

MOVER_UPSERT_SQL: Dict[str, str] = {
    "aircraft": """
        INSERT INTO transport.aircraft (source, source_id, callsign, icao24,
            location, heading, altitude_ft, ground_speed_kts, observed_at, properties)
        VALUES ($1, $2, $3, $4,
            ST_SetSRID(ST_MakePoint($5, $6), 4326)::geography,
            $7, $8, $9, COALESCE($10::timestamptz, NOW()), $11::jsonb)
        ON CONFLICT (source, source_id) WHERE source_id IS NOT NULL DO UPDATE SET
            callsign = EXCLUDED.callsign,
            icao24 = EXCLUDED.icao24,
            location = EXCLUDED.location,
            heading = EXCLUDED.heading,
            altitude_ft = EXCLUDED.altitude_ft,
            ground_speed_kts = EXCLUDED.ground_speed_kts,
            observed_at = EXCLUDED.observed_at,
            properties = EXCLUDED.properties
    """,
    "vessels": """
        INSERT INTO transport.vessels (source, source_id, name, mmsi,
            location, speed_knots, heading, observed_at, properties)
        VALUES ($1, $2, $3, $4,
            ST_SetSRID(ST_MakePoint($5, $6), 4326)::geography,
            $7, $8, COALESCE($9::timestamptz, NOW()), $10::jsonb)
        ON CONFLICT (source, source_id) WHERE source_id IS NOT NULL DO UPDATE SET
            name = EXCLUDED.name,
            mmsi = EXCLUDED.mmsi,
            location = EXCLUDED.location,
            speed_knots = EXCLUDED.speed_knots,
            heading = EXCLUDED.heading,
            observed_at = EXCLUDED.observed_at,
            properties = EXCLUDED.properties
    """,
    "satellites": """
        INSERT INTO space.satellites (source, source_id, name, norad_id,
            orbit_type, location, altitude_km, observed_at, properties)
        VALUES ($1, $2, $3, $4,
            $5, ST_SetSRID(ST_MakePoint($6, $7), 4326)::geography,
            $8, COALESCE($9::timestamptz, NOW()), $10::jsonb)
        ON CONFLICT (source, source_id) WHERE source_id IS NOT NULL DO UPDATE SET
            name = EXCLUDED.name,
            norad_id = EXCLUDED.norad_id,
            orbit_type = EXCLUDED.orbit_type,
            location = EXCLUDED.location,
            altitude_km = EXCLUDED.altitude_km,
            observed_at = EXCLUDED.observed_at,
            properties = EXCLUDED.properties
    """,
}


class CollectorStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0


@dataclass
class RawEvent:
    """Raw event from data source."""

    source: str
    entity_id: str
    entity_type: str
    timestamp: datetime
    data: Dict[str, Any]
    raw_data: Optional[Any] = None


@dataclass
class TimelineEvent:
    """Processed event for timeline storage."""

    id: str
    entity_type: str
    timestamp: datetime
    lat: float
    lng: float
    altitude: Optional[float] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    quality_score: float = 1.0


@dataclass
class UnifiedEntity:
    """Unified entity payload emitted by collectors."""

    id: str
    type: str
    geometry: Dict[str, Any]
    state: Dict[str, Any]
    time: Dict[str, Any]
    confidence: float
    source: str
    properties: Dict[str, Any]
    s2_cell: str


@dataclass
class CollectorStats:
    """Runtime statistics for a collector."""

    total_fetches: int = 0
    successful_fetches: int = 0
    failed_fetches: int = 0
    total_events: int = 0
    last_fetch_time: Optional[datetime] = None
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    avg_fetch_duration_ms: float = 0.0


class BaseCollector(ABC):
    """
    Abstract base class for data collectors.

    Collectors fetch data from external sources and transform it
    for ingestion into MINDEX.
    """

    name: str = "base"
    entity_type: str = "unknown"
    poll_interval_seconds: int = 60
    retry_config: RetryConfig = field(default_factory=RetryConfig)

    def __init__(self):
        self.status = CollectorStatus.IDLE
        self.stats = CollectorStats()
        self.retry_config = RetryConfig()
        self._stop_event = asyncio.Event()
        self._pool = None

    async def initialize(self) -> None:
        """Initialize collector resources."""

    async def cleanup(self) -> None:
        """Cleanup collector resources."""

    @abstractmethod
    async def fetch(self) -> List[RawEvent]:
        """
        Fetch raw data from the source.

        Returns:
            List of raw events
        """

    @abstractmethod
    async def transform(self, raw: RawEvent) -> TimelineEvent:
        """
        Transform raw event to timeline event.

        Args:
            raw: Raw event from source

        Returns:
            Processed timeline event
        """

    def _compute_s2_cell(self, lat: float, lng: float, level: int = 14) -> str:
        """
        Compute a stable cell identifier for spatial sharding.

        We use a deterministic hash fallback to avoid hard dependency on native bindings
        while still producing a repeatable cell key for channel routing.
        """
        precision_lat = round(lat, max(1, level // 2))
        precision_lng = round(lng, max(1, level // 2))
        digest = sha1(f"{precision_lat}:{precision_lng}:{level}".encode("utf-8")).hexdigest()
        return digest[:16]

    def to_unified_entity(self, event: TimelineEvent) -> UnifiedEntity:
        observed_at = event.timestamp.isoformat()
        geometry = {
            "type": "Point",
            "coordinates": (
                [event.lng, event.lat]
                if event.altitude is None
                else [event.lng, event.lat, event.altitude]
            ),
        }
        return UnifiedEntity(
            id=event.id,
            type=event.entity_type,
            geometry=geometry,
            state={
                "altitude": event.altitude,
                "classification": (
                    event.properties.get("classification")
                    if isinstance(event.properties, dict)
                    else None
                ),
            },
            time={
                "observed_at": observed_at,
                "valid_from": observed_at,
            },
            confidence=event.quality_score,
            source=event.source,
            properties=event.properties,
            s2_cell=self._compute_s2_cell(event.lat, event.lng),
        )

    def _event_to_ingest_payload(self, event: TimelineEvent) -> Dict[str, Any]:
        """Map TimelineEvent to MINDEX IngestEntity JSON."""
        props = dict(event.properties or {})
        source_id = str(props.get("icao24") or props.get("mmsi") or props.get("norad_id") or event.id)
        name = (
            props.get("callsign")
            or props.get("name")
            or props.get("icao24")
            or f"{event.entity_type}:{source_id}"
        )

        if event.entity_type == "aircraft":
            if event.altitude is not None:
                props.setdefault("altitude", event.altitude * 3.28084)
            vel = props.get("velocity")
            if vel is not None and "speed" not in props:
                props["speed"] = float(vel) * 1.94384
            props.setdefault("icao24", source_id)

        if event.entity_type == "vessel":
            props.setdefault("mmsi", source_id)

        if event.entity_type == "satellite":
            props.setdefault("norad_id", source_id)
            if event.altitude is not None:
                props.setdefault("altitude_km", event.altitude / 1000.0)

        ts = event.timestamp
        occurred_at = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)

        return {
            "source": event.source,
            "source_id": source_id,
            "name": str(name).strip() or source_id,
            "entity_type": event.entity_type,
            "lat": event.lat,
            "lng": event.lng,
            "occurred_at": occurred_at,
            "properties": props,
        }

    def _mover_database_url(self) -> Optional[str]:
        return os.getenv("DATABASE_URL") or os.getenv("MINDEX_DATABASE_URL")

    def _mover_ingest_mode(self) -> str:
        """direct = asyncpg to Postgres; api = MINDEX earth/ingest; auto = direct then api."""
        return os.getenv("MOVER_INGEST_MODE", "auto").strip().lower()

    async def _ingest_mover_direct(
        self, by_layer: Dict[str, List[Dict[str, Any]]]
    ) -> int:
        """Write MOVER layers directly to Postgres (same DB as MAS DATABASE_URL)."""
        import asyncpg

        dsn = self._mover_database_url()
        if not dsn:
            return 0

        inserted = 0
        conn = await asyncpg.connect(dsn=dsn, timeout=30)
        try:
            for layer, entities in by_layer.items():
                sql = MOVER_UPSERT_SQL.get(layer)
                if not sql:
                    continue
                batch = entities[:EARTH_INGEST_BATCH_SIZE]
                for idx, ent in enumerate(batch):
                    props = ent.get("properties") or {}
                    try:
                        if layer == "aircraft":
                            await conn.execute(
                                sql,
                                ent["source"],
                                ent.get("source_id"),
                                ent.get("name"),
                                props.get("icao24"),
                                ent["lng"],
                                ent["lat"],
                                props.get("heading"),
                                props.get("altitude"),
                                props.get("speed"),
                                ent.get("occurred_at"),
                                json.dumps(props),
                            )
                        elif layer == "vessels":
                            await conn.execute(
                                sql,
                                ent["source"],
                                ent.get("source_id"),
                                ent.get("name"),
                                props.get("mmsi"),
                                ent["lng"],
                                ent["lat"],
                                props.get("speed"),
                                props.get("heading"),
                                ent.get("occurred_at"),
                                json.dumps(props),
                            )
                        elif layer == "satellites":
                            await conn.execute(
                                sql,
                                ent["source"],
                                ent.get("source_id"),
                                ent.get("name"),
                                props.get("norad_id"),
                                props.get("orbit_type"),
                                ent["lng"],
                                ent["lat"],
                                props.get("altitude_km"),
                                ent.get("occurred_at"),
                                json.dumps(props),
                            )
                        inserted += 1
                        if idx % 50 == 49:
                            await asyncio.sleep(0)
                    except Exception as exc:
                        logger.warning(
                            "%s direct ingest %s/%s failed: %s",
                            self.name,
                            layer,
                            ent.get("source_id"),
                            exc,
                        )
        finally:
            await conn.close()

        if inserted:
            logger.info("%s direct DB ingest: %s rows", self.name, inserted)
        return inserted

    async def _ingest_mover_api(
        self, by_layer: Dict[str, List[Dict[str, Any]]]
    ) -> int:
        import httpx

        base = os.getenv("MINDEX_API_URL", "http://192.168.0.189:8000").rstrip("/")
        token = os.getenv("MINDEX_INTERNAL_TOKEN", os.getenv("MAS_INTERNAL_TOKEN", ""))
        headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if token:
            headers["X-Internal-Token"] = token

        total_inserted = 0
        async with httpx.AsyncClient(timeout=60.0) as client:
            for layer, entities in by_layer.items():
                url = f"{base}/api/mindex/earth/ingest"
                for offset in range(0, len(entities), EARTH_INGEST_BATCH_SIZE):
                    chunk = entities[offset : offset + EARTH_INGEST_BATCH_SIZE]
                    resp = await client.post(
                        url,
                        json={"layer": layer, "entities": chunk},
                        headers=headers,
                    )
                    if resp.status_code not in (200, 201):
                        logger.error(
                            "%s earth ingest %s HTTP %s: %s",
                            self.name,
                            layer,
                            resp.status_code,
                            resp.text[:400],
                        )
                        continue
                    data = resp.json()
                    inserted = int(data.get("inserted", 0))
                    errors = int(data.get("errors", 0))
                    if errors:
                        logger.warning(
                            "%s earth ingest %s: inserted=%s errors=%s",
                            self.name,
                            layer,
                            inserted,
                            errors,
                        )
                    else:
                        logger.info(
                            "%s earth ingest %s: inserted=%s", self.name, layer, inserted
                        )
                    total_inserted += inserted
        return total_inserted

    async def ingest(self, events: List[TimelineEvent]) -> int:
        """
        Ingest MOVER events into MINDEX Postgres (direct asyncpg) with API fallback.

        Args:
            events: List of timeline events

        Returns:
            Number of entities inserted/updated
        """
        if not events:
            return 0

        by_layer: Dict[str, List[Dict[str, Any]]] = {}
        for event in events:
            layer = ENTITY_LAYER_MAP.get(event.entity_type)
            if not layer:
                logger.warning(
                    "%s: no earth ingest layer for entity_type=%s", self.name, event.entity_type
                )
                continue
            try:
                payload = self._event_to_ingest_payload(event)
            except Exception as exc:
                logger.warning(
                    "%s: payload mapping failed for %s: %s",
                    self.name,
                    event.entity_type,
                    exc,
                )
                continue
            by_layer.setdefault(layer, []).append(payload)

        if not by_layer:
            return 0

        mode = self._mover_ingest_mode()
        total_inserted = 0
        try:
            if mode in ("direct", "auto") and self._mover_database_url():
                total_inserted = await self._ingest_mover_direct(by_layer)
            if mode == "api" or (mode == "auto" and total_inserted == 0):
                api_inserted = await self._ingest_mover_api(by_layer)
                if api_inserted:
                    total_inserted = api_inserted

            self.stats.total_events += total_inserted
            return total_inserted

        except Exception as e:
            logger.error(f"{self.name} ingest error: {e}")
            return total_inserted

    async def run_once(self) -> List[TimelineEvent]:
        """Run a single fetch-transform-ingest cycle."""
        start_time = datetime.utcnow()

        try:
            # Fetch
            raw_events = await self.fetch()

            # Transform
            events = []
            for raw in raw_events:
                try:
                    event = await self.transform(raw)
                    events.append(event)
                except Exception as e:
                    logger.warning(f"{self.name} transform error: {e}")

            # Ingest
            await self.ingest(events)

            # Update stats
            self.stats.total_fetches += 1
            self.stats.successful_fetches += 1
            self.stats.last_fetch_time = datetime.utcnow()

            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.stats.avg_fetch_duration_ms = (
                self.stats.avg_fetch_duration_ms * (self.stats.total_fetches - 1) + duration_ms
            ) / self.stats.total_fetches

            return events

        except Exception as e:
            self.stats.failed_fetches += 1
            self.stats.last_error = str(e)
            self.stats.last_error_time = datetime.utcnow()
            logger.error(f"{self.name} run_once error: {e}")
            raise

    async def run_loop(self) -> None:
        """Run continuous collection loop."""
        self.status = CollectorStatus.RUNNING
        logger.info(f"{self.name} collector started")

        retry_count = 0
        retry_delay = self.retry_config.initial_delay

        while not self._stop_event.is_set():
            try:
                await self.run_once()
                retry_count = 0
                retry_delay = self.retry_config.initial_delay

            except Exception as e:
                self.status = CollectorStatus.ERROR
                retry_count += 1

                if retry_count >= self.retry_config.max_retries:
                    logger.error(f"{self.name} max retries reached, stopping")
                    break

                logger.warning(f"{self.name} error (retry {retry_count}): {e}")
                await asyncio.sleep(retry_delay)
                retry_delay = min(
                    retry_delay * self.retry_config.exponential_base, self.retry_config.max_delay
                )
                continue

            # Wait for next poll
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.poll_interval_seconds)
            except asyncio.TimeoutError:
                pass  # Normal timeout, continue loop

        self.status = CollectorStatus.STOPPED
        logger.info(f"{self.name} collector stopped")

    def stop(self) -> None:
        """Signal the collector to stop."""
        self._stop_event.set()

    def get_status(self) -> Dict[str, Any]:
        """Get collector status and stats."""
        return {
            "name": self.name,
            "entity_type": self.entity_type,
            "status": getattr(self.status, "value", self.status),
            "poll_interval": self.poll_interval_seconds,
            "stats": {
                "total_fetches": self.stats.total_fetches,
                "successful_fetches": self.stats.successful_fetches,
                "failed_fetches": self.stats.failed_fetches,
                "total_events": self.stats.total_events,
                "last_fetch_time": (
                    self.stats.last_fetch_time.isoformat() if self.stats.last_fetch_time else None
                ),
                "last_error": self.stats.last_error,
                "last_error_time": (
                    self.stats.last_error_time.isoformat() if self.stats.last_error_time else None
                ),
                "avg_fetch_duration_ms": round(self.stats.avg_fetch_duration_ms, 2),
            },
        }
