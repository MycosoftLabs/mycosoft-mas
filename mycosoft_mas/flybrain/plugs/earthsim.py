"""Earth Simulator / AO operator plug (spec §2 ``earthsim``).

``observe()`` builds one ``earthsim`` observation from the ITDX map slice
(``plug_config.map_slice`` or the Fort Stewart demonstration slice from
``itdx_api.fort_stewart_demo_slice``), the in-process device registry
snapshot and the Earth-2 status probe. ``navigate()`` plans a
:class:`NavPath` across the AO from the AO centre toward the side the
brain is being driven hardest on, treating assets, devices and located
detections as obstacles. ``act()`` returns operator narration lines.
Nothing is actuated.

All MAS calls are in-process (spec §11.6) and wrapped in ``try/except``
with a 3 s budget; an unreachable source becomes a note, never a value.
"""

from __future__ import annotations

import asyncio
import math
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from mycosoft_mas.flybrain.plugs.base import FlyBrainPlug, PlugContext
from mycosoft_mas.flybrain.schemas import (
    ORIGIN_SIMULATED,
    DetectionFrame,
    GeoPoint,
    MotorAction,
    NavPath,
    Observation,
)

PROBE_BUDGET_S = 3.0
DEFAULT_GRID_SIZE_M = 2000.0
MAX_GRID_SIZE_M = 4000.0
GRID_CELLS_PER_SIDE = 160
MIN_CELL_M = 5.0
DEFAULT_OBSTACLE_RADIUS_M = 30.0
DETECTION_POINT_RADIUS_M = 10.0
GOAL_DISTANCE_FRACTION = 0.4
EARTH_RADIUS_M = 6371008.8


# ---------------------------------------------------------------------------
# Helpers shared with the ITDX plug
# ---------------------------------------------------------------------------


def _num(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(out) or math.isinf(out):
        return None
    return out


def _latlon(item: Any) -> Optional[Tuple[float, float]]:
    if isinstance(item, (list, tuple)) and len(item) >= 2:
        lon, lat = _num(item[0]), _num(item[1])
        return (lat, lon) if lat is not None and lon is not None else None
    if not isinstance(item, Mapping):
        return None
    for lat_key, lon_key in (("lat", "lon"), ("lat", "lng"), ("latitude", "longitude")):
        lat, lon = _num(item.get(lat_key)), _num(item.get(lon_key))
        if lat is not None and lon is not None:
            return lat, lon
    for nested in ("location", "position", "center", "coordinates", "gps"):
        sub = item.get(nested)
        if sub is not None and sub is not item:
            found = _latlon(sub)
            if found:
                return found
    return None


def ao_center(map_slice: Mapping[str, Any]) -> Optional[GeoPoint]:
    """AO centre from ``ao.center`` or the ``ao.bbox`` midpoint."""
    ao = map_slice.get("ao") if isinstance(map_slice, Mapping) else None
    if not isinstance(ao, Mapping):
        return None
    pt = _latlon(ao.get("center"))
    if pt is not None:
        return GeoPoint(lat=pt[0], lon=pt[1])
    bbox = ao.get("bbox")
    if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
        vals = [_num(v) for v in bbox]
        if all(v is not None for v in vals):
            w, s, e, n = (float(v) for v in vals)  # type: ignore[arg-type]
            return GeoPoint(lat=(s + n) / 2.0, lon=(w + e) / 2.0)
    return None


def ao_extent_m(map_slice: Mapping[str, Any]) -> Optional[float]:
    """Smaller side of the AO bbox in metres, or ``None``."""
    ao = map_slice.get("ao") if isinstance(map_slice, Mapping) else None
    if not isinstance(ao, Mapping):
        return None
    bbox = ao.get("bbox")
    if not (isinstance(bbox, (list, tuple)) and len(bbox) == 4):
        return None
    vals = [_num(v) for v in bbox]
    if not all(v is not None for v in vals):
        return None
    w, s, e, n = (float(v) for v in vals)  # type: ignore[arg-type]
    lat_mid = (s + n) / 2.0
    width = abs(math.radians(e - w)) * EARTH_RADIUS_M * math.cos(math.radians(lat_mid))
    height = abs(math.radians(n - s)) * EARTH_RADIUS_M
    return max(0.0, min(width, height))


def _bearing_deg(a: GeoPoint, b: GeoPoint) -> float:
    phi1, phi2 = math.radians(a.lat), math.radians(b.lat)
    dlon = math.radians(b.lon - a.lon)
    x = math.sin(dlon) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlon)
    return math.degrees(math.atan2(x, y)) % 360.0


def drive_side(
    encoded_rates: Mapping[str, float], left_groups: Sequence[str], right_groups: Sequence[str]
) -> Tuple[float, float, str]:
    """``(left_hz, right_hz, side)`` from the encoded drive; side in left/right/none."""
    left = max([float(encoded_rates.get(g, 0.0) or 0.0) for g in left_groups] or [0.0])
    right = max([float(encoded_rates.get(g, 0.0) or 0.0) for g in right_groups] or [0.0])
    if right > left:
        return left, right, "right"
    if left > right:
        return left, right, "left"
    return left, right, "none"


def plan_across_ao(
    map_slice: Mapping[str, Any],
    action: MotorAction,
    encoded_rates: Mapping[str, float],
    detections: Optional[DetectionFrame],
    *,
    left_groups: Sequence[str] = (),
    right_groups: Sequence[str] = (),
    size_m: Optional[float] = None,
    cell_m: Optional[float] = None,
    obstacle_radius_m: float = DEFAULT_OBSTACLE_RADIUS_M,
) -> NavPath:
    """Plan from the AO centre toward the highest-drive side (spec §2 ``earthsim``).

    Goal bearing = observer heading (AO centre → ``focus`` when given, else
    ``heading_deg``, else north) + 90° toward the side with the higher
    encoded left/right drive + the brain's ``heading_delta_deg`` when the
    action is locomotion. Goal distance = 40 % of the grid size. Assets,
    devices and located detections are obstacles.
    """
    from mycosoft_mas.flybrain.navigation import OccupancyGrid, geo_from_enu, plan

    center = ao_center(map_slice)
    if center is None:
        return NavPath(feasible=False, note="map slice has no AO centre or bbox; cannot plan")

    extent = ao_extent_m(map_slice)
    size = _num(size_m)
    if size is None or size <= 0:
        size = min(extent, MAX_GRID_SIZE_M) if extent else DEFAULT_GRID_SIZE_M
        size = max(size, 200.0)
    cell = _num(cell_m)
    if cell is None or cell <= 0:
        cell = max(MIN_CELL_M, size / GRID_CELLS_PER_SIDE)
    grid = OccupancyGrid(center, size_m=size, cell_m=cell)

    # observer heading
    heading: Optional[float] = None
    focus = _latlon(map_slice.get("focus"))
    if focus is not None and (focus[0], focus[1]) != (center.lat, center.lon):
        heading = _bearing_deg(center, GeoPoint(lat=focus[0], lon=focus[1]))
    if heading is None:
        heading = _num(map_slice.get("heading_deg"))
    heading_note = "focus" if focus is not None and heading is not None else "heading_deg"
    if heading is None:
        heading = 0.0
        heading_note = "north (no focus/heading in slice)"

    left_hz, right_hz, side = drive_side(encoded_rates, left_groups, right_groups)
    side_offset = 90.0 if side == "right" else (-90.0 if side == "left" else 0.0)
    delta = float(action.heading_delta_deg) if action.kind == "locomotion" else 0.0
    goal_bearing = (heading + side_offset + delta) % 360.0
    distance = GOAL_DISTANCE_FRACTION * grid.size_m
    goal = geo_from_enu(
        distance * math.sin(math.radians(goal_bearing)),
        distance * math.cos(math.radians(goal_bearing)),
        center,
    )

    # obstacles
    n_assets = n_devices = n_det = 0
    for key in ("assets", "devices"):
        seq = map_slice.get(key)
        if not isinstance(seq, (list, tuple)):
            continue
        for item in seq:
            pt = _latlon(item)
            if pt is None:
                continue
            if grid.add_point(pt[0], pt[1], obstacle_radius_m) or grid.in_bounds(pt[0], pt[1]):
                if key == "assets":
                    n_assets += 1
                else:
                    n_devices += 1
    if detections is not None and detections.available:
        for det in detections.detections:
            if det.perimeter:
                if grid.add_perimeter(det.perimeter):
                    n_det += 1
            elif det.location is not None:
                if grid.add_point(det.location.lat, det.location.lon, DETECTION_POINT_RADIUS_M):
                    n_det += 1

    nav = plan(grid, center, goal, turn_bias=float(action.turn))
    rule = (
        f"goal = AO centre + {distance:.0f} m at {goal_bearing:.0f}° "
        f"(observer heading {heading:.0f}° from {heading_note}; drive side={side} "
        f"left={left_hz:.1f} Hz right={right_hz:.1f} Hz; brain heading_delta={delta:+.1f}°); "
        f"obstacles: {n_assets} assets, {n_devices} devices, {n_det} detections in grid"
    )
    nav.note = f"{nav.note}; {rule}" if nav.note else rule
    return nav


def _device_rows_for_slice(devices: Any) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not isinstance(devices, (list, tuple)):
        return rows
    for dev in devices:
        if not isinstance(dev, Mapping):
            continue
        pt = _latlon(dev)
        row: Dict[str, Any] = {
            "id": dev.get("device_id") or dev.get("id"),
            "type": dev.get("device_type") or dev.get("type") or "device",
            "status": dev.get("status"),
        }
        if pt is not None:
            row["lat"], row["lon"] = pt
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# In-process probes (each guarded; never HTTP to MAS itself)
# ---------------------------------------------------------------------------


def default_map_slice() -> Dict[str, Any]:
    from mycosoft_mas.core.routers.itdx_api import fort_stewart_demo_slice

    return fort_stewart_demo_slice()


def devices_snapshot() -> Dict[str, Any]:
    from mycosoft_mas.core.routers.itdx_api import _devices_inprocess

    return _devices_inprocess()


async def earth2_status() -> Dict[str, Any]:
    from mycosoft_mas.core.routers.itdx_api import _earth2_status_inprocess

    return await _earth2_status_inprocess()


# ---------------------------------------------------------------------------
# Plug
# ---------------------------------------------------------------------------


class EarthSimPlug(FlyBrainPlug):
    """Earth Simulator operator: AO slice + devices + Earth-2 → nav path + narration."""

    name = "earthsim"
    navigates = True

    def __init__(self, config=None, settings=None) -> None:
        super().__init__(config, settings)
        self.map_slice: Dict[str, Any] = {}
        self.devices: List[Dict[str, Any]] = []
        self.earth2: Dict[str, Any] = {}
        self.last_nav: Optional[NavPath] = None

    def describe(self) -> Dict[str, Any]:
        base = super().describe()
        base.update(
            {
                "observe": "ITDX map slice (plug_config.map_slice or Fort Stewart demo), "
                "device registry snapshot, Earth-2 status — all in-process",
                "act": "NavPath across the AO toward the highest-drive side + operator narration",
                "map_slice_source": "plug_config" if self.plug_map_slice() else "fort_stewart_demo",
            }
        )
        return base

    def plug_map_slice(self) -> Optional[Dict[str, Any]]:
        cfg = self.config.plug_config if isinstance(self.config.plug_config, dict) else {}
        ms = cfg.get("map_slice")
        return dict(ms) if isinstance(ms, dict) else None

    async def observe(self, ctx: PlugContext) -> List[Observation]:
        notes: List[str] = []
        map_slice = self.plug_map_slice()
        if map_slice is None:
            try:
                map_slice = await asyncio.wait_for(
                    asyncio.to_thread(default_map_slice), PROBE_BUDGET_S
                )
            except Exception as exc:  # noqa: BLE001
                notes.append(
                    f"earthsim: default map slice unavailable ({type(exc).__name__}: {exc})"
                )
                map_slice = None
        if map_slice is None:
            self.last_observe_notes = notes
            ctx.notes.extend(notes)
            return []
        payload: Dict[str, Any] = {
            "ao": map_slice.get("ao") or {},
            "assets": list(map_slice.get("assets") or []),
            "devices": list(map_slice.get("devices") or []),
        }
        for key in ("focus", "heading_deg", "clock", "origin"):
            if key in map_slice:
                payload[key] = map_slice[key]

        # device registry (in-process)
        try:
            snap = await asyncio.wait_for(asyncio.to_thread(devices_snapshot), PROBE_BUDGET_S)
            rows = _device_rows_for_slice(snap.get("devices"))
            self.devices = rows
            payload["devices"] = payload["devices"] + rows
            if not rows:
                notes.append("earthsim: device registry has no devices")
        except Exception as exc:  # noqa: BLE001
            self.devices = []
            notes.append(f"earthsim: device registry unavailable ({type(exc).__name__}: {exc})")

        # Earth-2 status (in-process probe of the Earth-2 router)
        try:
            self.earth2 = await asyncio.wait_for(earth2_status(), PROBE_BUDGET_S)
            payload["earth2"] = {
                k: self.earth2.get(k)
                for k in ("service", "source", "status", "available", "models_loaded")
                if k in self.earth2
            }
        except Exception as exc:  # noqa: BLE001
            self.earth2 = {"available": False, "error": f"{type(exc).__name__}: {exc}"}
            notes.append(f"earthsim: Earth-2 status unavailable ({type(exc).__name__}: {exc})")

        self.map_slice = {**map_slice, "devices": payload["devices"]}
        self.last_observe_notes = notes
        ctx.notes.extend(notes)
        return [Observation(kind="earthsim", payload=payload, t_ms=ctx.t_ms, source="earthsim")]

    async def navigate(
        self, ctx: PlugContext, action: MotorAction, detections: Optional[DetectionFrame]
    ) -> Optional[NavPath]:
        if not self.map_slice:
            self.last_nav = NavPath(
                feasible=False, note="no map slice observed this session; nothing to plan on"
            )
            return self.last_nav
        cfg = ctx.plug_config
        nav = await asyncio.to_thread(
            plan_across_ao,
            self.map_slice,
            action,
            ctx.encoded_rates_hz,
            detections,
            left_groups=ctx.atlas.input_groups("left") if ctx.atlas is not None else (),
            right_groups=ctx.atlas.input_groups("right") if ctx.atlas is not None else (),
            size_m=_num(cfg.get("grid_size_m")),
            cell_m=_num(cfg.get("cell_m")),
            obstacle_radius_m=_num(cfg.get("obstacle_radius_m")) or DEFAULT_OBSTACLE_RADIUS_M,
        )
        self.last_nav = nav
        return nav

    async def act(
        self,
        ctx: PlugContext,
        action: MotorAction,
        nav: Optional[NavPath],
        detections: Optional[DetectionFrame],
    ) -> Dict[str, Any]:
        ao = self.map_slice.get("ao") if isinstance(self.map_slice, dict) else {}
        place = (ao or {}).get("name") or (ao or {}).get("place") or "unspecified AO"
        ev = action.evidence or {}
        lines: List[str] = [
            f"FlyBrain ({ORIGIN_SIMULATED}) over {place}: readouts forward "
            f"{float(ev.get('forward_hz', 0.0)):.1f} Hz, left {float(ev.get('left_hz', 0.0)):.1f} Hz, "
            f"right {float(ev.get('right_hz', 0.0)):.1f} Hz → {action.kind}, "
            f"turn {action.turn:+.2f} ({action.heading_delta_deg:+.1f}°), "
            f"throttle {action.throttle_pct:.0f} %, confidence {action.confidence:.2f}."
        ]
        if nav is None:
            lines.append("Navigation: no path planned this tick.")
        elif nav.feasible:
            lines.append(
                f"Navigation: feasible path, {len(nav.waypoints)} waypoints, "
                f"{(nav.cost or 0.0):.0f} m, {nav.blocked_cells}/{nav.total_cells} grid cells blocked."
            )
        else:
            lines.append(f"Navigation: no feasible path — {nav.note}")
        if detections is None:
            lines.append("Detections: none supplied this tick.")
        elif not detections.available:
            lines.append(f"Detections unavailable: {detections.note or 'no reason given'}.")
        else:
            lines.append(f"Detections: {len(detections.detections)} in frame.")
        lines.append(f"Devices in registry: {len(self.devices)}.")
        if self.earth2:
            status = self.earth2.get("status") or self.earth2.get("service") or "unknown"
            avail = self.earth2.get("available")
            lines.append(
                f"Earth-2: {status}"
                + (f" (available={avail})" if avail is not None else "")
                + (f" — {self.earth2.get('error')}" if self.earth2.get("error") else "")
                + "."
            )
        lines.append("Advisory only. Nothing actuated.")
        result = {
            "mode": self.name,
            "origin": ORIGIN_SIMULATED,
            "actuated": False,
            "dry_run": ctx.dry_run,
            "narration": lines,
            "place": place,
            "nav_feasible": bool(nav.feasible) if nav is not None else None,
            "n_waypoints": len(nav.waypoints) if nav is not None else 0,
            "n_devices": len(self.devices),
            "earth2": self.earth2,
            "observe_notes": list(self.last_observe_notes),
        }
        self.last_result = result
        return result


__all__ = [
    "EarthSimPlug",
    "ao_center",
    "ao_extent_m",
    "default_map_slice",
    "devices_snapshot",
    "drive_side",
    "earth2_status",
    "plan_across_ao",
]
