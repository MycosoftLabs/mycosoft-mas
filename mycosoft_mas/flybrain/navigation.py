"""FlyBrain navigation — local ENU occupancy grid, A* and NavPath (spec §8).

``OccupancyGrid`` rasterises perimeters and points into a square grid of
``cell_m`` cells centred on a ``GeoPoint`` in a local East-North-Up frame
(equirectangular approximation, fine at <= 5 km). ``plan`` runs A* over the
grid (8-neighbour, diagonal cost sqrt(2), no corner cutting), applies the
brain's ``turn_bias`` and decimates the result with Douglas-Peucker to at
most 12 waypoints plus a GeoJSON LineString.

Turn bias (``turn_bias`` in [-1, 1], negative = left, matching
``MotorAction.turn``) is applied as two non-negative cost terms so A* stays
admissible with the octile heuristic:

* ``bias_weight * |turn_bias| * |dheading| / 45`` on every move that turns
  *against* the preferred side (the spec's dheading term; dheading is the
  change of heading between consecutive moves);
* ``bias_weight * |turn_bias| * min(1, lateral / 2 cell)`` on every move that
  ends on the *against* side of the straight start->goal line.

The second term is what actually chooses a side: around a mirror-symmetric
obstacle the total against-side turning is identical for both routes, so a
turn-only penalty cannot break the tie. Both terms are zero when
``turn_bias == 0``.

Infeasible plans (start/goal outside the grid or blocked, goal unreachable)
return ``feasible=False``, ``waypoints=[]`` and an honest ``note``.

Pure Python; safe to import under ``MAS_LIGHT_IMPORT=1``.
"""

from __future__ import annotations

import heapq
import math
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from mycosoft_mas.flybrain.schemas import Detection, GeoPoint, NavPath, Waypoint

EARTH_RADIUS_M = 6371008.8
MAX_WAYPOINTS = 12
SQRT2 = math.sqrt(2.0)

# Neighbour order: N, NE, E, SE, S, SW, W, NW as (d_row(north), d_col(east)).
_DIRS: Tuple[Tuple[int, int], ...] = (
    (1, 0),
    (1, 1),
    (0, 1),
    (-1, 1),
    (-1, 0),
    (-1, -1),
    (0, -1),
    (1, -1),
)
_DIR_HEADING_DEG: Tuple[float, ...] = (0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0)


# ---------------------------------------------------------------------------
# Geodesy helpers
# ---------------------------------------------------------------------------


def _origin_latlon(origin: Any) -> Tuple[float, float]:
    if isinstance(origin, GeoPoint):
        return float(origin.lat), float(origin.lon)
    if isinstance(origin, Mapping):
        return float(origin["lat"]), float(origin["lon"])
    lat, lon = origin
    return float(lat), float(lon)


def enu_from_geo(lat: float, lon: float, origin: Any) -> Tuple[float, float]:
    """(lat, lon) → (east_m, north_m) relative to ``origin`` (equirectangular)."""
    lat0, lon0 = _origin_latlon(origin)
    east = math.radians(float(lon) - lon0) * EARTH_RADIUS_M * math.cos(math.radians(lat0))
    north = math.radians(float(lat) - lat0) * EARTH_RADIUS_M
    return east, north


def geo_from_enu(east_m: float, north_m: float, origin: Any) -> GeoPoint:
    """(east_m, north_m) relative to ``origin`` → ``GeoPoint`` (inverse of ``enu_from_geo``)."""
    lat0, lon0 = _origin_latlon(origin)
    cos_lat = math.cos(math.radians(lat0))
    if abs(cos_lat) < 1e-12:  # at the pole east is undefined; keep the origin longitude
        lon = lon0
    else:
        lon = lon0 + math.degrees(float(east_m) / (EARTH_RADIUS_M * cos_lat))
    lat = lat0 + math.degrees(float(north_m) / EARTH_RADIUS_M)
    return GeoPoint(lat=lat, lon=lon)


def wrap_deg(angle_deg: float) -> float:
    a = (angle_deg + 180.0) % 360.0 - 180.0
    return 180.0 if a == -180.0 else a


def _point_in_ring(x: float, y: float, ring: Sequence[Tuple[float, float]]) -> bool:
    """Even-odd point-in-polygon test in the ENU plane."""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > y) != (yj > y):
            x_cross = (xj - xi) * (y - yi) / ((yj - yi) or 1e-300) + xi
            if x < x_cross:
                inside = not inside
        j = i
    return inside


# ---------------------------------------------------------------------------
# Occupancy grid
# ---------------------------------------------------------------------------


class OccupancyGrid:
    """Square boolean occupancy grid in a local ENU frame around ``center``.

    Rows index north (row 0 = southern edge), columns index east.
    """

    def __init__(self, center: GeoPoint, size_m: float = 400.0, cell_m: float = 5.0) -> None:
        if not isinstance(center, GeoPoint):
            lat, lon = _origin_latlon(center)
            center = GeoPoint(lat=lat, lon=lon)
        self.center = center
        self.size_m = float(size_m) if size_m and size_m > 0 else 400.0
        self.cell_m = float(cell_m) if cell_m and cell_m > 0 else 5.0
        self.n = max(1, int(math.ceil(self.size_m / self.cell_m)))
        self.size_m = self.n * self.cell_m  # snap to whole cells
        self._half = self.size_m / 2.0
        self._cells = [bytearray(self.n) for _ in range(self.n)]
        self._blocked = 0
        self.features: List[Dict[str, Any]] = []

    # -- coordinate transforms -------------------------------------------------

    def to_enu(self, lat: float, lon: float) -> Tuple[float, float]:
        return enu_from_geo(lat, lon, self.center)

    def to_geo(self, east_m: float, north_m: float) -> GeoPoint:
        return geo_from_enu(east_m, north_m, self.center)

    def cell_of_enu(self, east_m: float, north_m: float) -> Optional[Tuple[int, int]]:
        col = int(math.floor((east_m + self._half) / self.cell_m))
        row = int(math.floor((north_m + self._half) / self.cell_m))
        if 0 <= row < self.n and 0 <= col < self.n:
            return row, col
        return None

    def cell_of(self, lat: float, lon: float) -> Optional[Tuple[int, int]]:
        east, north = self.to_enu(lat, lon)
        return self.cell_of_enu(east, north)

    def cell_center_enu(self, row: int, col: int) -> Tuple[float, float]:
        return (
            -self._half + (col + 0.5) * self.cell_m,
            -self._half + (row + 0.5) * self.cell_m,
        )

    def in_bounds(self, lat: float, lon: float) -> bool:
        return self.cell_of(lat, lon) is not None

    # -- occupancy ---------------------------------------------------------------

    def _block(self, row: int, col: int) -> int:
        if 0 <= row < self.n and 0 <= col < self.n and not self._cells[row][col]:
            self._cells[row][col] = 1
            self._blocked += 1
            return 1
        return 0

    def blocked_cell(self, row: int, col: int) -> bool:
        if 0 <= row < self.n and 0 <= col < self.n:
            return bool(self._cells[row][col])
        return True

    def is_blocked(self, lat: float, lon: float) -> bool:
        """True when the cell containing (lat, lon) is occupied or lies outside the grid."""
        cell = self.cell_of(lat, lon)
        if cell is None:
            return True
        return bool(self._cells[cell[0]][cell[1]])

    def add_perimeter(self, ring: Sequence[Sequence[float]]) -> int:
        """Block every cell inside or touched by a ``[[lon, lat], ...]`` ring.

        Returns the number of newly blocked cells (0 for a malformed ring).
        """
        pts: List[Tuple[float, float]] = []
        for p in ring or []:
            if isinstance(p, Mapping):
                lat, lon = p.get("lat"), p.get("lon", p.get("lng"))
            elif isinstance(p, (list, tuple)) and len(p) >= 2:
                lon, lat = p[0], p[1]
            else:
                continue
            try:
                pts.append(self.to_enu(float(lat), float(lon)))  # type: ignore[arg-type]
            except (TypeError, ValueError):
                continue
        if len(pts) >= 2 and pts[0] == pts[-1]:
            pts = pts[:-1]
        if len(pts) < 3:
            return 0
        added = 0
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        c_min = max(0, int(math.floor((min(xs) + self._half) / self.cell_m)))
        c_max = min(self.n - 1, int(math.floor((max(xs) + self._half) / self.cell_m)))
        r_min = max(0, int(math.floor((min(ys) + self._half) / self.cell_m)))
        r_max = min(self.n - 1, int(math.floor((max(ys) + self._half) / self.cell_m)))
        for row in range(r_min, r_max + 1):
            for col in range(c_min, c_max + 1):
                cx, cy = self.cell_center_enu(row, col)
                if _point_in_ring(cx, cy, pts):
                    added += self._block(row, col)
        # edges: sample so thin rings still block the cells they cross
        step = self.cell_m / 2.0
        for i in range(len(pts)):
            (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % len(pts)]
            length = math.hypot(x2 - x1, y2 - y1)
            samples = max(1, int(math.ceil(length / step)))
            for k in range(samples + 1):
                t = k / samples
                cell = self.cell_of_enu(x1 + (x2 - x1) * t, y1 + (y2 - y1) * t)
                if cell is not None:
                    added += self._block(*cell)
        self.features.append({"kind": "perimeter", "vertices": len(pts), "cells_added": added})
        return added

    def add_point(self, lat: float, lon: float, radius_m: float = 0.0) -> int:
        """Block the cell containing the point and every cell centre within ``radius_m``."""
        try:
            east, north = self.to_enu(float(lat), float(lon))
        except (TypeError, ValueError):
            return 0
        radius = max(float(radius_m or 0.0), 0.0)
        added = 0
        centre_cell = self.cell_of_enu(east, north)
        if centre_cell is not None:
            added += self._block(*centre_cell)
        if radius > 0.0:
            c_min = max(0, int(math.floor((east - radius + self._half) / self.cell_m)))
            c_max = min(self.n - 1, int(math.floor((east + radius + self._half) / self.cell_m)))
            r_min = max(0, int(math.floor((north - radius + self._half) / self.cell_m)))
            r_max = min(self.n - 1, int(math.floor((north + radius + self._half) / self.cell_m)))
            for row in range(r_min, r_max + 1):
                for col in range(c_min, c_max + 1):
                    cx, cy = self.cell_center_enu(row, col)
                    if math.hypot(cx - east, cy - north) <= radius:
                        added += self._block(row, col)
        self.features.append({"kind": "point", "radius_m": radius, "cells_added": added})
        return added

    def stats(self) -> Dict[str, Any]:
        total = self.n * self.n
        return {
            "size_m": self.size_m,
            "cell_m": self.cell_m,
            "n_side": self.n,
            "total_cells": total,
            "blocked_cells": self._blocked,
            "blocked_fraction": (self._blocked / total) if total else 0.0,
            "features": len(self.features),
            "center": {"lat": self.center.lat, "lon": self.center.lon},
            "frame": "ENU equirectangular",
        }


# ---------------------------------------------------------------------------
# Douglas-Peucker
# ---------------------------------------------------------------------------


def _perp_distance(p: Tuple[float, float], a: Tuple[float, float], b: Tuple[float, float]) -> float:
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    seg = dx * dx + dy * dy
    if seg <= 1e-18:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def douglas_peucker(
    points: Sequence[Tuple[float, float]], epsilon: float
) -> List[Tuple[float, float]]:
    """Classic Douglas-Peucker simplification (iterative, keeps endpoints)."""
    n = len(points)
    if n <= 2:
        return list(points)
    keep = [False] * n
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        lo, hi = stack.pop()
        if hi - lo < 2:
            continue
        best_d = -1.0
        best_i = -1
        for i in range(lo + 1, hi):
            d = _perp_distance(points[i], points[lo], points[hi])
            if d > best_d:
                best_d, best_i = d, i
        if best_d > epsilon and best_i > 0:
            keep[best_i] = True
            stack.append((lo, best_i))
            stack.append((best_i, hi))
    return [p for p, k in zip(points, keep) if k]


def decimate(
    points: Sequence[Tuple[float, float]], max_points: int, base_epsilon: float
) -> List[Tuple[float, float]]:
    """Douglas-Peucker with epsilon doubled until ``<= max_points`` remain."""
    pts = list(points)
    if len(pts) <= max_points:
        return pts
    eps = max(base_epsilon, 1e-6)
    for _ in range(40):
        simplified = douglas_peucker(pts, eps)
        if len(simplified) <= max_points:
            return simplified
        eps *= 2.0
    # fallback: uniform subsample keeping the endpoints
    if max_points <= 2:
        return [pts[0], pts[-1]]
    idx = [round(i * (len(pts) - 1) / (max_points - 1)) for i in range(max_points)]
    return [pts[i] for i in sorted(set(idx))]


# ---------------------------------------------------------------------------
# A* planner
# ---------------------------------------------------------------------------


def _octile(r1: int, c1: int, r2: int, c2: int) -> float:
    dr, dc = abs(r1 - r2), abs(c1 - c2)
    return (dr + dc) + (SQRT2 - 2.0) * min(dr, dc)


def _astar(
    grid: OccupancyGrid,
    start: Tuple[int, int],
    goal: Tuple[int, int],
    turn_bias: float,
    bias_weight: float,
    max_expansions: int,
) -> Tuple[Optional[List[Tuple[int, int]]], float, int]:
    """A* on the grid. Returns (cells, cost, expansions); cells is None when unreachable."""
    n = grid.n
    blocked = grid.blocked_cell
    bias = max(-1.0, min(1.0, float(turn_bias or 0.0)))
    weight = max(float(bias_weight or 0.0), 0.0) * abs(bias)
    use_dir = weight > 0.0
    prefer_right = bias > 0.0

    # straight start->goal line in cell units for the side term
    sr, sc = start
    gr, gc = goal
    line_dr, line_dc = gr - sr, gc - sc
    line_len = math.hypot(line_dr, line_dc)

    def side_penalty(r: int, c: int) -> float:
        if not use_dir or line_len < 1e-9:
            return 0.0
        # cross > 0 → cell lies to the LEFT of the start->goal direction (east/north frame)
        cross = (line_dc * (r - sr) - line_dr * (c - sc)) / line_len
        against = cross > 0.0 if prefer_right else cross < 0.0
        if not against:
            return 0.0
        return weight * min(1.0, abs(cross) / 2.0)

    def turn_penalty(prev_dir: int, new_dir: int) -> float:
        if not use_dir or prev_dir < 0 or prev_dir == new_dir:
            return 0.0
        delta = wrap_deg(_DIR_HEADING_DEG[new_dir] - _DIR_HEADING_DEG[prev_dir])
        turning_right = delta > 0.0
        against = (not turning_right) if prefer_right else turning_right
        return weight * abs(delta) / 45.0 if against else 0.0

    start_state = (sr, sc, -1)
    g_cost: Dict[Tuple[int, int, int], float] = {start_state: 0.0}
    parent: Dict[Tuple[int, int, int], Optional[Tuple[int, int, int]]] = {start_state: None}
    closed: set = set()
    counter = 0
    open_heap: List[Tuple[float, int, Tuple[int, int, int]]] = [
        (_octile(sr, sc, gr, gc), counter, start_state)
    ]
    expansions = 0
    goal_state: Optional[Tuple[int, int, int]] = None
    while open_heap:
        _, _, state = heapq.heappop(open_heap)
        if state in closed:
            continue
        closed.add(state)
        expansions += 1
        r, c, d = state
        if (r, c) == goal:
            goal_state = state
            break
        if expansions > max_expansions:
            break
        base = g_cost[state]
        for nd, (dr, dc) in enumerate(_DIRS):
            nr, nc = r + dr, c + dc
            if not (0 <= nr < n and 0 <= nc < n) or blocked(nr, nc):
                continue
            if dr and dc and (blocked(r + dr, c) or blocked(r, c + dc)):
                continue  # no corner cutting
            step = SQRT2 if (dr and dc) else 1.0
            cost = base + step + turn_penalty(d, nd) + side_penalty(nr, nc)
            ns = (nr, nc, nd if use_dir else -1)
            if cost < g_cost.get(ns, math.inf):
                g_cost[ns] = cost
                parent[ns] = state
                counter += 1
                heapq.heappush(open_heap, (cost + _octile(nr, nc, gr, gc), counter, ns))
    if goal_state is None:
        return None, math.inf, expansions
    cells: List[Tuple[int, int]] = []
    cur: Optional[Tuple[int, int, int]] = goal_state
    while cur is not None:
        cells.append((cur[0], cur[1]))
        cur = parent[cur]
    cells.reverse()
    return cells, g_cost[goal_state], expansions


def plan(
    grid: OccupancyGrid,
    start: GeoPoint,
    goal: GeoPoint,
    turn_bias: float = 0.0,
    bias_weight: float = 0.5,
    max_expansions: int = 500_000,
) -> NavPath:
    """A* route from ``start`` to ``goal`` over ``grid`` → ``NavPath`` (spec §8)."""
    stats = grid.stats()
    bias = max(-1.0, min(1.0, float(turn_bias or 0.0)))

    def infeasible(note: str) -> NavPath:
        return NavPath(
            start=start,
            goal=goal,
            waypoints=[],
            geojson=None,
            blocked_cells=stats["blocked_cells"],
            total_cells=stats["total_cells"],
            cost=None,
            feasible=False,
            turn_bias=bias,
            note=note,
        )

    if not isinstance(start, GeoPoint) or not isinstance(goal, GeoPoint):
        return infeasible("start and goal must be GeoPoint")
    s_enu = grid.to_enu(start.lat, start.lon)
    g_enu = grid.to_enu(goal.lat, goal.lon)
    s_cell = grid.cell_of_enu(*s_enu)
    g_cell = grid.cell_of_enu(*g_enu)
    if s_cell is None:
        return infeasible(f"start outside grid ({stats['size_m']:.0f} m around centre)")
    if g_cell is None:
        return infeasible(f"goal outside grid ({stats['size_m']:.0f} m around centre)")
    if grid.blocked_cell(*s_cell):
        return infeasible("start cell is blocked")
    if grid.blocked_cell(*g_cell):
        return infeasible("goal cell is blocked")

    cells, astar_cost, expansions = _astar(grid, s_cell, g_cell, bias, bias_weight, max_expansions)
    if cells is None:
        if expansions > max_expansions:
            return infeasible(
                f"search budget exhausted after {expansions} expansions; no path found"
            )
        return infeasible(f"goal unreachable: no free path ({expansions} cells expanded)")

    enu_pts: List[Tuple[float, float]] = [grid.cell_center_enu(r, c) for (r, c) in cells]
    enu_pts[0] = s_enu
    enu_pts[-1] = g_enu
    if len(enu_pts) == 1:
        enu_pts = [s_enu, g_enu]
    simplified = decimate(enu_pts, MAX_WAYPOINTS, grid.cell_m * 0.25)
    length_m = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(enu_pts[:-1], enu_pts[1:]))
    geo_pts = [grid.to_geo(x, y) for (x, y) in simplified]
    waypoints: List[Waypoint] = []
    for i, gp in enumerate(geo_pts):
        note = "start" if i == 0 else ("goal" if i == len(geo_pts) - 1 else "")
        waypoints.append(Waypoint(lat=gp.lat, lon=gp.lon, hold_seconds=0, note=note))
    geojson = {
        "type": "LineString",
        "coordinates": [[gp.lon, gp.lat] for gp in geo_pts],
    }
    side = "right" if bias > 0 else ("left" if bias < 0 else "none")
    note = (
        f"A* 8-neighbour over {grid.n}x{grid.n} grid ({grid.cell_m:g} m cells); "
        f"{len(cells)} cells, {length_m:.1f} m, {len(waypoints)} waypoints "
        f"(Douglas-Peucker <= {MAX_WAYPOINTS}); turn_bias={bias:+.2f} side={side} "
        f"weight={bias_weight:g}; A* cost {astar_cost:.2f} cell-units; {expansions} expansions"
    )
    if len(cells) == 1:
        note = "start and goal share a cell; " + note
    return NavPath(
        start=start,
        goal=goal,
        waypoints=waypoints,
        geojson=geojson,
        blocked_cells=stats["blocked_cells"],
        total_cells=stats["total_cells"],
        cost=length_m,
        feasible=True,
        turn_bias=bias,
        note=note,
    )


# ---------------------------------------------------------------------------
# Reactive avoidance
# ---------------------------------------------------------------------------


def _det_field(det: Any, name: str) -> Any:
    if isinstance(det, Mapping):
        return det.get(name)
    return getattr(det, name, None)


def avoidance_vector(
    detections: Sequence[Any],
    heading_deg: float,
    hfov_deg: float = 90.0,
    near_range_m: float = 10.0,
) -> Dict[str, Any]:
    """Steer away from detections ahead: ``{turn_hint, nearest_range_m|None, ...}``.

    ``turn_hint`` in [-1, 1] (negative = turn left). Each detection with a
    ``bearing_deg`` within ``±hfov_deg/2`` of the heading pushes away from
    its side, weighted by angular proximity and by range when ``range_m`` is
    known (``1 - range/near_range``, 0 beyond ``near_range_m``). Detections
    without a range are treated as near (conservative) and counted in
    ``n_unknown_range``; detections without a bearing are ignored and
    counted in ``n_no_bearing``. Nothing is invented: ``nearest_range_m`` is
    ``None`` unless a detection carried a range.
    """
    half = max(float(hfov_deg or 90.0), 1.0) / 2.0
    near = max(float(near_range_m or 10.0), 1e-6)
    try:
        heading = float(heading_deg or 0.0)
    except (TypeError, ValueError):
        heading = 0.0
    push = 0.0
    considered = no_bearing = unknown_range = 0
    nearest: Optional[float] = None
    nearest_rel: Optional[float] = None
    for det in detections or []:
        if isinstance(det, Detection):
            bearing, rng = det.bearing_deg, det.range_m
        else:
            bearing, rng = _det_field(det, "bearing_deg"), _det_field(det, "range_m")
        try:
            bearing_f = float(bearing) if bearing is not None else None
        except (TypeError, ValueError):
            bearing_f = None
        if bearing_f is None:
            no_bearing += 1
            continue
        rel = wrap_deg(bearing_f - heading)
        if abs(rel) > half:
            continue
        try:
            rng_f = float(rng) if rng is not None else None
        except (TypeError, ValueError):
            rng_f = None
        if rng_f is not None and rng_f >= 0.0:
            w_range = max(0.0, 1.0 - rng_f / near)
            if nearest is None or rng_f < nearest:
                nearest, nearest_rel = rng_f, rel
        else:
            w_range = 1.0
            unknown_range += 1
        w_angle = 1.0 - abs(rel) / half
        weight = w_angle * w_range
        if weight <= 0.0:
            continue
        considered += 1
        # obstacle on the left (rel < 0) → push right (+); dead ahead → push right by convention
        push += weight if rel <= 0.0 else -weight
    turn_hint = max(-1.0, min(1.0, push))
    notes: List[str] = []
    if considered == 0:
        notes.append("no detections ahead with a bearing")
    if unknown_range:
        notes.append(f"{unknown_range} detection(s) without range treated as near")
    if no_bearing:
        notes.append(f"{no_bearing} detection(s) without bearing ignored")
    return {
        "turn_hint": turn_hint,
        "nearest_range_m": nearest,
        "nearest_bearing_rel_deg": nearest_rel,
        "n_considered": considered,
        "n_no_bearing": no_bearing,
        "n_unknown_range": unknown_range,
        "note": "; ".join(notes),
    }


__all__ = [
    "EARTH_RADIUS_M",
    "MAX_WAYPOINTS",
    "OccupancyGrid",
    "avoidance_vector",
    "decimate",
    "douglas_peucker",
    "enu_from_geo",
    "geo_from_enu",
    "plan",
    "wrap_deg",
]
