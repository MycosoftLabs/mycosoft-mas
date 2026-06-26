"""Autonomy interfaces for Psathyrella 4-DOF buoy control."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class AutonomyMode(str, Enum):
    """Control modes exposed to future MycaControl/AgaricFlight adapters."""

    MANUAL = "manual"
    WAYPOINT = "waypoint"
    CURRENT_FIGHT_HOLD = "current_fight_hold"
    CAMERA_POINT_AT = "camera_point_at"
    SIGNAL_FOLLOW = "signal_follow"


class SignalFollowMode(str, Enum):
    """Signal-follow modes for acoustics and RF homing."""

    ACOUSTIC = "acoustic"
    RF = "rf"
    OPTICAL = "optical"
    HYBRID = "hybrid"


class WaypointRecord(BaseModel):
    """Waypoint target for a surface buoy mission."""

    waypoint_id: str = Field(default_factory=lambda: str(uuid4()))
    latitude: float
    longitude: float
    hold_seconds: int = Field(default=0, ge=0, le=3600)
    tolerance_m: float = Field(default=2.5, ge=0.5, le=50.0)
    heading_deg: Optional[float] = Field(default=None, ge=0.0, le=360.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CameraPointAtState(BaseModel):
    """Point-at target state for a stabilized camera tower."""

    bearing_deg: float = Field(default=0.0, ge=0.0, le=360.0)
    pitch_deg: float = Field(default=0.0, ge=-90.0, le=90.0)
    hold_seconds: int = Field(default=0, ge=0, le=3600)


class PsathyrellaAutonomyState(BaseModel):
    """Runtime autonomy state snapshot."""

    mode: AutonomyMode = AutonomyMode.MANUAL
    signal_follow_mode: SignalFollowMode = SignalFollowMode.ACOUSTIC
    active_waypoint_id: Optional[str] = None
    current_fight_hold_enabled: bool = False
    camera_point_at: Optional[CameraPointAtState] = None
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PsathyrellaAutonomyController:
    """Minimal autonomy controller facade for future ArduSub adapter wiring."""

    def __init__(self) -> None:
        self._state = PsathyrellaAutonomyState()
        self._waypoints: List[WaypointRecord] = []

    @property
    def state(self) -> PsathyrellaAutonomyState:
        return self._state

    def list_waypoints(self) -> List[WaypointRecord]:
        return list(self._waypoints)

    def replace_waypoints(self, waypoints: List[WaypointRecord]) -> PsathyrellaAutonomyState:
        self._waypoints = list(waypoints)
        self._state.active_waypoint_id = waypoints[0].waypoint_id if waypoints else None
        self._state.mode = AutonomyMode.WAYPOINT if waypoints else AutonomyMode.MANUAL
        self._touch()
        return self._state

    def set_mode(self, mode: AutonomyMode, signal_follow_mode: Optional[SignalFollowMode] = None) -> PsathyrellaAutonomyState:
        self._state.mode = mode
        if signal_follow_mode is not None:
            self._state.signal_follow_mode = signal_follow_mode
        self._state.current_fight_hold_enabled = mode == AutonomyMode.CURRENT_FIGHT_HOLD
        self._touch()
        return self._state

    def point_camera(self, bearing_deg: float, pitch_deg: float, hold_seconds: int = 0) -> PsathyrellaAutonomyState:
        self._state.mode = AutonomyMode.CAMERA_POINT_AT
        self._state.camera_point_at = CameraPointAtState(
            bearing_deg=bearing_deg,
            pitch_deg=pitch_deg,
            hold_seconds=hold_seconds,
        )
        self._touch()
        return self._state

    def compute_guidance(self, latest_position: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Return an adapter-ready guidance payload.

        This intentionally does not execute full autonomy control loops; it provides
        a stable contract for a future MycaControl/AgaricFlight implementation.
        """
        target_waypoint: Optional[WaypointRecord] = None
        if self._state.active_waypoint_id:
            target_waypoint = next(
                (wp for wp in self._waypoints if wp.waypoint_id == self._state.active_waypoint_id),
                None,
            )

        return {
            "mode": self._state.mode,
            "signal_follow_mode": self._state.signal_follow_mode,
            "active_waypoint": target_waypoint.model_dump() if target_waypoint else None,
            "camera_point_at": self._state.camera_point_at.model_dump() if self._state.camera_point_at else None,
            "latest_position": latest_position or {},
            "current_fight_hold_enabled": self._state.current_fight_hold_enabled,
            "status": "ready_for_adapter",
            "updated_at": self._state.updated_at,
        }

    def _touch(self) -> None:
        self._state.updated_at = datetime.now(timezone.utc).isoformat()
