"""Mission plan validation, Redis persistence, and minimal executor for Psathyrella."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

import redis.asyncio as redis
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://192.168.0.189:6379/0")
MISSION_KEY_PREFIX = "psathyrella:mission:"

VALID_TASK_KINDS = {
    "transit",
    "loiter",
    "survey",
    "track",
    "solar_reposition",
    "station_keep",
}
VALID_COMMS_LOSS_POLICIES = {"rtl", "hold", "continue"}

_redis_client: Optional[redis.Redis] = None


class MissionTask(BaseModel):
    id: str
    kind: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    radius_m: Optional[float] = Field(default=None, alias="radiusM")
    loiter_s: Optional[int] = Field(default=None, alias="loiterS")
    note: Optional[str] = None

    model_config = {"populate_by_name": True}

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, value: str) -> str:
        normalized = (value or "").strip().lower()
        if normalized not in VALID_TASK_KINDS:
            raise ValueError(f"invalid_task_kind:{value}")
        return normalized


class MissionPlanRecord(BaseModel):
    id: str
    name: str
    tasks: List[MissionTask]
    geofence: Optional[List[List[float]]] = None
    comms_loss_policy: Literal["rtl", "hold", "continue"] = Field(default="rtl", alias="commsLossPolicy")
    valid_until_ms: Optional[int] = Field(default=None, alias="validUntilMs")
    roe: Optional[str] = None
    signature: Optional[str] = None
    created_ms: int = Field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp() * 1000), alias="createdMs")

    model_config = {"populate_by_name": True}


async def _get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True,
        )
    return _redis_client


def _normalize_plan_dict(plan: Dict[str, Any]) -> Dict[str, Any]:
    """Accept camelCase from GCS contract; normalize for Pydantic."""
    normalized = dict(plan)
    if "commsLossPolicy" in normalized and "comms_loss_policy" not in normalized:
        normalized["comms_loss_policy"] = normalized["commsLossPolicy"]
    if "validUntilMs" in normalized and "valid_until_ms" not in normalized:
        normalized["valid_until_ms"] = normalized["validUntilMs"]
    if "createdMs" in normalized and "created_ms" not in normalized:
        normalized["created_ms"] = normalized["createdMs"]
    tasks = normalized.get("tasks")
    if isinstance(tasks, list):
        fixed_tasks: List[Dict[str, Any]] = []
        for task in tasks:
            if not isinstance(task, dict):
                continue
            t = dict(task)
            if "radiusM" in t and "radius_m" not in t:
                t["radius_m"] = t["radiusM"]
            if "loiterS" in t and "loiter_s" not in t:
                t["loiter_s"] = t["loiterS"]
            fixed_tasks.append(t)
        normalized["tasks"] = fixed_tasks
    return normalized


def validate_mission_plan_dict(plan: Dict[str, Any]) -> MissionPlanRecord:
    """Validate MissionPlan shape; raise ValueError on invalid input."""
    if not plan.get("id"):
        raise ValueError("mission.upload requires params.plan.id")
    tasks = plan.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("mission.upload requires non-empty params.plan.tasks")

    policy = str(plan.get("commsLossPolicy") or plan.get("comms_loss_policy") or "rtl").lower()
    if policy not in VALID_COMMS_LOSS_POLICIES:
        raise ValueError(f"invalid_comms_loss_policy:{policy}")

    geofence = plan.get("geofence")
    if geofence is not None:
        if not isinstance(geofence, list) or len(geofence) < 3:
            raise ValueError("geofence requires at least 3 points")

    valid_until = plan.get("validUntilMs") if plan.get("validUntilMs") is not None else plan.get("valid_until_ms")
    if valid_until is not None:
        try:
            until_ms = int(valid_until)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid validUntilMs") from exc
        if until_ms < int(datetime.now(timezone.utc).timestamp() * 1000):
            raise ValueError("mission plan expired (validUntilMs in past)")

    return MissionPlanRecord.model_validate(_normalize_plan_dict(plan))


async def load_mission_plan(plan: Dict[str, Any], *, device_id: str) -> MissionPlanRecord:
    """Validate and persist mission plan to Redis."""
    record = validate_mission_plan_dict(plan)
    client = await _get_redis()
    key = f"{MISSION_KEY_PREFIX}{device_id}"
    await client.set(key, record.model_dump_json(by_alias=True), ex=86400 * 7)
    return record


async def fetch_mission_plan(device_id: str) -> Optional[MissionPlanRecord]:
    client = await _get_redis()
    payload = await client.get(f"{MISSION_KEY_PREFIX}{device_id}")
    if not payload:
        return None
    try:
        data = json.loads(payload)
        return MissionPlanRecord.model_validate(_normalize_plan_dict(data))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to parse mission plan for %s: %s", device_id, exc)
        return None


def _point_in_polygon(lat: float, lon: float, polygon: List[List[float]]) -> bool:
    """Ray-casting point-in-polygon for geofence [[lat,lon], ...]."""
    if len(polygon) < 3:
        return True
    inside = False
    j = len(polygon) - 1
    for i in range(len(polygon)):
        yi, xi = polygon[i][0], polygon[i][1]
        yj, xj = polygon[j][0], polygon[j][1]
        intersect = ((yi > lat) != (yj > lat)) and (
            lon < (xj - xi) * (lat - yi) / (yj - yi + 1e-12) + xi
        )
        if intersect:
            inside = not inside
        j = i
    return inside


class PsathyrellaMissionExecutor:
    """Shadow behavior-tree executor on MAS; edge Jetson copy is authoritative when dark."""

    def __init__(self, device_id: str) -> None:
        self.device_id = device_id
        self.active_plan: Optional[MissionPlanRecord] = None
        self.active_task_id: Optional[str] = None
        self.phase: str = "idle"
        self.aborted: bool = False
        self.geofence_breach: bool = False
        self.comms_lost: bool = False
        self.last_heartbeat_ms: Optional[int] = None

    def load(self, record: MissionPlanRecord) -> None:
        self.active_plan = record
        self.active_task_id = record.tasks[0].id if record.tasks else None
        self.phase = "executing" if record.tasks else "loaded"
        self.aborted = False
        self.geofence_breach = False
        self.comms_lost = False

    def abort(self) -> None:
        self.aborted = True
        self.phase = "aborted"
        self.active_task_id = None

    def record_heartbeat(self, at_ms: Optional[int] = None) -> None:
        self.last_heartbeat_ms = at_ms if at_ms is not None else int(datetime.now(timezone.utc).timestamp() * 1000)
        if self.comms_lost:
            self.comms_lost = False

    def tick(
        self,
        *,
        pose: Optional[Dict[str, Any]] = None,
        heartbeat_timeout_s: int = 120,
        now_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        One behavior-tree evaluation step (~1 Hz on edge; shadow mirror on MAS).

        Returns guidance hints and alert codes for SSE/telemetry consumers.
        """
        now = now_ms if now_ms is not None else int(datetime.now(timezone.utc).timestamp() * 1000)
        alerts: List[Dict[str, Any]] = []
        guidance: Dict[str, Any] = {"status": "idle", "mode_hint": "STATION_KEEP"}

        if self.aborted or self.active_plan is None:
            return {"phase": self.phase, "alerts": alerts, "guidance": guidance}

        if self.last_heartbeat_ms is not None:
            elapsed_s = (now - self.last_heartbeat_ms) / 1000.0
            if elapsed_s > heartbeat_timeout_s:
                self.comms_lost = True
                policy = self.active_plan.comms_loss_policy
                if policy == "rtl":
                    guidance["mode_hint"] = "RTL"
                elif policy == "hold":
                    guidance["mode_hint"] = "STATION_KEEP"
                else:
                    guidance["mode_hint"] = "AUTO"
                alerts.append({"code": "COMMS_LOST", "level": "warn", "policy": policy})

        lat = _num_pose(pose, "lat")
        lon = _num_pose(pose, "lon")
        geofence = self.active_plan.geofence
        if geofence and lat is not None and lon is not None:
            if not _point_in_polygon(lat, lon, geofence):
                self.geofence_breach = True
                guidance["mode_hint"] = "RTL"
                alerts.append({"code": "GEOFENCE_BREACH", "level": "crit"})

        task = self._active_task()
        if task is None:
            self.phase = "complete"
            guidance["status"] = "mission_complete"
            return {"phase": self.phase, "alerts": alerts, "guidance": guidance, "activeTaskId": None}

        guidance["activeTaskId"] = task.id
        guidance["taskKind"] = task.kind
        guidance["status"] = "executing"
        self.phase = "executing"

        if task.kind == "transit" and task.lat is not None and task.lon is not None:
            guidance["mode_hint"] = "GUIDED"
            guidance["target"] = {"lat": task.lat, "lon": task.lon}
            if lat is not None and lon is not None:
                dist_m = _haversine_m(lat, lon, task.lat, task.lon)
                guidance["distanceM"] = round(dist_m, 1)
                if dist_m <= float(task.radius_m or 15.0):
                    self._advance_task()
        elif task.kind == "loiter":
            guidance["mode_hint"] = "STATION_KEEP"
            if task.lat is not None and task.lon is not None:
                guidance["target"] = {"lat": task.lat, "lon": task.lon, "loiterS": task.loiter_s}
        elif task.kind == "station_keep":
            guidance["mode_hint"] = "STATION_KEEP"
        elif task.kind == "survey":
            guidance["mode_hint"] = "AUTO"
            guidance["surveyRadiusM"] = task.radius_m
        elif task.kind == "track":
            guidance["mode_hint"] = "SIGNAL_FOLLOW"
        elif task.kind == "solar_reposition":
            guidance["mode_hint"] = "STATION_KEEP"
            guidance["solarReposition"] = True

        return {
            "phase": self.phase,
            "missionId": self.active_plan.id,
            "activeTaskId": self.active_task_id,
            "alerts": alerts,
            "guidance": guidance,
            "commsLossPolicy": self.active_plan.comms_loss_policy,
            "geofenceBreached": self.geofence_breach,
        }

    def _active_task(self) -> Optional[MissionTask]:
        if not self.active_plan or not self.active_task_id:
            return None
        return next((t for t in self.active_plan.tasks if t.id == self.active_task_id), None)

    def _advance_task(self) -> None:
        if not self.active_plan or not self.active_task_id:
            return
        ids = [t.id for t in self.active_plan.tasks]
        try:
            idx = ids.index(self.active_task_id)
        except ValueError:
            self.active_task_id = None
            return
        if idx + 1 < len(ids):
            self.active_task_id = ids[idx + 1]
        else:
            self.active_task_id = None
            self.phase = "complete"

    @property
    def active_mission_id(self) -> Optional[str]:
        if self.aborted or self.active_plan is None:
            return None
        return self.active_plan.id


def _num_pose(pose: Optional[Dict[str, Any]], key: str) -> Optional[float]:
    if not pose:
        return None
    value = pose.get(key)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    from math import asin, cos, radians, sin, sqrt

    r = 6371000.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * r * asin(sqrt(a))


_executors: Dict[str, PsathyrellaMissionExecutor] = {}


def get_mission_executor(device_id: str) -> PsathyrellaMissionExecutor:
    if device_id not in _executors:
        _executors[device_id] = PsathyrellaMissionExecutor(device_id)
    return _executors[device_id]
