"""
Transit GTFS-RT collector — Jun 15, 2026 (Earth Sim §1.3).

Polls SoCal agencies + Amtraker; writes transit.* tables in MINDEX.
Flag-gated: TRANSIT_RT_COLLECTOR_ENABLED=1 (never auto-starts in prod without Morgan).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import aiohttp

from .base_collector import BaseCollector, CollectorStatus, RawEvent, TimelineEvent
from .transit_gtfs import (
    DecodedVehicle,
    StaticCatalog,
    decode_amtraker_trains,
    decode_trip_updates_pb,
    decode_vehicle_positions_pb,
    merge_trip_etas,
    parse_static_gtfs_zip,
)

logger = logging.getLogger(__name__)

FETCH_TIMEOUT_SEC = float(os.getenv("TRANSIT_RT_FETCH_TIMEOUT_SEC", "12"))
STATIC_REFRESH_SEC = int(os.getenv("TRANSIT_STATIC_REFRESH_SEC", str(24 * 3600)))


@dataclass
class AgencyFeed:
    slug: str
    agency: str
    id_prefix: str
    vehicle_type_default: int
    vp_url: str
    tu_url: Optional[str] = None
    static_gtfs_url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    format: str = "gtfs-rt"  # gtfs-rt | amtraker-json


def _build_agency_feeds() -> List[AgencyFeed]:
    """SoCal-focused feeds per EARTH_SIM_DATA_EXPANSION_HANDOFF §1.3."""
    key_511 = os.getenv("TRANSIT_511_API_KEY", "").strip()
    key_sd = os.getenv("SDMTS_API_KEY", os.getenv("TRANSIT_SDMTS_API_KEY", key_511)).strip()
    key_metrolink = os.getenv("METROLINK_API_KEY", "").strip()
    key_nctd = os.getenv("NCTD_API_KEY", os.getenv("TRANSIT_NCTD_API_KEY", "")).strip()
    mts_agency = os.getenv("MTS_511_AGENCY_CODE", "MTS").strip()

    feeds: List[AgencyFeed] = []

    if key_sd or os.getenv("MTS_GTFS_RT_VP_URL"):
        vp = os.getenv(
            "MTS_GTFS_RT_VP_URL",
            f"http://api.511.org/transit/VehiclePositions?api_key={key_sd}&agency={mts_agency}"
            if key_sd
            else "",
        )
        tu = os.getenv(
            "MTS_GTFS_RT_TU_URL",
            f"http://api.511.org/transit/TripUpdates?api_key={key_sd}&agency={mts_agency}"
            if key_sd
            else None,
        )
        if vp:
            feeds.append(
                AgencyFeed(
                    slug="mts",
                    agency="MTS",
                    id_prefix="mts",
                    vehicle_type_default=0,
                    vp_url=vp,
                    tu_url=tu,
                    static_gtfs_url=os.getenv(
                        "MTS_STATIC_GTFS_URL",
                        "https://www.sdmts.com/google_transit/google_transit.zip",
                    ),
                )
            )

    if key_nctd or os.getenv("NCTD_GTFS_RT_VP_URL"):
        vp = os.getenv(
            "NCTD_GTFS_RT_VP_URL",
            "https://www.gonctd.com/google_transit/gtfs-realtime/GTFS-RT-VehiclePositions.pb",
        )
        tu = os.getenv(
            "NCTD_GTFS_RT_TU_URL",
            "https://www.gonctd.com/google_transit/gtfs-realtime/GTFS-RT-TripUpdates.pb",
        )
        feeds.append(
            AgencyFeed(
                slug="nctd",
                agency="NCTD",
                id_prefix="nctd",
                vehicle_type_default=2,
                vp_url=vp,
                tu_url=tu,
                static_gtfs_url=os.getenv(
                    "NCTD_STATIC_GTFS_URL",
                    "https://www.gonctd.com/files/gtfs/google_transit.zip",
                ),
                headers={"api-key": key_nctd} if key_nctd else None,
            )
        )

    feeds.append(
        AgencyFeed(
            slug="amtrak",
            agency="Amtrak",
            id_prefix="amtrak",
            vehicle_type_default=2,
            vp_url=os.getenv("AMTRAKER_V3_URL", "https://api-v3.amtraker.com/v3/trains"),
            format="amtraker-json",
        )
    )

    if key_metrolink:
        feeds.append(
            AgencyFeed(
                slug="metrolink",
                agency="Metrolink",
                id_prefix="metrolink",
                vehicle_type_default=2,
                vp_url=f"https://api.simplifytransit.com/metrolink/vehicles/vehicles.pb?key={key_metrolink}",
                tu_url=f"https://api.simplifytransit.com/metrolink/tripupdates/tripupdates.pb?key={key_metrolink}",
                static_gtfs_url=os.getenv(
                    "METROLINK_STATIC_GTFS_URL",
                    "https://www.metrolinktrains.com/google_transit.zip",
                ),
            )
        )

    if key_511:
        for slug, agency, op, rtype in (
            ("caltrain", "Caltrain", "CT", 2),
        ):
            feeds.append(
                AgencyFeed(
                    slug=slug,
                    agency=agency,
                    id_prefix=slug,
                    vehicle_type_default=rtype,
                    vp_url=f"http://api.511.org/transit/VehiclePositions?api_key={key_511}&agency={op}",
                    tu_url=f"http://api.511.org/transit/TripUpdates?api_key={key_511}&agency={op}",
                    static_gtfs_url=os.getenv(
                        "CALTRAIN_STATIC_GTFS_URL",
                        "https://www.caltrain.com/files/gtfs/Caltrain-GTFS.zip",
                    ),
                )
            )

    return feeds


class TransitRTCollector(BaseCollector):
    """
    GTFS-RT + Amtraker collector for CREP liveTransit layer.

    Does not block other collectors — own poll loop via orchestrator circuit breaker.
    """

    name = "transit_rt"
    entity_type = "transit_vehicle"
    poll_interval_seconds = int(os.getenv("TRANSIT_RT_POLL_INTERVAL_SEC", "20"))

    def __init__(self) -> None:
        super().__init__()
        self._session: Optional[aiohttp.ClientSession] = None
        self._pool = None
        self._feeds = _build_agency_feeds()
        self._static_loaded: Dict[str, float] = {}
        self._catalogs: Dict[str, StaticCatalog] = {}

    async def initialize(self) -> None:
        timeout = aiohttp.ClientTimeout(total=FETCH_TIMEOUT_SEC)
        self._session = aiohttp.ClientSession(
            timeout=timeout,
            headers={"User-Agent": "Mycosoft-MAS-TransitRT/1.0"},
        )

    async def cleanup(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def fetch(self) -> List[RawEvent]:
        return []

    async def transform(self, raw: RawEvent) -> TimelineEvent:
        raise NotImplementedError("transit_rt uses custom ingest")

    async def run_once(self) -> List[TimelineEvent]:
        """Override: fetch all feeds, upsert MINDEX transit tables."""
        if not self._session:
            await self.initialize()

        start = datetime.now(tz=timezone.utc)
        all_vehicles: List[DecodedVehicle] = []
        seen_agencies: List[str] = []

        for feed in self._feeds:
            try:
                await self._maybe_load_static(feed)
                vehicles = await self._fetch_feed(feed)
                all_vehicles.extend(vehicles)
                seen_agencies.append(feed.agency)
            except Exception as exc:
                logger.warning("transit_rt feed %s failed: %s", feed.slug, exc)

        ingested = await self._ingest_transit(all_vehicles, seen_agencies)

        self.stats.total_fetches += 1
        self.stats.successful_fetches += 1
        self.stats.last_fetch_time = datetime.utcnow()
        self.stats.total_events += ingested

        duration_ms = (datetime.now(tz=timezone.utc) - start).total_seconds() * 1000
        n = self.stats.total_fetches
        self.stats.avg_fetch_duration_ms = (
            self.stats.avg_fetch_duration_ms * (n - 1) + duration_ms
        ) / n

        return []

    async def _fetch_feed(self, feed: AgencyFeed) -> List[DecodedVehicle]:
        assert self._session is not None
        headers = dict(feed.headers or {})
        async with self._session.get(feed.vp_url, headers=headers) as resp:
            if resp.status != 200:
                logger.warning("transit_rt %s VP HTTP %s", feed.slug, resp.status)
                return []
            body = await resp.read()

        if feed.format == "amtraker-json":
            data = json.loads(body.decode("utf-8"))
            return decode_amtraker_trains(data, agency=feed.agency, id_prefix=feed.id_prefix)

        vehicles = decode_vehicle_positions_pb(body, feed.agency, feed.id_prefix)

        if feed.tu_url:
            try:
                async with self._session.get(feed.tu_url, headers=headers) as tu_resp:
                    if tu_resp.status == 200:
                        tu_body = await tu_resp.read()
                        etas = decode_trip_updates_pb(tu_body)
                        merge_trip_etas(vehicles, etas)
            except Exception as exc:
                logger.debug("transit_rt %s TU skip: %s", feed.slug, exc)

        catalog = self._catalogs.get(feed.slug)
        if catalog:
            for v in vehicles:
                if v.route_id and v.route_id in catalog.routes:
                    r = catalog.routes[v.route_id]
                    v.route_short_name = v.route_short_name or r.route_short_name
                    v.route_color = v.route_color or r.route_color
                    v.route_type = r.route_type if r.route_type is not None else feed.vehicle_type_default
                else:
                    v.route_type = feed.vehicle_type_default
        else:
            for v in vehicles:
                v.route_type = feed.vehicle_type_default

        return vehicles

    async def _maybe_load_static(self, feed: AgencyFeed) -> None:
        if not feed.static_gtfs_url:
            return
        now = time.time()
        last = self._static_loaded.get(feed.slug, 0)
        if now - last < STATIC_REFRESH_SEC and feed.slug in self._catalogs:
            return
        assert self._session is not None
        try:
            async with self._session.get(feed.static_gtfs_url) as resp:
                if resp.status != 200:
                    return
                data = await resp.read()
            catalog = parse_static_gtfs_zip(data)
            self._catalogs[feed.slug] = catalog
            self._static_loaded[feed.slug] = now
            await self._ingest_static(feed.agency, catalog)
            logger.info(
                "transit_rt static loaded %s routes=%s shapes=%s",
                feed.slug,
                len(catalog.routes),
                len(catalog.shapes),
            )
        except Exception as exc:
            logger.warning("transit_rt static %s failed: %s", feed.slug, exc)

    async def _get_pool(self):
        import asyncpg

        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                os.getenv("MINDEX_DATABASE_URL", "postgresql://mindex:mindex@localhost:5432/mindex"),
                min_size=1,
                max_size=3,
                command_timeout=30,
            )
        return self._pool

    async def _ingest_static(self, agency: str, catalog: StaticCatalog) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            for rid, route in catalog.routes.items():
                color = route.route_color
                if color and not color.startswith("#"):
                    color = f"#{color}"
                await conn.execute(
                    """
                    INSERT INTO transit.routes (agency, route_id, route_short_name, route_long_name, route_type, route_color, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, now())
                    ON CONFLICT (agency, route_id) DO UPDATE SET
                        route_short_name = EXCLUDED.route_short_name,
                        route_long_name = EXCLUDED.route_long_name,
                        route_type = EXCLUDED.route_type,
                        route_color = EXCLUDED.route_color,
                        updated_at = now()
                    """,
                    agency,
                    rid,
                    route.route_short_name,
                    route.route_long_name,
                    route.route_type,
                    color,
                )

            for sid, stop in catalog.stops.items():
                lat, lng = stop.get("lat"), stop.get("lng")
                if lat is None or lng is None:
                    continue
                await conn.execute(
                    """
                    INSERT INTO transit.stops (agency, stop_id, stop_name, geom, updated_at)
                    VALUES ($1, $2, $3, ST_SetSRID(ST_Point($4, $5), 4326), now())
                    ON CONFLICT (agency, stop_id) DO UPDATE SET
                        stop_name = EXCLUDED.stop_name,
                        geom = EXCLUDED.geom,
                        updated_at = now()
                    """,
                    agency,
                    sid,
                    stop.get("stop_name"),
                    lng,
                    lat,
                )

            for route_id, shape_id in catalog.route_shapes.items():
                coords = catalog.shapes.get(shape_id)
                if not coords or len(coords) < 2:
                    continue
                route = catalog.routes.get(route_id)
                color = route.route_color if route else None
                if color and not str(color).startswith("#"):
                    color = f"#{color}"
                wkt_coords = ", ".join(f"{lng} {lat}" for lng, lat in coords)
                wkt = f"LINESTRING({wkt_coords})"
                await conn.execute(
                    """
                    INSERT INTO transit.shapes (agency, route_id, shape_id, geom, route_color, updated_at)
                    VALUES ($1, $2, $3, ST_GeomFromText($4, 4326), $5, now())
                    ON CONFLICT (agency, route_id, shape_id) DO UPDATE SET
                        geom = EXCLUDED.geom,
                        route_color = EXCLUDED.route_color,
                        updated_at = now()
                    """,
                    agency,
                    route_id,
                    shape_id,
                    wkt,
                    color,
                )

    async def _ingest_transit(self, vehicles: List[DecodedVehicle], agencies: List[str]) -> int:
        if not vehicles and not agencies:
            return 0
        pool = await self._get_pool()
        count = 0
        async with pool.acquire() as conn:
            for v in vehicles:
                route_color = v.route_color
                if route_color and not str(route_color).startswith("#"):
                    route_color = f"#{route_color}"
                route_short = v.route_short_name or v.route_id
                await conn.execute(
                    """
                    INSERT INTO transit.vehicles (
                        vehicle_uid, agency, route_id, trip_id, geom, bearing, speed,
                        current_status, stop_id, next_stop_eta, occupancy,
                        route_short_name, route_color, route_type, updated_at
                    ) VALUES (
                        $1, $2, $3, $4, ST_SetSRID(ST_Point($5, $6), 4326),
                        $7, $8, $9, $10, $11, $12, $13, $14, $15, now()
                    )
                    ON CONFLICT (vehicle_uid) DO UPDATE SET
                        agency = EXCLUDED.agency,
                        route_id = EXCLUDED.route_id,
                        trip_id = EXCLUDED.trip_id,
                        geom = EXCLUDED.geom,
                        bearing = EXCLUDED.bearing,
                        speed = EXCLUDED.speed,
                        current_status = EXCLUDED.current_status,
                        stop_id = EXCLUDED.stop_id,
                        next_stop_eta = EXCLUDED.next_stop_eta,
                        occupancy = EXCLUDED.occupancy,
                        route_short_name = EXCLUDED.route_short_name,
                        route_color = EXCLUDED.route_color,
                        route_type = EXCLUDED.route_type,
                        updated_at = now()
                    """,
                    v.vehicle_uid,
                    v.agency,
                    v.route_id,
                    v.trip_id,
                    v.lng,
                    v.lat,
                    v.bearing,
                    v.speed,
                    v.current_status,
                    v.stop_id,
                    v.next_stop_eta,
                    v.occupancy,
                    route_short,
                    route_color,
                    v.route_type,
                )
                count += 1

            if agencies:
                await conn.execute(
                    """
                    DELETE FROM transit.vehicles
                    WHERE agency = ANY($1::text[])
                      AND updated_at < now() - interval '8 minutes'
                    """,
                    list(set(agencies)),
                )
        return count

    def get_status(self) -> Dict[str, Any]:
        base = super().get_status()
        base["feeds"] = [f.slug for f in self._feeds]
        base["enabled"] = True
        return base
