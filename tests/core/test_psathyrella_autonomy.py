from mycosoft_mas.devices.psathyrella.autonomy import (
    AutonomyMode,
    PsathyrellaAutonomyController,
    SignalFollowMode,
    WaypointRecord,
)


def test_replace_waypoints_switches_mode() -> None:
    controller = PsathyrellaAutonomyController()
    waypoint = WaypointRecord(latitude=32.56289, longitude=-117.1357)

    state = controller.replace_waypoints([waypoint])

    assert state.mode == AutonomyMode.WAYPOINT
    assert state.active_waypoint_id == waypoint.waypoint_id
    assert len(controller.list_waypoints()) == 1


def test_camera_point_and_guidance_payload() -> None:
    controller = PsathyrellaAutonomyController()
    controller.set_mode(AutonomyMode.SIGNAL_FOLLOW, SignalFollowMode.ACOUSTIC)
    state = controller.point_camera(bearing_deg=78.5, pitch_deg=-12.0, hold_seconds=30)
    guidance = controller.compute_guidance({"lat": 32.56, "lon": -117.13})

    assert state.mode == AutonomyMode.CAMERA_POINT_AT
    assert guidance["camera_point_at"]["bearing_deg"] == 78.5
    assert guidance["latest_position"]["lat"] == 32.56
