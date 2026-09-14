"""Psathyrella / MycaControl droid plug (spec §2 ``droid``, §11.3).

``observe()`` reads the device's telemetry **in-process** through
``device_registry_api.get_device_telemetry`` (no HTTP self-call) and, when
a detector is available (remote Jetson ``/detect`` snapshot or the local
YOLO26+SAHI on ``plug_config.frame_ref``), one camera detection frame.
Every device call is wrapped in ``try/except`` with a 3 s budget and turns
into a note when it fails.

``act()`` always returns the guidance payload
``{mode, heading_delta_deg, throttle_pct, waypoints, camera_point_at,
dry_run, actuated, avani}``. Actuation (waypoint save + camera point-at)
is **triple-gated**: session ``dry_run=False`` **and** env
``FLYBRAIN_DROID_ACTUATE=1`` **and** an AVANI ``approved=True`` decision on
``Proposal(source_agent="flybrain-droid", action_type="navigation",
risk_tier=MEDIUM, reversibility=0.8)``. The default is dry-run and AVANI
is not even consulted until the first two gates pass.
"""

from __future__ import annotations

import asyncio
import math
from typing import Any, Dict, List, Mapping, Optional, Tuple

from mycosoft_mas.flybrain.config import _env_flag
from mycosoft_mas.flybrain.plugs.base import FlyBrainPlug, PlugContext
from mycosoft_mas.flybrain.schemas import (
    ORIGIN_SIMULATED,
    DetectionFrame,
    GeoPoint,
    MotorAction,
    NavPath,
    Observation,
)

DEVICE_BUDGET_S = 3.0
ACTUATE_ENV = "FLYBRAIN_DROID_ACTUATE"
DEFAULT_GRID_SIZE_M = 400.0
DEFAULT_CELL_M = 5.0
DETECTION_POINT_RADIUS_M = 5.0
EARTH_RADIUS_M = 6371008.8


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


def _first(mapping: Mapping[str, Any], *keys: str) -> Optional[float]:
    for key in keys:
        if key in mapping:
            value = _num(mapping.get(key))
            if value is not None:
                return value
    return None


def extract_pose(telemetry: Any) -> Dict[str, Optional[float]]:
    """``{lat, lon, heading_deg, speed_kn}`` from a buoy telemetry dict (None when absent)."""
    out: Dict[str, Optional[float]] = {
        "lat": None,
        "lon": None,
        "heading_deg": None,
        "speed_kn": None,
    }
    if not isinstance(telemetry, Mapping):
        return out
    gps = telemetry.get("gps") if isinstance(telemetry.get("gps"), Mapping) else {}
    pose = telemetry.get("pose") if isinstance(telemetry.get("pose"), Mapping) else {}
    for src in (pose, gps, telemetry):
        if out["lat"] is None:
            out["lat"] = _first(src, "lat", "latitude")
        if out["lon"] is None:
            out["lon"] = _first(src, "lon", "lng", "longitude")
        if out["heading_deg"] is None:
            out["heading_deg"] = _first(
                src, "heading_deg", "headingDeg", "heading", "cog", "compass_deg"
            )
        if out["speed_kn"] is None:
            out["speed_kn"] = _first(src, "speed_kn", "speedKn", "sog")
    return out


def _bearing_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> Tuple[float, float]:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    x = math.sin(dlon) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlon)
    bearing = math.degrees(math.atan2(x, y)) % 360.0
    east = dlon * EARTH_RADIUS_M * math.cos((phi1 + phi2) / 2.0)
    north = (phi2 - phi1) * EARTH_RADIUS_M
    return bearing, math.hypot(east, north)


# ---------------------------------------------------------------------------
# In-process device access (module-level so tests can monkeypatch them)
# ---------------------------------------------------------------------------


async def get_device_telemetry(device_id: str) -> Dict[str, Any]:
    """In-process ``device_registry_api.get_device_telemetry`` (raises on failure)."""
    from mycosoft_mas.core.routers.device_registry_api import get_device_telemetry as _get

    body = await _get(device_id=device_id)
    return body if isinstance(body, dict) else {"raw": body}


async def evaluate_navigation_proposal(
    device_id: str, guidance: Mapping[str, Any], session_id: str
) -> Dict[str, Any]:
    """AVANI governor decision for a FlyBrain navigation action (spec §11.3)."""
    from mycosoft_mas.avani.governor.governor import Proposal, RiskTier
    from mycosoft_mas.core.routers.avani_router import get_governor

    proposal = Proposal(
        source_agent="flybrain-droid",
        action_type="navigation",
        description=(
            f"FlyBrain ({ORIGIN_SIMULATED}) guidance for {device_id}: "
            f"heading_delta {float(guidance.get('heading_delta_deg', 0.0)):+.1f}°, "
            f"throttle {float(guidance.get('throttle_pct', 0.0)):.0f} %, "
            f"{len(guidance.get('waypoints') or [])} waypoints, camera point-at "
            f"{'set' if guidance.get('camera_point_at') else 'none'}."
        ),
        risk_tier=RiskTier.MEDIUM,
        reversibility=0.8,
        metadata={
            "session_id": session_id,
            "device_id": device_id,
            "origin": ORIGIN_SIMULATED,
            "n_waypoints": len(guidance.get("waypoints") or []),
        },
    )
    decision = await get_governor().evaluate_proposal(proposal)
    return decision.to_dict()


async def save_waypoints(device_id: str, waypoints: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Persist waypoints exactly like ``psathyrella_api.mutate_waypoints(replace)``."""
    from mycosoft_mas.core.routers import psathyrella_api
    from mycosoft_mas.devices.psathyrella.autonomy import WaypointRecord

    records = [
        WaypointRecord(
            latitude=float(wp["lat"]),
            longitude=float(wp["lon"]),
            hold_seconds=int(wp.get("hold_seconds", 0) or 0),
            metadata={"source": "flybrain", "origin": ORIGIN_SIMULATED, "note": wp.get("note", "")},
        )
        for wp in waypoints
    ]
    await psathyrella_api._save_waypoints(device_id, records)
    state = psathyrella_api._autonomy_controller.replace_waypoints(records)
    return {"count": len(records), "autonomy_state": state.model_dump()}


async def point_camera(
    device_id: str, bearing_deg: float, pitch_deg: float = 0.0
) -> Dict[str, Any]:
    """Send ``psa_camera_point`` through the device registry (in-process)."""
    from mycosoft_mas.core.routers import device_registry_api, psathyrella_api

    psathyrella_api._autonomy_controller.point_camera(
        bearing_deg=float(bearing_deg) % 360.0, pitch_deg=float(pitch_deg), hold_seconds=0
    )
    cmd = device_registry_api.DeviceCommand(
        command="psa_camera_point",
        params={
            "bearing_deg": float(bearing_deg) % 360.0,
            "pitch_deg": float(pitch_deg),
            "hold_seconds": 0,
        },
        timeout=DEVICE_BUDGET_S,
    )
    response = await device_registry_api.send_device_command(
        device_id=device_id, cmd=cmd, use_mycorrhizae=True
    )
    return response if isinstance(response, dict) else {"response": response}


def actuation_enabled_by_env() -> bool:
    return _env_flag(ACTUATE_ENV, False)


# ---------------------------------------------------------------------------
# Plug
# ---------------------------------------------------------------------------


class DroidPlug(FlyBrainPlug):
    """Psathyrella / MycaControl adapter with triple-gated actuation."""

    name = "droid"
    navigates = True
    actuates = True

    def __init__(self, config=None, settings=None) -> None:
        super().__init__(config, settings)
        self.pose: Dict[str, Optional[float]] = extract_pose(None)
        self.telemetry: Dict[str, Any] = {}
        self.telemetry_ok = False
        self.last_frame: Optional[DetectionFrame] = None
        self.last_guidance: Dict[str, Any] = {}
        self.last_nav: Optional[NavPath] = None

    # -- config ---------------------------------------------------------------

    def device_id(self) -> str:
        if self.config.device_id:
            return str(self.config.device_id)
        try:
            from mycosoft_mas.devices.psathyrella.constants import PSATHYRELLA_DEVICE_ID

            return PSATHYRELLA_DEVICE_ID
        except Exception:  # noqa: BLE001
            return "psathyrella"

    def goal(self) -> Optional[GeoPoint]:
        cfg = self.config.plug_config if isinstance(self.config.plug_config, dict) else {}
        goal = cfg.get("goal")
        if isinstance(goal, Mapping):
            lat, lon = _num(goal.get("lat")), _num(goal.get("lon", goal.get("lng")))
            if lat is not None and lon is not None:
                return GeoPoint(lat=lat, lon=lon)
        return None

    def describe(self) -> Dict[str, Any]:
        base = super().describe()
        base.update(
            {
                "device_id": self.device_id(),
                "goal": self.goal().model_dump() if self.goal() else None,
                "observe": "in-process device telemetry + camera detections (remote /detect "
                "snapshot or local YOLO26+SAHI on plug_config.frame_ref)",
                "act": "guidance payload; waypoints + camera point-at only when dry_run=False "
                f"and {ACTUATE_ENV}=1 and AVANI approves",
                "gates": {
                    "dry_run": bool(self.config.dry_run),
                    "env_actuate": actuation_enabled_by_env(),
                    "avani": "consulted only when the first two gates pass",
                },
            }
        )
        return base

    # -- observe ----------------------------------------------------------------

    async def _observe_telemetry(self, ctx: PlugContext, notes: List[str]) -> Optional[Observation]:
        device_id = self.device_id()
        try:
            telemetry = await asyncio.wait_for(get_device_telemetry(device_id), DEVICE_BUDGET_S)
        except asyncio.TimeoutError:
            self.telemetry_ok = False
            notes.append(
                f"droid: telemetry for {device_id} timed out after {DEVICE_BUDGET_S:.0f} s"
            )
            return None
        except Exception as exc:  # noqa: BLE001 - HTTPException 404/503, connection errors
            self.telemetry_ok = False
            detail = getattr(exc, "detail", None) or str(exc)
            notes.append(
                f"droid: telemetry unavailable for {device_id} ({type(exc).__name__}: {detail})"
            )
            return None
        self.telemetry = telemetry
        self.telemetry_ok = True
        pose = extract_pose(telemetry)
        self.pose = pose
        payload: Dict[str, Any] = {"device_id": device_id}
        if pose["heading_deg"] is None:
            notes.append(f"droid: telemetry for {device_id} carries no heading; no turn drive")
        else:
            payload["heading_deg"] = pose["heading_deg"]
        if pose["speed_kn"] is not None:
            payload["speed_kn"] = pose["speed_kn"]
        goal = self.goal()
        if goal is not None and pose["lat"] is not None and pose["lon"] is not None:
            bearing, distance = _bearing_distance(pose["lat"], pose["lon"], goal.lat, goal.lon)
            payload["target_bearing_deg"] = bearing
            payload["distance_to_goal_m"] = distance
        elif goal is not None:
            notes.append("droid: goal configured but telemetry has no GPS fix; no goal drive")
        if len(payload) == 1:
            notes.append("droid: telemetry has no usable pose fields; no drive from telemetry")
            return None
        return Observation(
            kind="telemetry", payload=payload, t_ms=ctx.t_ms, source=f"device:{device_id}"
        )

    async def _observe_detections(
        self, ctx: PlugContext, notes: List[str]
    ) -> Optional[Observation]:
        try:
            detector = ctx.get_detector()
        except Exception as exc:  # noqa: BLE001
            notes.append(f"droid: detector unavailable ({type(exc).__name__}: {exc})")
            return None
        if detector is None:
            notes.append("droid: no detector configured; no camera observation")
            return None
        pose = None
        if self.pose.get("lat") is not None and self.pose.get("lon") is not None:
            pose = {
                "lat": self.pose["lat"],
                "lon": self.pose["lon"],
                "heading_deg": self.pose.get("heading_deg"),
            }
        frame: Optional[DetectionFrame] = None
        frame_ref = ctx.plug_config.get("frame_ref") or ctx.plug_config.get("image_path")
        try:
            remote = getattr(detector, "remote", None)
            if remote is not None and getattr(remote, "url", None):
                frame = await asyncio.wait_for(
                    detector.asnapshot(ctx.plug_config.get("camera_source"), pose=pose),
                    DEVICE_BUDGET_S,
                )
            elif frame_ref and getattr(detector, "available", False):
                frame = await asyncio.wait_for(
                    detector.adetect(str(frame_ref), pose=pose, source="droid", t_ms=ctx.t_ms),
                    DEVICE_BUDGET_S + 5.0,
                )
            else:
                health = detector.health()
                reason = health.reason or "no remote detector URL and no plug_config.frame_ref"
                notes.append(f"droid: detections unavailable ({reason}); no boxes invented")
                return None
        except asyncio.TimeoutError:
            notes.append("droid: detector timed out; no boxes invented")
            return None
        except Exception as exc:  # noqa: BLE001 - DetectorUnavailable and transport errors
            notes.append(
                f"droid: detections unavailable ({type(exc).__name__}: {exc}); no boxes invented"
            )
            return None
        if frame is None or not frame.available:
            notes.append(
                f"droid: detector reported unavailable ({getattr(frame, 'note', '') or 'no reason'})"
            )
            return None
        self.last_frame = frame
        payload = frame.model_dump()
        if self.pose.get("heading_deg") is not None:
            payload["heading_deg"] = self.pose["heading_deg"]
        return Observation(kind="detections", payload=payload, t_ms=ctx.t_ms, source="droid-camera")

    async def observe(self, ctx: PlugContext) -> List[Observation]:
        notes: List[str] = []
        out: List[Observation] = []
        self.last_frame = None
        telemetry_obs = await self._observe_telemetry(ctx, notes)
        if telemetry_obs is not None:
            out.append(telemetry_obs)
        det_obs = await self._observe_detections(ctx, notes)
        if det_obs is not None:
            out.append(det_obs)
        self.last_observe_notes = notes
        ctx.notes.extend(notes)
        return out

    # -- navigate -----------------------------------------------------------------

    async def navigate(
        self, ctx: PlugContext, action: MotorAction, detections: Optional[DetectionFrame]
    ) -> Optional[NavPath]:
        goal = self.goal()
        if goal is None:
            self.last_nav = None
            return None
        lat, lon = self.pose.get("lat"), self.pose.get("lon")
        if lat is None or lon is None:
            self.last_nav = NavPath(
                goal=goal,
                feasible=False,
                note="no GPS fix in device telemetry; cannot plan to goal",
            )
            return self.last_nav
        start = GeoPoint(lat=lat, lon=lon)
        cfg = ctx.plug_config
        size_m = _num(cfg.get("grid_size_m")) or DEFAULT_GRID_SIZE_M
        cell_m = _num(cfg.get("cell_m")) or DEFAULT_CELL_M
        self.last_nav = await asyncio.to_thread(
            self._plan, start, goal, action, detections, size_m, cell_m
        )
        return self.last_nav

    @staticmethod
    def _plan(
        start: GeoPoint,
        goal: GeoPoint,
        action: MotorAction,
        detections: Optional[DetectionFrame],
        size_m: float,
        cell_m: float,
    ) -> NavPath:
        from mycosoft_mas.flybrain.navigation import OccupancyGrid, plan

        _, distance = _bearing_distance(start.lat, start.lon, goal.lat, goal.lon)
        size = max(size_m, 2.2 * distance + 4 * cell_m)
        centre = GeoPoint(lat=(start.lat + goal.lat) / 2.0, lon=(start.lon + goal.lon) / 2.0)
        grid = OccupancyGrid(centre, size_m=size, cell_m=cell_m)
        if detections is not None and detections.available:
            for det in detections.detections:
                if det.perimeter:
                    grid.add_perimeter(det.perimeter)
                elif det.location is not None:
                    grid.add_point(det.location.lat, det.location.lon, DETECTION_POINT_RADIUS_M)
        return plan(grid, start, goal, turn_bias=float(action.turn))

    # -- act --------------------------------------------------------------------------

    def _guidance(
        self,
        ctx: PlugContext,
        action: MotorAction,
        nav: Optional[NavPath],
        detections: Optional[DetectionFrame],
    ) -> Dict[str, Any]:
        heading = self.pose.get("heading_deg")
        camera: Optional[Dict[str, Any]] = None
        if heading is not None:
            camera = {
                "bearing_deg": (heading + action.heading_delta_deg) % 360.0,
                "pitch_deg": 0.0,
                "hold_seconds": 0,
            }
        waypoints = (
            [wp.model_dump() for wp in nav.waypoints] if (nav is not None and nav.feasible) else []
        )
        return {
            "mode": "flybrain_locomotion" if action.kind == "locomotion" else "hold",
            "origin": ORIGIN_SIMULATED,
            "device_id": self.device_id(),
            "session_id": ctx.session_id,
            "heading_delta_deg": action.heading_delta_deg,
            "throttle_pct": action.throttle_pct,
            "turn": action.turn,
            "confidence": action.confidence,
            "waypoints": waypoints,
            "camera_point_at": camera,
            "current_heading_deg": heading,
            "position": (
                {"lat": self.pose.get("lat"), "lon": self.pose.get("lon")}
                if self.pose.get("lat") is not None
                else None
            ),
            "telemetry_ok": self.telemetry_ok,
            "n_detections": len(detections.detections) if detections is not None else None,
            "nav_feasible": bool(nav.feasible) if nav is not None else None,
            "nav_note": nav.note if nav is not None else None,
            "dry_run": ctx.dry_run,
            "actuated": False,
            "avani": None,
        }

    async def act(
        self,
        ctx: PlugContext,
        action: MotorAction,
        nav: Optional[NavPath],
        detections: Optional[DetectionFrame],
    ) -> Dict[str, Any]:
        guidance = self._guidance(ctx, action, nav, detections)
        env_ok = actuation_enabled_by_env()
        gates = {"dry_run": ctx.dry_run, "env_actuate": env_ok, "avani_approved": None}
        guidance["gates"] = gates
        guidance["observe_notes"] = list(self.last_observe_notes)

        if ctx.dry_run:
            guidance["reason"] = "dry_run=True on this session; guidance returned, nothing actuated"
        elif not env_ok:
            guidance["reason"] = (
                f"{ACTUATE_ENV} is not 1 on MAS; guidance returned, nothing actuated"
            )
        else:
            device_id = self.device_id()
            try:
                decision = await asyncio.wait_for(
                    evaluate_navigation_proposal(device_id, guidance, ctx.session_id),
                    DEVICE_BUDGET_S,
                )
            except Exception as exc:  # noqa: BLE001
                decision = {
                    "approved": False,
                    "reason": f"AVANI unavailable: {type(exc).__name__}: {exc}",
                }
            guidance["avani"] = decision
            approved = bool(decision.get("approved"))
            gates["avani_approved"] = approved
            if not approved:
                guidance["reason"] = f"AVANI did not approve: {decision.get('reason', 'no reason')}"
            elif not guidance["waypoints"] and guidance["camera_point_at"] is None:
                guidance["reason"] = (
                    "all gates passed but there is nothing to actuate (no feasible path, no heading)"
                )
            else:
                steps: Dict[str, Any] = {}
                actuated = False
                if guidance["waypoints"]:
                    try:
                        steps["waypoints"] = await asyncio.wait_for(
                            save_waypoints(device_id, guidance["waypoints"]), DEVICE_BUDGET_S
                        )
                        actuated = True
                    except Exception as exc:  # noqa: BLE001
                        steps["waypoints"] = {"error": f"{type(exc).__name__}: {exc}"}
                if guidance["camera_point_at"] is not None:
                    try:
                        steps["camera"] = await asyncio.wait_for(
                            point_camera(device_id, guidance["camera_point_at"]["bearing_deg"]),
                            DEVICE_BUDGET_S,
                        )
                        actuated = True
                    except Exception as exc:  # noqa: BLE001
                        steps["camera"] = {"error": f"{type(exc).__name__}: {exc}"}
                guidance["actuation"] = steps
                guidance["actuated"] = actuated
                guidance["reason"] = (
                    "actuated: all three gates passed"
                    if actuated
                    else "all gates passed but every actuation step failed (see actuation)"
                )
        self.last_guidance = guidance
        self.last_result = guidance
        return guidance


__all__ = [
    "ACTUATE_ENV",
    "DroidPlug",
    "actuation_enabled_by_env",
    "evaluate_navigation_proposal",
    "extract_pose",
    "get_device_telemetry",
    "point_camera",
    "save_waypoints",
]
