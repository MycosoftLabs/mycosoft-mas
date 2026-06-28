"""Tests for Psathyrella GPS NMEA parsing, mission executor, and comms MT queue."""

from __future__ import annotations

import pytest

from mycosoft_mas.devices.psathyrella.comms_bridge import PsathyrellaCommsBridge
from mycosoft_mas.devices.psathyrella.gps_nmea import merge_nmea_from_text, parse_nmea_sentence
from mycosoft_mas.devices.psathyrella.mission_executor import (
    MissionPlanRecord,
    MissionTask,
    PsathyrellaMissionExecutor,
    validate_mission_plan_dict,
)


def test_parse_nmea_gga_sentence() -> None:
    line = "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47"
    block = parse_nmea_sentence(line)
    assert block is not None
    gps = block["gps"]
    assert gps["lat"] is not None
    assert gps["lon"] is not None
    assert gps["satellites"] == 8
    assert gps["lock"] == "locked"


def test_merge_nmea_from_multiline_text() -> None:
    text = (
        "$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A\n"
        "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47"
    )
    merged = merge_nmea_from_text(text)
    assert merged.get("lat") is not None
    assert merged.get("speed_kn") == 22.4


def test_mt_queue_enqueue_and_flush() -> None:
    bridge = PsathyrellaCommsBridge()
    frame = bridge.enqueue_mt_command(
        "psathyrella-buoy-com4",
        {"cmd": "nav.thrust_vector", "params": {"heading": 90}},
        bearer="iridium",
    )
    state = bridge.get_state("psathyrella-buoy-com4")
    assert state["mt_queued"] == 1
    drained = bridge.flush_mt_queue("psathyrella-buoy-com4")
    assert len(drained) == 1
    assert drained[0]["frame_id"] == frame.frame_id
    assert bridge.get_state("psathyrella-buoy-com4")["mt_queued"] == 0


def test_sbd_oversize_guard() -> None:
    bridge = PsathyrellaCommsBridge()
    huge = {"data": "x" * 500}
    packed = bridge.pack_sbd_frame(huge, max_bytes=340)
    assert packed["status"] == "pending"
    assert packed["reason"] == "SBD_OVERSIZE"


def test_mission_executor_transit_advance() -> None:
    plan = validate_mission_plan_dict(
        {
            "id": "m_exec_1",
            "name": "test",
            "tasks": [
                {"id": "t1", "kind": "transit", "lat": 32.56289, "lon": -117.1357, "radiusM": 1000},
                {"id": "t2", "kind": "station_keep"},
            ],
            "commsLossPolicy": "hold",
        }
    )
    executor = PsathyrellaMissionExecutor("psathyrella-buoy-com4")
    executor.load(plan)
    tick = executor.tick(pose={"lat": 32.56289, "lon": -117.1357})
    assert tick["guidance"]["taskKind"] == "transit"
    assert executor.active_task_id == "t2"


def test_mission_geofence_breach() -> None:
    record = MissionPlanRecord(
        id="m_geo",
        name="geo",
        tasks=[MissionTask(id="t1", kind="station_keep")],
        geofence=[[32.55, -117.12], [32.60, -117.12], [32.60, -117.18], [32.55, -117.18]],
        comms_loss_policy="rtl",
    )
    executor = PsathyrellaMissionExecutor("psathyrella-buoy-com4")
    executor.load(record)
    tick = executor.tick(pose={"lat": 32.50, "lon": -117.15})
    assert tick["geofenceBreached"] is True
    assert any(a["code"] == "GEOFENCE_BREACH" for a in tick["alerts"])
