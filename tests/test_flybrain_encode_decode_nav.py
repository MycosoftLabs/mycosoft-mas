"""Tests for FlyBrain encoders (spec §6), decoders (§7) and navigation (§8).

No connectome, no network: the sensorimotor mapping below is a tiny explicit
fixture with the same shape as ``config/flybrain_atlas.yaml``. Real-data
tests are skipped unless ``FLYBRAIN_DATA_DIR`` holds the FlyWire files.
"""

from __future__ import annotations

import math
import os
import time
from pathlib import Path

import pytest

from mycosoft_mas.flybrain.decoders import LocomotionDecoder, PopulationClassifier
from mycosoft_mas.flybrain.encoders import (
    EncoderConfig,
    encode,
    encode_detections,
    encode_earthsim,
    encode_nlm,
    encode_raw_rates,
    encode_telemetry,
    known_groups,
)
from mycosoft_mas.flybrain.navigation import (
    OccupancyGrid,
    avoidance_vector,
    enu_from_geo,
    geo_from_enu,
    plan,
)
from mycosoft_mas.flybrain.schemas import Detection, GeoPoint, MotorAction, NavPath, Observation

SENSORIMOTOR = {
    "inputs": {
        "forward": ["p9_left", "p9_right"],
        "left": ["p9_left"],
        "right": ["p9_right"],
        "attract": ["sugar_grn"],
    },
    "readouts": {
        "forward": ["p9_shared_downstream"],
        "turn_left": ["p9_left_downstream"],
        "turn_right": ["p9_right_downstream"],
        "feeding": ["sugar_downstream"],
    },
}


def _det(cx: float, cy: float = 0.5, w: float = 0.2, h: float = 0.2, **kw) -> dict:
    x1, x2 = (cx - w / 2) * 640, (cx + w / 2) * 640
    y1, y2 = (cy - h / 2) * 480, (cy + h / 2) * 480
    base = {"id": "d1", "cls": "person", "conf": 0.9, "bbox_xyxy": [x1, y1, x2, y2]}
    base.update(kw)
    return base


def _frame(*dets: dict, **extra) -> dict:
    payload = {"frame_w": 640, "frame_h": 480, "detections": list(dets)}
    payload.update(extra)
    return payload


# ---------------------------------------------------------------------------
# Encoders
# ---------------------------------------------------------------------------


def test_detection_left_from_bbox_position():
    rates, notes = encode_detections(_frame(_det(0.2)), SENSORIMOTOR)
    assert rates.get("p9_left", 0.0) > 0.0
    assert rates.get("p9_right", 0.0) == 0.0
    assert "sugar_grn" not in rates


def test_detection_right_from_bbox_position():
    rates, _ = encode_detections(_frame(_det(0.8)), SENSORIMOTOR)
    assert rates.get("p9_right", 0.0) > 0.0
    assert rates.get("p9_left", 0.0) == 0.0


def test_detection_asymmetry_from_bearing_overrides_bbox():
    # bbox says right, bearing (relative to heading 90) says 30 deg to the left
    det = _det(0.8, bearing_deg=60.0)
    rates, _ = encode_detections(_frame(det, heading_deg=90.0), SENSORIMOTOR)
    assert rates.get("p9_left", 0.0) > 0.0
    assert rates.get("p9_right", 0.0) == 0.0
    # heading wraps: bearing 350 with heading 10 is 20 deg left
    rates2, _ = encode_detections(
        _frame(_det(0.8, bearing_deg=350.0), heading_deg=10.0), SENSORIMOTOR
    )
    assert rates2.get("p9_left", 0.0) > 0.0 and rates2.get("p9_right", 0.0) == 0.0


def test_attract_category_routes_to_attract_group():
    rates, _ = encode_detections(_frame(_det(0.7, category="food", cls="apple")), SENSORIMOTOR)
    assert rates.get("sugar_grn", 0.0) > 0.0
    assert rates.get("p9_right", 0.0) > 0.0
    # class-name match also counts, custom attract categories honoured
    cfg = EncoderConfig(attract_categories=("vehicle",))
    rates2, _ = encode_detections(_frame(_det(0.7, category="vehicle")), SENSORIMOTOR, cfg)
    assert rates2.get("sugar_grn", 0.0) > 0.0
    rates3, _ = encode_detections(_frame(_det(0.7, category="food")), SENSORIMOTOR, cfg)
    assert "sugar_grn" not in rates3


def test_detection_rates_scale_with_conf_and_area_and_clip():
    small, _ = encode_detections(_frame(_det(0.2, w=0.1, h=0.1, conf=0.5)), SENSORIMOTOR)
    big, _ = encode_detections(_frame(_det(0.2, w=0.4, h=0.4, conf=0.9)), SENSORIMOTOR)
    assert 0.0 < small["p9_left"] < big["p9_left"]
    huge = [_det(0.2, w=0.9, h=0.9, conf=1.0) for _ in range(5)]
    clipped, _ = encode_detections(_frame(*huge), SENSORIMOTOR)
    assert clipped["p9_left"] == pytest.approx(200.0)
    cfg = EncoderConfig(max_rate_hz=50.0)
    clipped2, _ = encode_detections(_frame(*huge), SENSORIMOTOR, cfg)
    assert clipped2["p9_left"] == pytest.approx(50.0)


def test_bearing_only_detection_without_bbox_area_gets_no_drive():
    # Spec §6: rate += k * conf * area with a measured bbox area. A detection carrying a
    # bearing but no usable bbox (no frame dims, bbox outside [0, 1]) must not be given a
    # placeholder area — it produces no drive and is reported as skipped.
    det = {
        "id": "d1",
        "cls": "person",
        "conf": 0.9,
        "bearing_deg": 60.0,
        "bbox_xyxy": [10, 10, 50, 50],
    }
    payload = {"detections": [det], "heading_deg": 90.0}  # no frame_w/frame_h
    rates, notes = encode_detections(payload, SENSORIMOTOR)
    assert rates == {}
    assert any("bearing_deg given but no usable bbox area" in n and "skipped" in n for n in notes)
    assert any("no usable detections; no drive" in n for n in notes)
    assert not any("nominal" in n for n in notes)
    # a sibling detection with a measured bbox still drives; the bbox-less one is counted skipped
    bare = {"id": "d2", "cls": "person", "conf": 0.9, "bearing_deg": 60.0}
    rates2, notes2 = encode_detections(
        {"frame_w": 640, "frame_h": 480, "heading_deg": 90.0, "detections": [bare, _det(0.2)]},
        SENSORIMOTOR,
    )
    expected = 400.0 * 0.9 * (0.2 * 0.2)
    assert rates2["p9_left"] == pytest.approx(expected)
    assert any("encoded 1, skipped 1" in n for n in notes2)


def test_no_detections_means_no_drive_and_malformed_fields_noted():
    rates, notes = encode_detections(_frame(), SENSORIMOTOR)
    assert rates == {}
    assert any("empty" in n for n in notes)
    rates, notes = encode_detections({"available": False, "note": "no detector"}, SENSORIMOTOR)
    assert rates == {}
    assert any("unavailable" in n for n in notes)
    bad = _frame({"cls": "x", "conf": "not-a-number", "bbox_xyxy": [1, 2, 3, 4]}, "junk", _det(0.3))
    rates, notes = encode_detections(bad, SENSORIMOTOR)
    assert rates.get("p9_left", 0.0) > 0.0
    assert any("skipped" in n for n in notes)
    # never raises on garbage
    assert encode_detections(None, SENSORIMOTOR)[0] == {}
    assert encode_detections({"detections": "nope"}, SENSORIMOTOR)[0] == {}


def test_telemetry_heading_error_and_distance():
    rates, _ = encode_telemetry(
        {"heading_deg": 0.0, "target_bearing_deg": 45.0, "distance_to_goal_m": 100.0}, SENSORIMOTOR
    )
    # right turn: p9_right gets the turn drive (max-merged with forward), p9_left only forward
    assert rates["p9_right"] >= rates["p9_left"] > 0.0
    rates_l, _ = encode_telemetry(
        {"heading_deg": 10.0, "target_bearing_deg": 300.0, "distance_to_goal_m": 5.0}, SENSORIMOTOR
    )
    assert rates_l["p9_left"] > rates_l["p9_right"] > 0.0
    assert rates_l["p9_left"] <= 100.0
    arrived, notes = encode_telemetry(
        {"heading_deg": 0.0, "target_bearing_deg": 0.0, "distance_to_goal_m": 0.0}, SENSORIMOTOR
    )
    assert arrived == {}
    assert any("arrived" in n for n in notes)
    missing, notes = encode_telemetry({}, SENSORIMOTOR)
    assert missing == {} and notes


def test_earthsim_slice_bearings_and_density():
    payload = {
        "ao": {"center": {"lat": 32.7, "lon": -117.2}, "bbox": [-117.3, 32.6, -117.1, 32.8]},
        "focus": {"lat": 32.71, "lon": -117.2},  # looking north
        "assets": [{"id": "a", "lat": 32.7, "lon": -117.21, "category": "food"}],  # west → left
        "devices": [{"device_id": "d", "location": {"lat": 32.7, "lon": -117.19}}],  # east → right
    }
    rates, notes = encode_earthsim(payload, SENSORIMOTOR)
    assert rates["p9_left"] > 0.0 and rates["p9_right"] > 0.0
    assert rates["sugar_grn"] > 0.0
    empty, notes = encode_earthsim({"ao": {}}, SENSORIMOTOR)
    assert empty == {} and any("no assets" in n for n in notes)


def test_nlm_not_loaded_yields_zero_drive_with_unqualified_note():
    rates, notes = encode_nlm({"model_loaded": False, "confidence": 0.9}, SENSORIMOTOR)
    assert rates == {}
    assert any("UNQUALIFIED" in n for n in notes)
    # stub 0.85 is never drive
    rates, notes = encode_nlm({"model_loaded": True, "confidence": 0.85}, SENSORIMOTOR)
    assert rates == {} and any("UNQUALIFIED" in n for n in notes)
    rates, notes = encode_nlm(
        {"model_loaded": True, "confidence": 0.7, "prediction": "placeholder"}, SENSORIMOTOR
    )
    assert rates == {}
    rates, _ = encode_nlm(
        {"model_loaded": True, "confidence": 0.5, "prediction": "Agaricus"}, SENSORIMOTOR
    )
    assert rates == {"sugar_grn": pytest.approx(100.0)}


def test_raw_rates_rejects_unknown_groups_with_note():
    allowed = known_groups(SENSORIMOTOR)
    assert "p9_left" in allowed and "sugar_downstream" in allowed
    rates, notes = encode_raw_rates(
        {"p9_left": 40, "nope": 10, "p9_right": -1, "sugar_grn": 999}, allowed
    )
    assert rates == {"p9_left": 40.0, "sugar_grn": 200.0}
    assert any("unknown group 'nope'" in n for n in notes)
    assert any("invalid rate" in n for n in notes)
    assert any("clipped" in n for n in notes)


def test_encode_merges_by_max_and_never_raises():
    obs = [
        Observation(kind="detections", payload=_frame(_det(0.2, w=0.3, h=0.3, conf=1.0))),
        Observation(kind="raw_rates", payload={"p9_left": 5.0, "p9_right": 12.0}),
        Observation(kind="nlm", payload={"model_loaded": False}),
        {"kind": "bogus", "payload": {}},
        "garbage",
        {"kind": "telemetry", "payload": None},
    ]
    rates, notes = encode(obs, SENSORIMOTOR)
    det_rates, _ = encode_detections(obs[0].payload, SENSORIMOTOR)
    assert rates["p9_left"] == pytest.approx(max(det_rates["p9_left"], 5.0))
    assert rates["p9_right"] == pytest.approx(12.0)
    assert all(v <= 200.0 for v in rates.values())
    assert any("unknown kind" in n for n in notes)
    assert any("unsupported type" in n for n in notes)
    assert any("UNQUALIFIED" in n for n in notes)
    assert encode([], SENSORIMOTOR) == ({}, [])


# ---------------------------------------------------------------------------
# Decoders
# ---------------------------------------------------------------------------


def test_decoder_turn_sign_and_magnitude():
    dec = LocomotionDecoder(SENSORIMOTOR["readouts"], fwd_ref_hz=50.0, max_turn_deg=30.0)
    act = dec.decode(
        {"p9_shared_downstream": 25.0, "p9_left_downstream": 10.0, "p9_right_downstream": 30.0}, 400
    )
    assert isinstance(act, MotorAction)
    assert act.kind == "locomotion"
    assert act.turn == pytest.approx(0.5, abs=1e-3)
    assert act.heading_delta_deg == pytest.approx(15.0, abs=0.05)
    assert act.forward == pytest.approx(0.5)
    assert act.throttle_pct == pytest.approx(50.0)
    assert act.confidence == pytest.approx(1 - math.exp(-2))
    assert act.evidence["left_hz"] == 10.0 and act.evidence["right_hz"] == 30.0
    assert act.evidence["forward_hz"] == 25.0
    assert act.evidence["formula"] == "locomotion_v1" and "turn=" in act.evidence["formula_text"]
    left = dec.decode(
        {"p9_shared_downstream": 100.0, "p9_left_downstream": 30.0, "p9_right_downstream": 10.0}, 50
    )
    assert left.turn < 0 and left.heading_delta_deg == pytest.approx(-15.0, abs=0.05)
    assert left.forward == 1.0 and left.throttle_pct == 100.0


def test_decoder_silent_brain_confidence_zero_and_kind_none():
    dec = LocomotionDecoder(SENSORIMOTOR)  # whole sensorimotor block accepted too
    act = dec.decode({}, 0)
    assert act.kind == "none"
    assert act.confidence == 0.0
    assert act.turn == 0.0 and act.forward == 0.0
    assert "silent" in act.note
    quiet = dec.decode(
        {"p9_shared_downstream": 1.0, "p9_left_downstream": 1.0, "p9_right_downstream": 1.0}, 10
    )
    assert quiet.kind == "none" and quiet.confidence > 0.0


def test_decoder_single_stray_spike_does_not_saturate_turn():
    """Regression: 0.3 Hz vs 0.0 Hz in the turn readouts (one spike in a 50 ms window
    over ~30 neurons) must not decode as a full-scale turn; the turn is gated to 0 below
    min_turn_hz (default 5 Hz) and kind stays 'none'."""
    dec = LocomotionDecoder(SENSORIMOTOR["readouts"])
    assert dec.min_turn_hz == 5.0
    act = dec.decode({"p9_left_downstream": 0.0, "p9_right_downstream": 0.3}, 1)
    assert act.kind == "none"
    assert act.turn == 0.0
    assert act.heading_delta_deg == 0.0
    assert act.evidence["turn_gated"] is True
    assert act.evidence["min_turn_hz"] == 5.0
    assert "min_turn_hz" in act.note
    # Mirror image: the sign must not be decided by noise either way.
    mirror = dec.decode({"p9_left_downstream": 0.3, "p9_right_downstream": 0.0}, 1)
    assert mirror.kind == "none" and mirror.turn == 0.0
    # Just under the gate is still 0; at/above the gate the ratio applies again.
    under = dec.decode({"p9_left_downstream": 0.0, "p9_right_downstream": 4.9}, 20)
    assert under.turn == 0.0 and under.evidence["turn_gated"] is True
    over = dec.decode({"p9_left_downstream": 0.0, "p9_right_downstream": 5.0}, 20)
    assert over.turn > 0.99 and over.kind == "locomotion"
    assert over.evidence["turn_gated"] is False
    # A genuinely left-dominant drive with a stray right spike is not flipped to the right.
    left_dom = dec.decode({"p9_left_downstream": 20.0, "p9_right_downstream": 0.3}, 300)
    assert left_dom.turn < -0.9 and left_dom.heading_delta_deg < -27.0
    # Gate is configurable (0 disables it and restores the raw ratio).
    raw = LocomotionDecoder(SENSORIMOTOR["readouts"], min_turn_hz=0.0)
    assert raw.decode({"p9_left_downstream": 0.0, "p9_right_downstream": 0.3}, 1).turn > 0.99


def test_classifier_none_without_labels_then_classifies():
    clf = PopulationClassifier()
    assert clf.predict({"p9_left_downstream": 10.0}) is None
    clf.observe({"p9_left_downstream": 10.0}, None)
    assert clf.predict({"p9_left_downstream": 10.0}) is None
    assert clf.state()["ready"] is False and clf.state()["n_unlabelled"] == 1
    clf.observe({"p9_left_downstream": 40.0, "p9_right_downstream": 5.0}, "left_turn")
    clf.observe({"p9_left_downstream": 5.0, "p9_right_downstream": 40.0}, "right_turn")
    clf.observe({"p9_left_downstream": 6.0, "p9_right_downstream": 44.0}, "right_turn")
    out = clf.predict({"p9_left_downstream": 4.0, "p9_right_downstream": 38.0})
    assert out is not None and out["label"] == "right_turn"
    assert out["n_centroids"] == 2 and out["margin_hz"] > 0
    assert (
        clf.predict({"p9_left_downstream": 45.0, "p9_right_downstream": 3.0})["label"]
        == "left_turn"
    )
    assert clf.predict({"unrelated": 1.0}) is None
    state = clf.state()
    assert state["labels"]["right_turn"]["count"] == 2
    assert state["labels"]["right_turn"]["centroid"]["p9_right_downstream"] == pytest.approx(42.0)


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------

CENTER = GeoPoint(lat=32.7157, lon=-117.1611)


def _pt(east: float, north: float) -> GeoPoint:
    return geo_from_enu(east, north, CENTER)


def _ring(e1: float, n1: float, e2: float, n2: float) -> list:
    corners = [(e1, n1), (e2, n1), (e2, n2), (e1, n2), (e1, n1)]
    return [[_pt(e, n).lon, _pt(e, n).lat] for e, n in corners]


def test_enu_round_trip_within_1cm():
    for east, north in [(0.0, 0.0), (123.4, -87.6), (-2400.0, 1999.5), (5.0, 5.0)]:
        gp = geo_from_enu(east, north, CENTER)
        e2, n2 = enu_from_geo(gp.lat, gp.lon, CENTER)
        assert abs(e2 - east) < 0.01 and abs(n2 - north) < 0.01
    # 100 m north is ~0.0009 deg of latitude
    assert geo_from_enu(0.0, 100.0, CENTER).lat - CENTER.lat == pytest.approx(0.000899, abs=1e-5)


def test_grid_blocks_polygon_and_point():
    grid = OccupancyGrid(CENTER, size_m=200.0, cell_m=5.0)
    assert grid.stats()["blocked_cells"] == 0 and grid.stats()["total_cells"] == 1600
    added = grid.add_perimeter(_ring(-30, 10, 30, 30))
    assert added > 0
    inside = _pt(0.0, 20.0)
    outside = _pt(0.0, -20.0)
    assert grid.is_blocked(inside.lat, inside.lon)
    assert not grid.is_blocked(outside.lat, outside.lon)
    p = _pt(-60.0, -60.0)
    n_pt = grid.add_point(p.lat, p.lon, radius_m=8.0)
    assert n_pt >= 1
    assert grid.is_blocked(p.lat, p.lon)
    near = _pt(-54.0, -60.0)
    assert grid.is_blocked(near.lat, near.lon)
    far = _pt(-40.0, -60.0)
    assert not grid.is_blocked(far.lat, far.lon)
    stats = grid.stats()
    assert stats["blocked_cells"] == added + n_pt
    assert 0 < stats["blocked_fraction"] < 1
    # outside the grid is reported blocked; malformed ring adds nothing
    way_out = _pt(500.0, 0.0)
    assert grid.is_blocked(way_out.lat, way_out.lon)
    assert grid.add_perimeter([[0, 0]]) == 0


def test_astar_routes_around_obstacle_and_is_feasible():
    grid = OccupancyGrid(CENTER, size_m=200.0, cell_m=5.0)
    grid.add_perimeter(_ring(-40, -5, 40, 5))  # wall across the middle
    start, goal = _pt(0.0, -60.0), _pt(0.0, 60.0)
    path = plan(grid, start, goal)
    assert isinstance(path, NavPath)
    assert path.feasible is True
    assert 2 <= len(path.waypoints) <= 12
    assert path.waypoints[0].lat == pytest.approx(start.lat) and path.waypoints[
        0
    ].lon == pytest.approx(start.lon)
    assert path.waypoints[-1].lat == pytest.approx(goal.lat) and path.waypoints[
        -1
    ].lon == pytest.approx(goal.lon)
    assert path.geojson["type"] == "LineString" and len(path.geojson["coordinates"]) == len(
        path.waypoints
    )
    assert path.cost is not None and path.cost > 120.0  # longer than the straight 120 m line
    assert path.blocked_cells > 0 and path.total_cells == 1600
    for wp in path.waypoints:
        assert not grid.is_blocked(wp.lat, wp.lon)
    # path must actually leave the blocked band: some waypoint is beyond |east| = 40
    assert any(abs(enu_from_geo(wp.lat, wp.lon, CENTER)[0]) > 40.0 for wp in path.waypoints)


def test_open_grid_path_is_straight_and_short():
    grid = OccupancyGrid(CENTER, size_m=200.0, cell_m=5.0)
    path = plan(grid, _pt(-50.0, -50.0), _pt(50.0, 50.0))
    assert path.feasible and len(path.waypoints) == 2
    assert path.cost == pytest.approx(math.hypot(100.0, 100.0), rel=0.05)


def test_blocked_goal_is_infeasible_with_empty_waypoints():
    grid = OccupancyGrid(CENTER, size_m=200.0, cell_m=5.0)
    grid.add_point(*(lambda g: (g.lat, g.lon))(_pt(20.0, 20.0)), radius_m=6.0)
    path = plan(grid, _pt(-50.0, -50.0), _pt(20.0, 20.0))
    assert path.feasible is False and path.waypoints == [] and path.geojson is None
    assert "goal cell is blocked" in path.note
    out = plan(grid, _pt(-50.0, -50.0), _pt(900.0, 0.0))
    assert out.feasible is False and out.waypoints == [] and "outside grid" in out.note
    # fully enclosed goal is unreachable
    grid2 = OccupancyGrid(CENTER, size_m=200.0, cell_m=5.0)
    grid2.add_perimeter(_ring(-30, -30, 30, -20))
    grid2.add_perimeter(_ring(-30, 20, 30, 30))
    grid2.add_perimeter(_ring(-30, -30, -20, 30))
    grid2.add_perimeter(_ring(20, -30, 30, 30))
    boxed = plan(grid2, _pt(-80.0, -80.0), _pt(0.0, 0.0))
    assert boxed.feasible is False and boxed.waypoints == [] and "unreachable" in boxed.note


def test_turn_bias_changes_side_around_symmetric_obstacle():
    grid = OccupancyGrid(CENTER, size_m=200.0, cell_m=5.0)
    grid.add_perimeter(_ring(-30, -5, 30, 5))  # symmetric wall about east = 0
    start, goal = _pt(0.0, -60.0), _pt(0.0, 60.0)

    def mean_east(path: NavPath) -> float:
        xs = [enu_from_geo(wp.lat, wp.lon, CENTER)[0] for wp in path.waypoints]
        return sum(xs) / len(xs)

    right = plan(grid, start, goal, turn_bias=1.0)
    left = plan(grid, start, goal, turn_bias=-1.0)
    assert right.feasible and left.feasible
    assert mean_east(right) > 5.0  # heading north, positive turn = right = east
    assert mean_east(left) < -5.0
    assert right.turn_bias == 1.0 and left.turn_bias == -1.0
    assert "side=right" in right.note and "side=left" in left.note
    # bias never makes the route go through the wall
    for p in (right, left):
        for wp in p.waypoints:
            assert not grid.is_blocked(wp.lat, wp.lon)


def test_avoidance_vector_pushes_away_from_nearest():
    dets = [
        Detection(
            id="a", cls="rock", conf=0.9, bbox_xyxy=(0, 0, 1, 1), bearing_deg=80.0, range_m=3.0
        ),
        Detection(id="b", cls="tree", conf=0.8, bbox_xyxy=(0, 0, 1, 1), bearing_deg=120.0),
        {"id": "c", "bearing_deg": 270.0, "range_m": 1.0},  # behind: ignored
        {"id": "d"},  # no bearing
    ]
    out = avoidance_vector(dets, heading_deg=90.0)
    assert out["nearest_range_m"] == 3.0
    assert out["turn_hint"] > 0.0  # nearest obstacle 10 deg to the left → push right
    assert out["n_considered"] == 2 and out["n_no_bearing"] == 1 and out["n_unknown_range"] == 1
    empty = avoidance_vector([], heading_deg=0.0)
    assert empty == {
        "turn_hint": 0.0,
        "nearest_range_m": None,
        "nearest_bearing_rel_deg": None,
        "n_considered": 0,
        "n_no_bearing": 0,
        "n_unknown_range": 0,
        "note": "no detections ahead with a bearing",
    }
    far = avoidance_vector([{"bearing_deg": 5.0, "range_m": 50.0}], heading_deg=0.0)
    assert far["turn_hint"] == 0.0 and far["nearest_range_m"] == 50.0


# ---------------------------------------------------------------------------
# Real data (skipped without FLYBRAIN_DATA_DIR)
# ---------------------------------------------------------------------------

_DATA_DIR = os.getenv("FLYBRAIN_DATA_DIR", "").strip()
_HAVE_DATA = bool(_DATA_DIR) and all(
    (Path(_DATA_DIR) / f).exists()
    for f in ("2025_Completeness_783.csv", "2025_Connectivity_783.npz")
)


@pytest.mark.skipif(not _HAVE_DATA, reason="FLYBRAIN_DATA_DIR with FlyWire v783 files not set")
def test_real_atlas_sensorimotor_mapping_drives_encoders_and_decoder():
    """Encoders/decoders keyed by the real atlas mapping; the completeness file confirms ids exist."""
    import csv

    import yaml

    atlas = yaml.safe_load(
        (Path(__file__).resolve().parents[1] / "config" / "flybrain_atlas.yaml").read_text()
    )
    t0 = time.perf_counter()
    with open(Path(_DATA_DIR) / "2025_Completeness_783.csv", newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        ids = {int(row[0]) for row in reader if row and row[0].isdigit()}
    load_s = time.perf_counter() - t0
    assert header and len(ids) > 100_000
    for name in ("sugar_grn", "p9_left", "p9_right"):
        group_ids = atlas["groups"][name]["flywire_ids"]
        assert all(i in ids for i in group_ids), f"{name} has ids missing from completeness"
    sm = atlas["sensorimotor"]
    rates, _ = encode([Observation(kind="detections", payload=_frame(_det(0.2)))], sm)
    assert rates.get("p9_left", 0.0) > 0.0
    dec = LocomotionDecoder(sm["readouts"])
    act = dec.decode(
        {"p9_shared_downstream": 20.0, "p9_left_downstream": 0.0, "p9_right_downstream": 8.0}, 100
    )
    assert act.turn > 0.9
    print(f"\ncompleteness csv parsed in {load_s:.2f}s ({len(ids)} ids)")
