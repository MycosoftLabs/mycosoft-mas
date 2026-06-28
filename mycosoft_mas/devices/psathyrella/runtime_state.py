"""In-memory Psathyrella runtime state (nav mode, arm, thrusters) until MAVLink adapter."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from mycosoft_mas.devices.psathyrella.autonomy import (
    PsathyrellaAutonomyController,
    WaypointRecord,
)

THRUSTER_LABELS = ["BOW-P", "BOW-S", "AFT-P", "AFT-S"]


@dataclass
class ThrusterRuntime:
    id: int
    label: str
    throttle_pct: float = 0.0
    azimuth_deg: float = 0.0
    current_a: Optional[float] = None
    rpm: Optional[float] = None
    faulted: bool = False


VALID_BEARERS = frozenset({"ble", "cellular", "wifi", "lora", "iridium", "starlink"})
VALID_COMMS_LOSS_POLICIES = frozenset({"rtl", "hold", "continue"})


@dataclass
class PsathyrellaRuntimeState:
    armed: bool = False
    mode: str = "MANUAL"
    fight_current: bool = False
    camera_hold_bearing_deg: Optional[float] = None
    commanded_vector: Optional[Dict[str, float]] = None
    thrusters: List[ThrusterRuntime] = field(default_factory=list)
    camera_zoom: Optional[float] = None
    camera_bearing_deg: Optional[float] = None
    camera_tilt_deg: Optional[float] = None
    camera_active: bool = False
    preferred_bearer: Optional[str] = None
    hydrophone_gain_db: Optional[float] = None
    comms_loss_policy: str = "rtl"
    active_mission_id: Optional[str] = None
    last_rf_contact_ms_ago: Optional[int] = None
    last_sat_contact_ms_ago: Optional[int] = None

    def __post_init__(self) -> None:
        if not self.thrusters:
            self.thrusters = [
                ThrusterRuntime(id=i, label=THRUSTER_LABELS[i]) for i in range(4)
            ]


_runtime_by_device: Dict[str, PsathyrellaRuntimeState] = {}
_autonomy_by_device: Dict[str, PsathyrellaAutonomyController] = {}


def get_runtime(device_id: str) -> PsathyrellaRuntimeState:
    if device_id not in _runtime_by_device:
        _runtime_by_device[device_id] = PsathyrellaRuntimeState()
    return _runtime_by_device[device_id]


def get_autonomy_controller(device_id: str) -> PsathyrellaAutonomyController:
    if device_id not in _autonomy_by_device:
        _autonomy_by_device[device_id] = PsathyrellaAutonomyController()
    return _autonomy_by_device[device_id]


def derive_contact_state(
    *,
    rf_connected: bool,
    sat_connected: bool,
    sat_last_contact_ms_ago: Optional[int],
) -> str:
    """Single source for GCS contactState: live | delayed | dark."""
    sat_recent = sat_last_contact_ms_ago is not None and sat_last_contact_ms_ago < 120_000
    if rf_connected:
        return "live"
    if sat_connected or sat_recent:
        return "delayed"
    return "dark"


def last_contact_ms_ago(
    rf_ms: Optional[int],
    sat_ms: Optional[int],
) -> Optional[int]:
    candidates = [v for v in (rf_ms, sat_ms) if v is not None]
    return min(candidates) if candidates else None


def waypoints_for_telemetry(device_id: str) -> tuple[List[Dict[str, Any]], Optional[str]]:
    controller = get_autonomy_controller(device_id)
    waypoints: List[Dict[str, Any]] = []
    for wp in controller.list_waypoints():
        entry: Dict[str, Any] = {
            "id": wp.waypoint_id,
            "lat": wp.latitude,
            "lon": wp.longitude,
        }
        if wp.metadata.get("label"):
            entry["label"] = wp.metadata["label"]
        if wp.metadata.get("loiter"):
            entry["loiter"] = wp.metadata["loiter"]
        waypoints.append(entry)
    return waypoints, controller.state.active_waypoint_id
