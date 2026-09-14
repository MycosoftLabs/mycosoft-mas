"""Tests for the FlyBrain vision stack (spec §9): slicing, detector honesty,
remote payload mapping, ontology/geometry, and BlueSight provider registration.

No network, no ultralytics/sahi. Transports are injected ``httpx.MockTransport``s.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx
import numpy as np
import pytest

from mycosoft_mas.bluesight.providers import ProviderRegistry
from mycosoft_mas.flybrain.config import FlyBrainSettings
from mycosoft_mas.flybrain.schemas import Detection, DetectionFrame, GeoPoint
from mycosoft_mas.flybrain.vision import detector as detector_mod
from mycosoft_mas.flybrain.vision.bluesight_provider import (
    DETECTOR_STATUS_KEY,
    FlyBrainVisionProvider,
    Yolo26SahiProvider,
    read_frame_ref,
    register_flybrain_providers,
)
from mycosoft_mas.flybrain.vision.detector import (
    DetectorUnavailable,
    FlyBrainDetector,
    RemoteDetector,
    get_detector,
    set_detector_for_tests,
)
from mycosoft_mas.flybrain.vision.ontology import (
    HEIGHT_PRIORS_M,
    TaxonResolver,
    TrackMemory,
    aenrich,
    bearing_from_bbox,
    categorize,
    enrich,
    estimate_range,
    footprint_perimeter,
    locate,
    vertical_fov_deg,
)
from mycosoft_mas.flybrain.vision.slicing import (
    box_iou,
    merge_detections,
    slice_boxes,
    sliced_predict,
)
from mycosoft_mas.schemas.bluesight import BlueSightSensorPacket

REPO_ROOT = Path(__file__).resolve().parents[1]


def _settings(tmp_path: Path, **overrides) -> FlyBrainSettings:
    base = dict(
        data_dir=tmp_path / "data",
        atlas_path=REPO_ROOT / "config" / "flybrain_atlas.yaml",
        record_dir=tmp_path / "rec",
        remote_detector_url=None,
        mindex_api_url="http://mindex.invalid:8000",
        camera_hfov_deg=90.0,
    )
    base.update(overrides)
    return FlyBrainSettings(**base)


# The verified live Jetson /detect shape (website camera/[feedId]/detections/route.ts).
JETSON_PAYLOAD = {
    "ok": True,
    "ts": "2026-08-02T05:00:19.878376+00:00",
    "engine": "ultralytics:yolo11n.pt",
    "deepstream": False,
    "device": "cpu",
    "note": "one-shot snapshot",
    "detections": [
        {"source": "quad360", "class": "couch", "confidence": 0.376, "bbox": [10, 20, 110, 220]},
        {
            "source": "pano",
            "class": "person",
            "confidence": 0.81,
            "bbox": [3000, 100, 3100, 400],
            "trackId": 7,
        },
        {"class": "boat", "confidence": 0.5, "bbox": [50, 60, 40, 30]},
        {"source": "bev", "class": "car", "confidence": 0.9, "bbox": [1, 2, 3]},
        {"source": "bev", "confidence": 0.9, "bbox": [1, 2, 3, 4]},
    ],
    "frames": {
        "quad360": {"frameW": 1920, "frameH": 1080},
        "pano": {"frameW": 3840, "frameH": 540},
        "bev": {"frameW": 800, "frameH": 800},
    },
}


# ---------------------------------------------------------------------------
# slicing.py
# ---------------------------------------------------------------------------


def test_slice_boxes_cover_frame_with_overlap():
    w, h, s, ov = 1000, 700, 640, 0.2
    tiles = slice_boxes(w, h, s, ov)
    assert tiles, "no tiles"
    cover = np.zeros((h, w), dtype=np.int32)
    for x1, y1, x2, y2 in tiles:
        assert 0 <= x1 < x2 <= w and 0 <= y1 < y2 <= h
        assert (x2 - x1) == s and (y2 - y1) == s
        cover[y1:y2, x1:x2] += 1
    assert cover.min() >= 1, "frame not fully covered"
    xs = sorted({(t[0], t[2]) for t in tiles})
    for (a1, a2), (b1, _) in zip(xs, xs[1:]):
        assert a2 - b1 >= int(ov * s), "horizontal overlap smaller than requested"
    assert len(tiles) == 4


def test_slice_boxes_small_frame_is_single_tile():
    assert slice_boxes(300, 200, 640, 0.2) == [(0, 0, 300, 200)]
    assert slice_boxes(0, 200, 640, 0.2) == []


def test_merge_detections_is_class_aware():
    a = (10, 10, 110, 110, 0.9, "dog")
    b = (15, 12, 112, 108, 0.7, "dog")  # same object, lower conf
    c = (12, 11, 110, 111, 0.8, "cat")  # different class, same place
    d = (500, 500, 540, 540, 0.6, "dog")  # far away
    assert box_iou(a[:4], b[:4]) > 0.5
    merged = merge_detections([a, b, c, d], iou_threshold=0.5)
    assert len(merged) == 3
    assert [m[5] for m in merged] == ["dog", "cat", "dog"]
    assert merged[0][4] == 0.9
    assert merge_detections([]) == []


def test_sliced_predict_returns_full_frame_coordinates():
    h, w = 700, 1000
    image = np.zeros((h, w, 3), dtype=np.uint8)
    image[500:510, 700:710] = 255  # one bright 10x10 square

    calls = []

    def fake_predict(tile):
        calls.append(tile.shape)
        mask = tile[..., 0] > 0
        if not mask.any():
            return []
        ys, xs = np.nonzero(mask)
        return [
            (
                float(xs.min()),
                float(ys.min()),
                float(xs.max() + 1),
                float(ys.max() + 1),
                0.9,
                "blob",
            )
        ]

    result = sliced_predict(fake_predict, image, 640, 0.2, 0.25)
    assert result.slices == 4
    assert result.full_frame is True
    assert len(calls) == 5  # 4 tiles + 1 full-frame pass
    assert len(result.detections) == 1, "duplicate tile hits must merge"
    x1, y1, x2, y2, conf, cls = result.detections[0]
    assert (x1, y1, x2, y2) == (700.0, 500.0, 710.0, 510.0)
    assert cls == "blob" and conf == 0.9


def test_sliced_predict_applies_conf_threshold():
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    result = sliced_predict(lambda t: [(0, 0, 10, 10, 0.1, "x")], image, 640, 0.2, 0.5)
    assert result.detections == []
    assert result.slices == 0  # frame smaller than a slice → only the full pass


# ---------------------------------------------------------------------------
# detector.py
# ---------------------------------------------------------------------------


def test_detector_with_no_backend_is_unavailable(tmp_path):
    det = FlyBrainDetector(settings=_settings(tmp_path), backend="none")
    health = det.health()
    assert det.available is False
    assert health.available is False
    assert health.engine is None
    assert "backend" in health.reason
    with pytest.raises(DetectorUnavailable):
        det.detect(b"not-an-image")


def test_detector_ultralytics_absent_reports_reason(tmp_path):
    pytest.importorskip("numpy")
    try:
        import ultralytics  # noqa: F401

        pytest.skip("ultralytics installed; absence path not testable here")
    except ImportError:
        pass
    det = FlyBrainDetector(settings=_settings(tmp_path), backend="ultralytics")
    health = det.health()
    assert health.available is False
    assert "ultralytics" in health.reason
    with pytest.raises(DetectorUnavailable):
        det.detect(np.zeros((10, 10, 3), dtype=np.uint8))
    # auto with no remote URL and no ultralytics → none, with both reasons
    auto = FlyBrainDetector(settings=_settings(tmp_path), backend="auto")
    assert auto.backend == "none"
    assert "ultralytics" in auto.health().reason and "remote" in auto.health().reason


def test_detector_rejects_unknown_backend(tmp_path):
    with pytest.raises(ValueError):
        FlyBrainDetector(settings=_settings(tmp_path), backend="magic")


def test_get_detector_cache_and_test_override(tmp_path):
    set_detector_for_tests(None)
    fake = FlyBrainDetector(settings=_settings(tmp_path), backend="none")
    set_detector_for_tests(fake)
    try:
        assert get_detector() is fake
        assert get_detector() is fake
    finally:
        set_detector_for_tests(None)
    assert detector_mod._DETECTOR is None


def _jetson_transport(payload=None, status=200, accept_post=True):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            if not accept_post:
                return httpx.Response(405)
            body = dict(payload or JETSON_PAYLOAD)
            body["frames"] = {"upload": {"frameW": 640, "frameH": 480}}
            body["detections"] = [
                {"source": "upload", "class": "dog", "confidence": 0.7, "bbox": [0, 0, 64, 48]}
            ]
            return httpx.Response(200, json=body)
        return httpx.Response(status, json=payload if payload is not None else JETSON_PAYLOAD)

    return httpx.MockTransport(handler)


def test_remote_snapshot_maps_jetson_payload():
    remote = RemoteDetector("http://jetson.invalid:8792/detect", transport=_jetson_transport())
    frame = remote.snapshot()
    assert isinstance(frame, DetectionFrame)
    assert frame.available is True
    assert frame.engine == "remote:ultralytics:yolo11n.pt"
    assert frame.model == "ultralytics:yolo11n.pt"
    assert frame.device == "cpu"
    assert frame.note == "one-shot snapshot"
    expected_ms = datetime(2026, 8, 2, 5, 0, 19, 878376, tzinfo=timezone.utc).timestamp() * 1000
    assert frame.t_ms == pytest.approx(expected_ms, abs=1.0)
    # default source (quad360) supplies the frame-level dims
    assert (frame.frame_w, frame.frame_h) == (1920, 1080)
    # 3 valid boxes: couch(quad360), person(pano), boat(untagged→quad360); 2 malformed dropped
    assert [d.cls for d in frame.detections] == ["couch", "person", "boat"]
    couch, person, boat = frame.detections
    assert couch.bbox_xyxy == (10.0, 20.0, 110.0, 220.0)
    assert couch.source == "quad360"
    assert couch.attributes["frame_w"] == 1920 and couch.attributes["frame_h"] == 1080
    assert couch.bbox_norm == pytest.approx((10 / 1920, 20 / 1080, 110 / 1920, 220 / 1080))
    assert person.source == "pano" and person.track_id == "7"
    assert person.attributes["frame_w"] == 3840 and person.attributes["frame_h"] == 540
    assert person.bbox_norm[0] == pytest.approx(3000 / 3840)
    assert boat.source == "quad360"
    assert boat.bbox_xyxy == (40.0, 30.0, 50.0, 60.0)  # corners normalised
    assert boat.conf == 0.5
    # per-source filter
    pano_only = remote.snapshot(source="pano")
    assert [d.cls for d in pano_only.detections] == ["person"]
    assert (pano_only.frame_w, pano_only.frame_h) == (3840, 540)
    assert pano_only.source == "pano"


def test_remote_snapshot_failures_are_unavailable():
    def boom(request):
        raise httpx.ConnectError("refused")

    remote = RemoteDetector(
        "http://jetson.invalid:8792/detect", transport=httpx.MockTransport(boom)
    )
    with pytest.raises(DetectorUnavailable):
        remote.snapshot()
    ok, reason = remote.probe()
    assert ok is False and "unreachable" in reason
    bad = RemoteDetector(
        "http://jetson.invalid:8792/detect", transport=_jetson_transport(status=503)
    )
    with pytest.raises(DetectorUnavailable):
        bad.snapshot()
    with pytest.raises(DetectorUnavailable):
        RemoteDetector("").snapshot()


def test_remote_post_image_and_refusal():
    remote = RemoteDetector("http://jetson.invalid:8792/detect", transport=_jetson_transport())
    frame = remote.post_image(b"\x89PNG fake", source="camera")
    assert frame.source == "camera"
    assert [d.cls for d in frame.detections] == ["dog"]
    assert (frame.frame_w, frame.frame_h) == (640, 480)
    refusing = RemoteDetector(
        "http://jetson.invalid:8792/detect", transport=_jetson_transport(accept_post=False)
    )
    with pytest.raises(DetectorUnavailable, match="does not accept image uploads"):
        refusing.post_image(b"\x89PNG fake")


def test_detector_remote_backend_uses_injected_transport(tmp_path):
    settings = _settings(tmp_path, remote_detector_url="http://jetson.invalid:8792/detect")
    det = FlyBrainDetector(settings=settings, backend="remote")
    det._remote = RemoteDetector(settings.remote_detector_url, transport=_jetson_transport())
    assert det.backend == "remote"
    health = det.health()
    assert health.available is True and health.engine == "remote"
    assert health.remote_url == settings.remote_detector_url
    frame = det.detect(b"bytes", pose={"lat": 32.7, "lon": -117.2, "heading_deg": 90.0})
    assert frame.detections[0].cls == "dog"
    assert frame.detections[0].category == "animal"
    assert frame.detections[0].bearing_deg is not None
    snap = det.snapshot(source="pano")
    assert [d.cls for d in snap.detections] == ["person"]


def test_adetect_runs_in_thread(tmp_path):
    det = FlyBrainDetector(settings=_settings(tmp_path), backend="none")

    async def go():
        with pytest.raises(DetectorUnavailable):
            await det.adetect(b"x")

    asyncio.run(go())


class _FakeYoloModel:
    """Stand-in for a loaded ``ultralytics.YOLO`` (tests only; never produces boxes)."""

    names = {0: "person", 1: "mushroom"}
    device = "cpu"


def _ultralytics_stub_detector(tmp_path, weights, loader):
    """Detector whose ultralytics probe is forced to succeed without the package."""
    det = FlyBrainDetector(
        settings=_settings(tmp_path, yolo_weights=weights), backend="ultralytics"
    )
    det._yolo_cls = loader  # what ``_probe_ultralytics`` would have imported
    return det


def _has_verified_field() -> bool:
    from mycosoft_mas.flybrain.schemas import VisionHealth

    return "verified" in VisionHealth.model_fields


def test_health_is_unavailable_until_weights_are_verified(tmp_path):
    """Regression: ultralytics importable + no weights on disk must not read available."""
    missing = str(tmp_path / "yolo26n.pt")
    det = _ultralytics_stub_detector(tmp_path, missing, lambda w: _FakeYoloModel())
    assert det.backend == "ultralytics"
    health = det.health()
    assert health.available is False
    assert health.engine == "ultralytics"
    assert "not loaded/verified" in health.reason
    assert det.available is False
    if _has_verified_field():
        assert health.verified is False


def test_health_weights_on_disk_is_available_but_not_verified(tmp_path):
    weights = tmp_path / "custom.pt"
    weights.write_bytes(b"\x00" * 8)
    det = _ultralytics_stub_detector(tmp_path, str(weights), lambda w: _FakeYoloModel())
    health = det.health()
    assert health.available is True
    assert "not yet verified" in health.reason
    if _has_verified_field():
        assert health.verified is False


def test_health_probe_model_reports_real_load_failure(tmp_path):
    def broken_loader(weights):
        raise OSError("no internet: cannot download " + weights)

    det = _ultralytics_stub_detector(tmp_path, "yolo26n.pt", broken_loader)
    health = det.health(probe_model=True)
    assert health.available is False
    assert "could not be loaded" in health.reason and "no internet" in health.reason
    if _has_verified_field():
        assert health.verified is False
    # the failure sticks: a later plain health() keeps the same honest reason
    assert det.health().available is False and "could not be loaded" in det.health().reason
    with pytest.raises(DetectorUnavailable):
        det.detect(np.zeros((4, 4, 3), dtype=np.uint8))


def test_health_probe_model_success_is_verified(tmp_path):
    det = _ultralytics_stub_detector(tmp_path, "yolo26n.pt", lambda w: _FakeYoloModel())
    assert det.health().available is False  # weights not on disk, not loaded yet
    health = det.health(probe_model=True)
    assert health.available is True and health.reason == ""
    assert health.device == "cpu"
    assert list(det.class_names) == ["person", "mushroom"]
    if _has_verified_field():
        assert health.verified is True


def _mindex_transport(seen=None):
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request.url.params["scientific_name"])
        if request.url.params["scientific_name"] == "dog":
            return httpx.Response(
                200, json=[{"taxon_id": "canis", "scientific_name": "Canis familiaris"}]
            )
        return httpx.Response(200, json={"items": []})

    return httpx.MockTransport(handler)


def test_detector_owns_a_taxon_resolver_bound_to_mindex(tmp_path):
    settings = _settings(tmp_path)
    det = FlyBrainDetector(settings=settings, backend="none")
    assert isinstance(det.resolver, TaxonResolver)
    assert det.resolver.base_url == settings.mindex_api_url.rstrip("/")


def test_adetect_performs_mindex_taxon_lookup(tmp_path):
    """Regression: the async path must actually attempt the MINDEX lookup."""
    settings = _settings(tmp_path, remote_detector_url="http://jetson.invalid:8792/detect")
    det = FlyBrainDetector(settings=settings, backend="remote")
    det._remote = RemoteDetector(settings.remote_detector_url, transport=_jetson_transport())
    seen = []
    det._resolver = TaxonResolver(settings.mindex_api_url, transport=_mindex_transport(seen))

    # sync path, cold cache: geometry only, no network, taxon stays None
    cold = det.detect(b"bytes")
    assert cold.detections[0].cls == "dog" and cold.detections[0].taxon is None
    assert seen == []

    frame = asyncio.run(det.adetect(b"bytes", pose={"lat": 32.7, "lon": -117.2, "heading_deg": 0}))
    dog = frame.detections[0]
    assert dog.cls == "dog" and dog.category == "animal"
    assert dog.taxon is not None and dog.taxon.matched and dog.taxon.taxon_id == "canis"
    assert dog.bearing_deg is not None  # geometry enrichment still applied
    assert seen == ["dog"]

    # the sync path now serves the cached taxon without another lookup
    warm = det.detect(b"bytes")
    assert warm.detections[0].taxon is not None and warm.detections[0].taxon.taxon_id == "canis"
    assert seen == ["dog"]


def test_asnapshot_performs_mindex_taxon_lookup(tmp_path):
    payload = dict(JETSON_PAYLOAD)
    payload["detections"] = [
        {"source": "quad360", "class": "dog", "confidence": 0.8, "bbox": [0, 0, 50, 50]},
        {"source": "quad360", "class": "car", "confidence": 0.9, "bbox": [0, 0, 50, 50]},
    ]
    settings = _settings(tmp_path, remote_detector_url="http://jetson.invalid:8792/detect")
    det = FlyBrainDetector(settings=settings, backend="remote")
    det._remote = RemoteDetector(settings.remote_detector_url, transport=_jetson_transport(payload))
    seen = []
    det._resolver = TaxonResolver(settings.mindex_api_url, transport=_mindex_transport(seen))
    frame = asyncio.run(det.asnapshot())
    dog, car = frame.detections
    assert dog.taxon is not None and dog.taxon.matched
    assert car.taxon is None  # vehicles are never looked up
    assert seen == ["dog"]


def test_adetect_unreachable_mindex_is_unmatched_not_fabricated(tmp_path):
    def boom(request):
        raise httpx.ConnectError("no route to MINDEX")

    settings = _settings(tmp_path, remote_detector_url="http://jetson.invalid:8792/detect")
    det = FlyBrainDetector(settings=settings, backend="remote")
    det._remote = RemoteDetector(settings.remote_detector_url, transport=_jetson_transport())
    det._resolver = TaxonResolver(settings.mindex_api_url, transport=httpx.MockTransport(boom))
    frame = asyncio.run(det.adetect(b"bytes"))
    dog = frame.detections[0]
    assert dog.taxon is not None and dog.taxon.matched is False
    assert dog.taxon.taxon_id is None and "unreachable" in dog.taxon.note


# ---------------------------------------------------------------------------
# ontology.py
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cls,expected",
    [
        ("person", "person"),
        ("boat", "vessel"),
        ("dog", "animal"),
        ("mushroom", "fungus"),
        ("broccoli", "food"),
        ("airplane", "aircraft"),
        ("truck", "vehicle"),
        ("potted plant", "plant"),
        ("Potted_Plant", "plant"),
        ("stop sign", "structure"),
        ("laptop", "object"),
        ("Fly Agaric", "fungus"),
        ("oyster mushrooms", "fungus"),
        ("zorblax", "object"),
        ("", "object"),
        (None, "object"),
    ],
)
def test_categorize(cls, expected):
    assert categorize(cls) == expected


def test_bearing_at_bbox_centre_equals_heading():
    assert bearing_from_bbox((300, 0, 340, 10), 640, 45.0, 90.0) == pytest.approx(45.0)
    assert bearing_from_bbox((0, 0, 10, 10), 640, 0.0, 90.0) == pytest.approx(
        360.0 - 45.0 + 45.0 * 10 / 640
    )
    assert bearing_from_bbox((630, 0, 640, 10), 640, 350.0, 90.0) == pytest.approx(
        (350.0 + 45.0 - 45.0 * 10 / 640) % 360
    )
    assert bearing_from_bbox((0, 0, 10, 10), None, 0.0, 90.0) is None
    assert bearing_from_bbox((0, 0, 10, 10), 640, None, 90.0) is None


def test_estimate_range_none_for_unknown_category():
    assert estimate_range((0, 0, 10, 100), 480, "object", 60.0) == (None, "estimate")
    assert estimate_range((0, 0, 10, 100), 480, "vessel", 60.0) == (None, "estimate")
    assert estimate_range((0, 0, 10, 100), 480, "person", None)[0] is None
    assert estimate_range((0, 0, 10, 0), 480, "person", 60.0)[0] is None
    rng, src = estimate_range((0, 0, 10, 240), 480, "person", 60.0)
    assert src == "estimate" and rng is not None
    # 240/480 of a 60° VFOV = 30° subtended by 1.7 m → 1.7 / (2 tan 15°) ≈ 3.17 m
    assert rng == pytest.approx(HEIGHT_PRIORS_M["person"] / (2 * np.tan(np.radians(15))), rel=1e-6)
    # class prior overrides category prior
    dog, _ = estimate_range((0, 0, 10, 240), 480, "animal", 60.0, cls="dog")
    assert dog == pytest.approx(HEIGHT_PRIORS_M["dog"] / (2 * np.tan(np.radians(15))), rel=1e-6)
    assert vertical_fov_deg(90.0, 1920, 1080) == pytest.approx(58.7, abs=0.2)


def test_locate_and_footprint():
    origin = GeoPoint(lat=32.7, lon=-117.2)
    north = locate(origin.lat, origin.lon, 0.0, 1000.0)
    assert north.lat > origin.lat and north.lon == pytest.approx(origin.lon)
    east = locate(origin.lat, origin.lon, 90.0, 1000.0)
    assert east.lon > origin.lon and east.lat == pytest.approx(origin.lat)
    ring = footprint_perimeter(east, 90.0, 4.0, 2.0)
    assert len(ring) == 5
    assert ring[0] == ring[-1]
    assert all(len(p) == 2 for p in ring)
    lons = [p[0] for p in ring]
    lats = [p[1] for p in ring]
    assert min(lons) < east.lon < max(lons) and min(lats) < east.lat < max(lats)


def test_track_memory_builds_pathway():
    mem = TrackMemory(max_points=3)
    p1 = mem.update("t1", GeoPoint(lat=1.0, lon=2.0), 0.0)
    assert p1 == [[2.0, 1.0]]
    mem.update("t1", GeoPoint(lat=1.1, lon=2.1), 100.0)
    mem.update("t1", GeoPoint(lat=1.2, lon=2.2), 200.0)
    p4 = mem.update("t1", GeoPoint(lat=1.3, lon=2.3), 300.0)
    assert p4 == [[2.1, 1.1], [2.2, 1.2], [2.3, 1.3]]  # bounded by max_points
    assert mem.pathway("missing") == []
    assert mem.last_seen_ms("t1") == 300.0
    assert mem.prune(now_ms=10_000.0, max_age_ms=1_000.0) == 1
    assert len(mem) == 0


def test_taxon_resolver_connection_failure_is_unmatched():
    def boom(request):
        raise httpx.ConnectError("no route to MINDEX")

    resolver = TaxonResolver(
        "http://mindex.invalid:8000", timeout_s=0.5, transport=httpx.MockTransport(boom)
    )
    taxon = asyncio.run(resolver.resolve("mushroom"))
    assert taxon is not None
    assert taxon.matched is False
    assert "unreachable" in taxon.note
    assert taxon.taxon_id is None
    assert resolver.resolve_cached("mushroom") is taxon
    assert resolver.resolve_cached("never-looked-up") is None
    assert asyncio.run(resolver.resolve("")) is None


def test_taxon_resolver_parses_match_and_caches():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        assert request.url.path == "/api/mindex/taxa"
        assert request.url.params["scientific_name"] == "amanita"
        assert request.url.params["limit"] == "1"
        return httpx.Response(
            200,
            json={"items": [{"id": "tx-1", "scientific_name": "Amanita", "rank": "genus"}]},
        )

    resolver = TaxonResolver("http://mindex.invalid:8000/", transport=httpx.MockTransport(handler))
    taxon = asyncio.run(resolver.resolve("Amanita"))
    assert taxon.matched is True and taxon.taxon_id == "tx-1" and taxon.rank == "genus"
    assert taxon.scientific_name == "Amanita"
    again = asyncio.run(resolver.resolve("amanita"))
    assert again is taxon and len(seen) == 1  # LRU hit

    empty = TaxonResolver(
        "http://mindex.invalid:8000",
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"items": []})),
    )
    miss = asyncio.run(empty.resolve("dog"))
    assert miss.matched is False and "no MINDEX taxon" in miss.note


def _frame(**overrides) -> DetectionFrame:
    base = dict(
        frame_w=640,
        frame_h=480,
        engine="test",
        detections=[
            Detection(
                id="d0", cls="person", conf=0.9, bbox_xyxy=(300, 100, 340, 340), track_id="p1"
            ),
            Detection(id="d1", cls="boat", conf=0.6, bbox_xyxy=(0, 0, 100, 100)),
        ],
    )
    base.update(overrides)
    return DetectionFrame(**base)


def test_enrich_fills_geometry_only_when_inputs_exist(tmp_path):
    settings = _settings(tmp_path)
    no_pose = enrich(_frame(), None, settings)
    person, boat = no_pose.detections
    assert person.category == "person" and boat.category == "vessel"
    assert person.bbox_norm is not None
    assert person.bearing_deg is None and person.location is None and person.perimeter is None
    assert (
        person.range_m is not None and person.range_source == "estimate"
    )  # needs only frame + prior
    assert boat.range_m is None and boat.range_source is None
    assert "no heading" in no_pose.note

    mem = TrackMemory()
    posed = enrich(
        _frame(t_ms=1.0),
        {"lat": 32.7, "lon": -117.2, "heading_deg": 90.0},
        settings,
        track_memory=mem,
    )
    person, boat = posed.detections
    assert person.bearing_deg == pytest.approx(90.0)  # bbox centred → heading
    assert person.location is not None and person.location.lon > -117.2
    assert person.perimeter is not None and len(person.perimeter) == 5
    assert person.pathway == [[person.location.lon, person.location.lat]]
    assert boat.bearing_deg == pytest.approx(90.0 - 45.0 + 90.0 * 50 / 640)
    assert boat.location is None and boat.perimeter is None and boat.pathway is None
    assert posed.note == ""

    # a measured range on the input is kept, not overwritten by the estimate
    measured = enrich(
        _frame(
            detections=[
                Detection(id="m", cls="person", conf=0.5, bbox_xyxy=(0, 0, 10, 10), range_m=12.5)
            ]
        ),
        None,
        settings,
    )
    assert (
        measured.detections[0].range_m == 12.5 and measured.detections[0].range_source == "measured"
    )


def test_aenrich_attaches_taxa_for_biological_classes(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        name = request.url.params["scientific_name"]
        if name == "dog":
            return httpx.Response(
                200, json=[{"taxon_id": "canis", "scientific_name": "Canis familiaris"}]
            )
        return httpx.Response(200, json={"items": []})

    resolver = TaxonResolver("http://mindex.invalid:8000", transport=httpx.MockTransport(handler))
    frame = DetectionFrame(
        frame_w=100,
        frame_h=100,
        detections=[
            Detection(id="a", cls="dog", conf=0.9, bbox_xyxy=(0, 0, 10, 10)),
            Detection(id="b", cls="car", conf=0.9, bbox_xyxy=(0, 0, 10, 10)),
        ],
    )
    out = asyncio.run(aenrich(frame, None, _settings(tmp_path), resolver=resolver))
    dog, car = out.detections
    assert dog.taxon is not None and dog.taxon.matched and dog.taxon.taxon_id == "canis"
    assert car.taxon is None  # vehicles are never looked up


# ---------------------------------------------------------------------------
# bluesight_provider.py
# ---------------------------------------------------------------------------


def _packet(frame_ref, **payload) -> BlueSightSensorPacket:
    return BlueSightSensorPacket(
        profile="device_scene",
        run_id="run-1",
        frame_id="frame-1",
        source="camera",
        frame_ref=frame_ref,
        payload=payload,
    )


def test_register_flybrain_providers_adds_both_names(tmp_path):
    registry = ProviderRegistry()
    det = FlyBrainDetector(settings=_settings(tmp_path), backend="none")
    names = register_flybrain_providers(registry, detector=det)
    assert names == ["yolo26_sahi", "flybrain_vision"]
    assert isinstance(registry.provider("yolo26_sahi"), Yolo26SahiProvider)
    assert isinstance(registry.provider("flybrain_vision"), FlyBrainVisionProvider)
    assert registry.provider("yolo26_sahi").name == "yolo26_sahi"
    assert registry.provider("flybrain_vision").name == "flybrain_vision"
    assert registry.provider("truth_bootstrap").name == "truth_bootstrap"  # untouched
    with pytest.raises(TypeError):
        register_flybrain_providers(object())  # type: ignore[arg-type]


def test_provider_unreadable_frame_ref_returns_empty(tmp_path):
    det = FlyBrainDetector(settings=_settings(tmp_path), backend="none")
    for provider in (Yolo26SahiProvider(detector=det), FlyBrainVisionProvider(detector=det)):
        assert provider.detect(_packet(None)) == []
        assert provider.detect(_packet("")) == []
        assert provider.detect(_packet(str(tmp_path / "missing.jpg"))) == []
        assert provider.detect(_packet("not-a-url-or-path")) == []
    assert read_frame_ref(None) is None
    assert read_frame_ref(str(tmp_path / "nope.png")) is None


def test_provider_readable_frame_but_no_detector_returns_empty(tmp_path):
    path = tmp_path / "frame.bin"
    path.write_bytes(b"\x00" * 64)
    det = FlyBrainDetector(settings=_settings(tmp_path), backend="none")
    assert read_frame_ref(str(path)) == b"\x00" * 64
    assert Yolo26SahiProvider(detector=det).detect(_packet(str(path))) == []
    assert FlyBrainVisionProvider(detector=det).detect(_packet(str(path))) == []


def test_provider_unavailable_detector_is_not_a_healthy_empty_frame(tmp_path, caplog):
    """Regression: an unavailable detector must not be persisted as "ran, saw nothing"."""
    path = tmp_path / "frame.bin"
    path.write_bytes(b"\x00" * 64)
    det = FlyBrainDetector(settings=_settings(tmp_path), backend="none")
    provider = Yolo26SahiProvider(detector=det)
    packet = _packet(str(path))
    assert provider.healthy  # nothing has run yet, so nothing has failed yet
    with caplog.at_level(logging.WARNING, logger="mycosoft_mas.flybrain.vision.bluesight_provider"):
        assert provider.detect(packet) == []
    assert not provider.healthy
    assert provider.last_error is not None and provider.last_error.startswith(
        "detector_unavailable:"
    )
    status = packet.metadata[DETECTOR_STATUS_KEY]
    assert status["provider"] == "yolo26_sahi"
    assert status["ran"] is False and status["healthy"] is False
    assert status["status"] == "detector_unavailable"
    assert status["reason"]
    assert any(
        r.levelno == logging.WARNING and "detector did not run" in r.getMessage()
        for r in caplog.records
    )

    # The same packet passed through BlueSightService.observe() carries the stamp into the
    # persisted observation's metadata (observe() copies normalized.metadata verbatim).
    unreadable = _packet(str(tmp_path / "missing.jpg"))
    assert FlyBrainVisionProvider(detector=det).detect(unreadable) == []
    assert unreadable.metadata[DETECTOR_STATUS_KEY]["status"] == "frame_unreadable"


def test_provider_status_stamp_says_ran_when_detector_ran(tmp_path):
    path = tmp_path / "frame.jpg"
    path.write_bytes(b"\xff\xd8 fake jpeg")
    settings = _settings(tmp_path, remote_detector_url="http://jetson.invalid:8792/detect")
    det = FlyBrainDetector(settings=settings, backend="remote")
    det._remote = RemoteDetector(settings.remote_detector_url, transport=_jetson_transport())
    provider = Yolo26SahiProvider(detector=det)
    packet = _packet(str(path))
    assert len(provider.detect(packet)) == 1
    assert provider.healthy and provider.last_error is None
    status = packet.metadata[DETECTOR_STATUS_KEY]
    assert status["ran"] is True and status["healthy"] is True and status["status"] == "ok"
    # A later failure on the same provider flips the flag and the stamp.
    assert provider.detect(_packet(None)) == []
    assert not provider.healthy


def test_provider_maps_remote_detections(tmp_path):
    path = tmp_path / "frame.jpg"
    path.write_bytes(b"\xff\xd8 fake jpeg")
    settings = _settings(tmp_path, remote_detector_url="http://jetson.invalid:8792/detect")
    det = FlyBrainDetector(settings=settings, backend="remote")
    det._remote = RemoteDetector(settings.remote_detector_url, transport=_jetson_transport())
    out = FlyBrainVisionProvider(detector=det).detect(
        _packet(str(path), pose={"lat": 32.7, "lon": -117.2, "heading_deg": 0.0})
    )
    assert len(out) == 1
    d = out[0]
    assert d.detection_id == "frame-1:upload:0"
    assert d.class_name == "dog" and d.confidence == 0.7
    assert d.bbox_xyxy == (0.0, 0.0, 64.0, 48.0)
    assert d.centroid_xy == (32.0, 24.0)
    assert d.attributes["category"] == "animal"
    assert d.attributes["frame_w"] == 640 and d.attributes["frame_h"] == 480
    assert d.attributes["bearing_deg"] is not None
    assert d.attributes["location"] is not None
    assert d.linked_entity is None  # no taxon lookup happened (sync path, cold cache)
    raw = Yolo26SahiProvider(detector=det).detect(_packet(str(path)))
    assert len(raw) == 1 and "bearing_deg" not in raw[0].attributes


# ---------------------------------------------------------------------------
# Real data (vision needs none; kept for parity with the other flybrain suites)
# ---------------------------------------------------------------------------


def _real_data_dir():
    raw = os.getenv("FLYBRAIN_DATA_DIR", "").strip()
    if not raw:
        return None
    p = Path(raw)
    if (p / "2025_Completeness_783.csv").is_file() and (p / "2025_Connectivity_783.npz").is_file():
        return p
    return None


@pytest.mark.skipif(
    _real_data_dir() is None, reason="FLYBRAIN_DATA_DIR with the v783 files not set"
)
def test_vision_stack_is_independent_of_connectome():
    """The vision stack must import and report honestly with or without the connectome."""
    det = FlyBrainDetector(backend="none")
    assert det.available is False
    assert json.loads(det.health().model_dump_json())["available"] is False
