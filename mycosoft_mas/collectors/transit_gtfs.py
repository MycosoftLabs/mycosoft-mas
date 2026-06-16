"""
GTFS-RT decode + static GTFS helpers for transit_rt_collector — Jun 15, 2026.
"""

from __future__ import annotations

import csv
import io
import logging
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from google.transit import gtfs_realtime_pb2
except ImportError:  # pragma: no cover
    gtfs_realtime_pb2 = None  # type: ignore

OCCUPANCY_ENUM = {
    0: "EMPTY",
    1: "MANY_SEATS_AVAILABLE",
    2: "FEW_SEATS_AVAILABLE",
    3: "STANDING_ROOM_ONLY",
    4: "CRUSHED_STANDING_ROOM_ONLY",
    5: "FULL",
    6: "NOT_ACCEPTING_PASSENGERS",
}

STATUS_ENUM = {
    0: "INCOMING_AT",
    1: "STOPPED_AT",
    2: "IN_TRANSIT_TO",
}


@dataclass
class DecodedVehicle:
    vehicle_uid: str
    agency: str
    route_id: Optional[str] = None
    trip_id: Optional[str] = None
    lat: float = 0.0
    lng: float = 0.0
    bearing: Optional[float] = None
    speed: Optional[float] = None
    current_status: Optional[str] = None
    stop_id: Optional[str] = None
    occupancy: Optional[str] = None
    vehicle_label: Optional[str] = None
    timestamp: Optional[datetime] = None
    route_short_name: Optional[str] = None
    route_color: Optional[str] = None
    route_type: Optional[int] = None
    next_stop_eta: Optional[int] = None


@dataclass
class TripEta:
    trip_id: str
    stop_id: Optional[str] = None
    arrival_time: Optional[int] = None  # epoch seconds from GTFS-RT


@dataclass
class StaticRoute:
    route_id: str
    route_short_name: Optional[str] = None
    route_long_name: Optional[str] = None
    route_type: Optional[int] = None
    route_color: Optional[str] = None
    shape_id: Optional[str] = None


@dataclass
class StaticCatalog:
    routes: Dict[str, StaticRoute] = field(default_factory=dict)
    stops: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    shapes: Dict[str, List[Tuple[float, float]]] = field(default_factory=dict)
    route_shapes: Dict[str, str] = field(default_factory=dict)


def decode_vehicle_positions_pb(data: bytes, agency: str, id_prefix: str) -> List[DecodedVehicle]:
    if gtfs_realtime_pb2 is None:
        logger.warning("gtfs-realtime-bindings not installed; cannot decode protobuf")
        return []
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(data)
    out: List[DecodedVehicle] = []
    for ent in feed.entity:
        if not ent.HasField("vehicle"):
            continue
        v = ent.vehicle
        if not v.HasField("position"):
            continue
        lat = float(v.position.latitude)
        lng = float(v.position.longitude)
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            continue
        vid = v.vehicle.id if v.HasField("vehicle") and v.vehicle.id else None
        trip_id = v.trip.trip_id if v.HasField("trip") and v.trip.trip_id else None
        route_id = v.trip.route_id if v.HasField("trip") and v.trip.route_id else None
        suffix = vid or trip_id or ent.id
        vehicle_uid = f"{id_prefix}_{suffix}"
        ts = None
        if v.timestamp:
            ts = datetime.fromtimestamp(int(v.timestamp), tz=timezone.utc)
        out.append(
            DecodedVehicle(
                vehicle_uid=vehicle_uid,
                agency=agency,
                route_id=route_id or None,
                trip_id=trip_id or None,
                lat=lat,
                lng=lng,
                bearing=float(v.position.bearing) if v.position.bearing else None,
                speed=float(v.position.speed) if v.position.speed else None,
                current_status=STATUS_ENUM.get(v.current_status) if v.current_status else None,
                stop_id=v.stop_id if v.stop_id else None,
                occupancy=OCCUPANCY_ENUM.get(v.occupancy_status) if v.occupancy_status else None,
                vehicle_label=vid,
                timestamp=ts,
            )
        )
    return out


def decode_trip_updates_pb(data: bytes) -> List[TripEta]:
    if gtfs_realtime_pb2 is None:
        return []
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(data)
    out: List[TripEta] = []
    for ent in feed.entity:
        if not ent.HasField("trip_update"):
            continue
        tu = ent.trip_update
        trip_id = tu.trip.trip_id if tu.HasField("trip") and tu.trip.trip_id else ent.id
        for stu in tu.stop_time_update:
            arrival = None
            if stu.HasField("arrival") and stu.arrival.time:
                arrival = int(stu.arrival.time)
            elif stu.HasField("departure") and stu.departure.time:
                arrival = int(stu.departure.time)
            stop_id = stu.stop_id if stu.stop_id else None
            if arrival:
                out.append(TripEta(trip_id=trip_id, stop_id=stop_id, arrival_time=arrival))
    return out


def merge_trip_etas(vehicles: List[DecodedVehicle], etas: List[TripEta]) -> None:
    """Attach next_stop_eta (epoch ms) when trip_id matches."""
    by_trip: Dict[str, List[TripEta]] = {}
    now = int(datetime.now(tz=timezone.utc).timestamp())
    for eta in etas:
        by_trip.setdefault(eta.trip_id, []).append(eta)
    for v in vehicles:
        if not v.trip_id or v.trip_id not in by_trip:
            continue
        candidates = [e for e in by_trip[v.trip_id] if e.arrival_time and e.arrival_time >= now - 60]
        if not candidates:
            candidates = by_trip[v.trip_id]
        candidates.sort(key=lambda e: e.arrival_time or 0)
        best = candidates[0]
        if best.arrival_time:
            v.next_stop_eta = int(best.arrival_time) * 1000
        if best.stop_id and not v.stop_id:
            v.stop_id = best.stop_id


def parse_static_gtfs_zip(data: bytes) -> StaticCatalog:
    catalog = StaticCatalog()
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = {n.lower(): n for n in zf.namelist()}

        routes_name = names.get("routes.txt")
        if routes_name:
            with zf.open(routes_name) as f:
                for row in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig")):
                    rid = row.get("route_id", "").strip()
                    if not rid:
                        continue
                    catalog.routes[rid] = StaticRoute(
                        route_id=rid,
                        route_short_name=(row.get("route_short_name") or "").strip() or None,
                        route_long_name=(row.get("route_long_name") or "").strip() or None,
                        route_type=int(row["route_type"]) if row.get("route_type", "").isdigit() else None,
                        route_color=(row.get("route_color") or "").strip() or None,
                        shape_id=(row.get("shape_id") or "").strip() or None,
                    )
                    if catalog.routes[rid].shape_id:
                        catalog.route_shapes[rid] = catalog.routes[rid].shape_id  # type: ignore

        trips_name = names.get("trips.txt")
        if trips_name:
            with zf.open(trips_name) as f:
                for row in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig")):
                    rid = row.get("route_id", "").strip()
                    sid = row.get("shape_id", "").strip()
                    if rid and sid and rid not in catalog.route_shapes:
                        catalog.route_shapes[rid] = sid

        stops_name = names.get("stops.txt")
        if stops_name:
            with zf.open(stops_name) as f:
                for row in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig")):
                    sid = row.get("stop_id", "").strip()
                    if not sid:
                        continue
                    lat = row.get("stop_lat")
                    lng = row.get("stop_lon")
                    catalog.stops[sid] = {
                        "stop_name": (row.get("stop_name") or "").strip() or None,
                        "lat": float(lat) if lat else None,
                        "lng": float(lng) if lng else None,
                    }

        shapes_name = names.get("shapes.txt")
        if shapes_name:
            with zf.open(shapes_name) as f:
                for row in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig")):
                    sid = row.get("shape_id", "").strip()
                    if not sid:
                        continue
                    seq = int(row["shape_pt_sequence"]) if row.get("shape_pt_sequence", "").isdigit() else 0
                    lat = float(row["shape_pt_lat"])
                    lng = float(row["shape_pt_lon"])
                    catalog.shapes.setdefault(sid, []).append((seq, lat, lng))
            for sid in list(catalog.shapes.keys()):
                pts = sorted(catalog.shapes[sid], key=lambda p: p[0])
                catalog.shapes[sid] = [(lng, lat) for _, lat, lng in pts]

    return catalog


def decode_amtraker_trains(data: Any, agency: str = "Amtrak", id_prefix: str = "amtrak") -> List[DecodedVehicle]:
    """Amtraker v3 JSON: { routeId: [ { trainNum, lat, lon, heading, velocity, ... } ] }."""
    out: List[DecodedVehicle] = []
    if not isinstance(data, dict):
        return out
    for _route_key, trains in data.items():
        if not isinstance(trains, list):
            continue
        for t in trains:
            if not isinstance(t, dict):
                continue
            lat = t.get("lat")
            lng = t.get("lon") if t.get("lon") is not None else t.get("lng")
            if lat is None or lng is None:
                continue
            train_num = t.get("trainNum") or t.get("trainID") or t.get("trainId")
            suffix = str(train_num or f"{lat},{lng}")
            speed_mph = t.get("velocity") or t.get("speed") or 0
            speed_mps = float(speed_mph) * 0.44704 if speed_mph else None
            out.append(
                DecodedVehicle(
                    vehicle_uid=f"{id_prefix}_{suffix}",
                    agency=agency,
                    route_id=str(t.get("routeName") or t.get("route") or "") or None,
                    trip_id=str(train_num) if train_num else None,
                    lat=float(lat),
                    lng=float(lng),
                    bearing=float(t["heading"]) if t.get("heading") is not None else None,
                    speed=speed_mps,
                    current_status=str(t.get("trainState") or t.get("eventCode") or "") or None,
                    vehicle_label=str(train_num) if train_num else None,
                )
            )
    return out
