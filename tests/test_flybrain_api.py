"""Integration tests for ``/api/flybrain/*`` and ``FlyBrainAgent`` (spec §10, §11).

A minimal FastAPI app mounts only ``flybrain_api.router`` (``myca_main`` is
never imported). Sessions run on the same explicit in-memory synthetic
connectome fixture as ``tests/test_flybrain_runtime.py`` — a test fixture,
not production data — pinned through ``connectome.set_cached_connectome``
with a temporary atlas whose ids exist in that fixture. No network. The
real-data test is skipped unless ``FLYBRAIN_DATA_DIR`` holds the FlyWire files.
"""

from __future__ import annotations

import asyncio
import base64
import io
import os
import time
from pathlib import Path

import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mycosoft_mas.agents.flybrain_agent import CAPABILITIES, FlyBrainAgent
from mycosoft_mas.core.routers import flybrain_api
from mycosoft_mas.flybrain.connectome import (
    Connectome,
    reset_connectome_cache,
    set_cached_connectome,
)
from mycosoft_mas.flybrain.runtime import FlyBrainRuntime, reset_runtime_for_tests
from mycosoft_mas.flybrain.schemas import Detection, DetectionFrame, Taxon
from mycosoft_mas.flybrain.vision.detector import set_detector_for_tests

# ---------------------------------------------------------------------------
# Synthetic fixture (identical wiring to tests/test_flybrain_runtime.py)
#   0 (p9_left)  -> 1, 0 -> 4 ; 2 (p9_right) -> 3, 2 -> 4 (shared) ; 5, 6 (sugar) -> 7
# ---------------------------------------------------------------------------

N_SYNTH = 60
SYNTH_IDS = [10_000 + i for i in range(N_SYNTH)]
SYNTH_PRE = [0, 0, 2, 2, 5, 6, 1]
SYNTH_POST = [1, 4, 3, 4, 7, 7, 8]
SYNTH_W = [1000.0, 1000.0, 1000.0, 1000.0, 1000.0, 1000.0, 2.0]

ATLAS_DOC = {
    "schema_version": "flybrain.atlas/v1",
    "source": {"connectome": "synthetic test fixture"},
    "groups": {
        "sugar_grn": {"role": "sensory", "flywire_ids": [SYNTH_IDS[5], SYNTH_IDS[6]]},
        "p9_left": {"role": "motor", "flywire_ids": [SYNTH_IDS[0]]},
        "p9_right": {"role": "motor", "flywire_ids": [SYNTH_IDS[2]]},
        "ghost": {"role": "custom", "flywire_ids": [999_999]},
    },
    "derived": {
        "p9_left_downstream": {
            "downstream_of": ["p9_left"],
            "hops": 1,
            "min_weight": 5,
            "exclude": ["p9_right"],
            "role": "motor",
        },
        "p9_right_downstream": {
            "downstream_of": ["p9_right"],
            "hops": 1,
            "min_weight": 5,
            "exclude": ["p9_left"],
            "role": "motor",
        },
        "p9_shared_downstream": {
            "downstream_of": ["p9_left", "p9_right"],
            "hops": 1,
            "min_weight": 5,
            "intersection": True,
            "role": "motor",
        },
        "sugar_downstream": {"downstream_of": ["sugar_grn"], "hops": 1, "min_weight": 5},
    },
    "sensorimotor": {
        "note": "test mapping",
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
    },
}

FORT_STEWART_SLICE = {
    "ao": {
        "name": "Fort Stewart",
        "bbox": [-81.70, 31.80, -81.45, 32.05],
        "center": {"lat": 31.8697, "lon": -81.6072},
    },
    "assets": [
        {"id": "hq", "type": "friendly_unit", "lat": 31.88, "lon": -81.61},
        {"id": "node-a", "type": "sensor", "lat": 31.90, "lon": -81.58},
    ],
}

CHANNEL_KEYS = {"pathways", "navigation", "biology", "information"}


def _data_dir():
    raw = os.getenv("FLYBRAIN_DATA_DIR", "").strip()
    if not raw:
        return None
    path = Path(raw)
    if (path / "2025_Completeness_783.csv").is_file() and (
        path / "2025_Connectivity_783.npz"
    ).is_file():
        return path
    return None


requires_real_data = pytest.mark.skipif(
    _data_dir() is None,
    reason="FLYBRAIN_DATA_DIR with 2025_Completeness_783.csv + 2025_Connectivity_783.npz not set",
)


def run(coro):
    return asyncio.run(coro)


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(flybrain_api.router)
    return app


def _env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, atlas: bool) -> None:
    if atlas:
        atlas_path = tmp_path / "atlas.yaml"
        atlas_path.write_text(yaml.safe_dump(ATLAS_DOC), encoding="utf-8")
        monkeypatch.setenv("FLYBRAIN_ATLAS_PATH", str(atlas_path))
    else:
        monkeypatch.delenv("FLYBRAIN_ATLAS_PATH", raising=False)
    monkeypatch.setenv("FLYBRAIN_RECORD_DIR", str(tmp_path / "records"))
    monkeypatch.setenv("FLYBRAIN_DATA_DIR", str(tmp_path / "no-data"))
    monkeypatch.setenv("FLYBRAIN_BACKEND", "numpy")
    monkeypatch.delenv("FLYBRAIN_DROID_ACTUATE", raising=False)
    monkeypatch.delenv("FLYBRAIN_REMOTE_DETECTOR_URL", raising=False)
    monkeypatch.delenv("PSATHYRELLA_CAM_DETECT_URL", raising=False)


@pytest.fixture
def synth() -> Connectome:
    return Connectome.from_arrays(SYNTH_IDS, SYNTH_PRE, SYNTH_POST, SYNTH_W)


@pytest.fixture
def runtime(tmp_path: Path, synth: Connectome, monkeypatch: pytest.MonkeyPatch) -> FlyBrainRuntime:
    """Process runtime over the synthetic connectome (the router uses ``get_runtime()``)."""
    _env(monkeypatch, tmp_path, atlas=True)
    set_cached_connectome(synth)
    set_detector_for_tests(None)
    rt = reset_runtime_for_tests()
    yield rt
    run(rt.close())
    reset_connectome_cache()
    set_detector_for_tests(None)
    reset_runtime_for_tests()


@pytest.fixture
def no_connectome(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FlyBrainRuntime:
    """Runtime with nothing on disk and nothing pinned — the honest 'unavailable' state."""
    _env(monkeypatch, tmp_path, atlas=True)
    (tmp_path / "no-data").mkdir()
    reset_connectome_cache()
    set_detector_for_tests(None)
    rt = reset_runtime_for_tests()
    yield rt
    run(rt.close())
    reset_connectome_cache()
    set_detector_for_tests(None)
    reset_runtime_for_tests()


@pytest.fixture
def client(runtime: FlyBrainRuntime):
    with TestClient(_app()) as tc:
        yield tc


@pytest.fixture
def client_no_connectome(no_connectome: FlyBrainRuntime):
    with TestClient(_app()) as tc:
        yield tc


def _create(client: TestClient, **cfg) -> dict:
    body = {"plug": "standalone", "seed": 7, "window_ms": 50.0}
    body.update(cfg)
    resp = client.post("/api/flybrain/sessions", json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Health / manifest / atlas
# ---------------------------------------------------------------------------


def test_health_schema_and_honest_status(client: TestClient):
    resp = client.get("/api/flybrain/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["schema_version"] == "flybrain/v1"
    assert body["status"] in ("healthy", "degraded")
    assert body["connectome"]["loaded"] is True
    assert body["connectome"]["n_neurons"] == N_SYNTH
    assert body["backend"] == "numpy"
    assert set(body["plugs"]) == {"standalone", "droid", "earthsim", "nlm", "itdx"}
    assert body["sessions"] == 0 and body["autopilots"] == 0
    assert "SIMULATED" in body["note"]
    # no detector backend in this environment → vision is honestly unavailable
    assert body["vision"]["available"] is False
    assert body["status"] == "degraded"


def test_health_without_connectome_is_unavailable(client_no_connectome: TestClient):
    body = client_no_connectome.get("/api/flybrain/health").json()
    assert body["status"] == "unavailable"
    assert body["connectome"]["loaded"] is False
    assert "flybrain_fetch_connectome.py" in body["connectome"]["reason"]
    manifest = client_no_connectome.get("/api/flybrain/connectome/manifest").json()
    assert manifest["loaded"] is False and manifest["n_neurons"] == 0
    atlas = client_no_connectome.get("/api/flybrain/atlas").json()
    assert atlas["schema_version"] == "flybrain.atlas/v1"
    assert atlas["connectome_loaded"] is False


def test_manifest_and_atlas_with_fixture(client: TestClient):
    manifest = client.get("/api/flybrain/connectome/manifest").json()
    assert manifest["loaded"] is True and manifest["n_neurons"] == N_SYNTH
    assert manifest["sha256_ok"] is None  # in-memory fixture: nothing to verify
    atlas = client.get("/api/flybrain/atlas").json()
    assert atlas["connectome_loaded"] is True
    names = {g["name"] for g in atlas["groups"]}
    assert {"p9_left", "p9_right", "sugar_grn", "p9_shared_downstream"} <= names
    ghost = next(g for g in atlas["groups"] if g["name"] == "ghost")
    assert ghost["missing_ids"] == [999_999]
    assert atlas["sensorimotor"]["inputs"]["left"]["groups"] == ["p9_left"]


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


def test_sessions_503_when_connectome_unavailable(client_no_connectome: TestClient):
    resp = client_no_connectome.post("/api/flybrain/sessions", json={"plug": "standalone"})
    assert resp.status_code == 503, resp.text
    detail = resp.json()["detail"]
    assert detail["error"] == "connectome_unavailable"
    assert "flybrain_fetch_connectome.py" in detail["reason"]
    assert detail["fetch"].startswith(
        "poetry run python scripts/flybrain_fetch_connectome.py --dest "
    )
    assert detail["fetch"].endswith(os.environ["FLYBRAIN_DATA_DIR"])
    assert client_no_connectome.get("/api/flybrain/sessions").json() == []


def test_session_lifecycle_tick_stimulate_spikes_reset_delete(client: TestClient):
    info = _create(client)
    sid = info["session_id"]
    assert info["schema_version"] == "flybrain/v1"
    assert info["status"] == "ready" and info["backend"] == "numpy"
    assert info["n_neurons"] == N_SYNTH and info["n_synapses"] == len(SYNTH_W)
    assert info["plug"]["name"] == "standalone" and info["plug"]["origin"] == "SIMULATED"

    listed = client.get("/api/flybrain/sessions").json()
    assert [s["session_id"] for s in listed] == [sid]
    assert client.get(f"/api/flybrain/sessions/{sid}").json()["session_id"] == sid
    assert client.get("/api/flybrain/health").json()["sessions"] == 1

    # tick with a raw_rates observation → SIMULATED rates, left turn
    resp = client.post(
        f"/api/flybrain/sessions/{sid}/tick",
        json={"observations": [{"kind": "raw_rates", "payload": {"p9_left": 100.0}}]},
    )
    assert resp.status_code == 200, resp.text
    tick = resp.json()
    assert tick["origin"] == "SIMULATED" and tick["brain"]["origin"] == "SIMULATED"
    assert tick["tick"] == 1 and tick["t_ms"] == pytest.approx(50.0)
    assert tick["encoded_rates_hz"] == {"p9_left": 100.0}
    rates = tick["brain"]["rates_hz"]
    assert rates["p9_left"] > 0.0 and rates["p9_left_downstream"] > 0.0
    assert rates["p9_right"] == 0.0
    assert "ghost" not in rates
    assert tick["action"]["turn"] < 0.0
    assert tick["plug"] == "standalone" and tick["dry_run"] is True
    assert tick["plug_result"]["actuated"] is False
    assert tick["nav"] is None and tick["detections"] is None

    # empty body tick
    resp = client.post(f"/api/flybrain/sessions/{sid}/tick")
    assert resp.status_code == 200 and resp.json()["tick"] == 2
    assert resp.json()["encoded_rates_hz"] == {}

    # stimulate (persistent manual drive) → BrainState
    resp = client.post(
        f"/api/flybrain/sessions/{sid}/stimulate",
        json=[{"group": "p9_right", "rate_hz": 100.0}],
    )
    assert resp.status_code == 200, resp.text
    state = resp.json()
    assert state["schema_version"] == "flybrain/v1" and state["origin"] == "SIMULATED"
    assert state["stimulated_hz"] == {"p9_right": 100.0}
    tick = client.post(f"/api/flybrain/sessions/{sid}/tick").json()
    assert tick["brain"]["rates_hz"]["p9_right"] > 0.0 and tick["action"]["turn"] > 0.0
    resp = client.post(
        f"/api/flybrain/sessions/{sid}/stimulate", json=[{"group": "p9_right", "mode": "silence"}]
    )
    assert resp.json()["silenced"] == ["p9_right"]
    assert client.post(f"/api/flybrain/sessions/{sid}/stimulate", json=[]).status_code == 400
    resp = client.post(
        f"/api/flybrain/sessions/{sid}/stimulate", json=[{"group": "nope", "rate_hz": 10.0}]
    )
    assert resp.status_code == 400 and "unknown atlas group" in resp.json()["detail"]["reason"]

    # state / spikes
    state = client.get(f"/api/flybrain/sessions/{sid}/state", params={"window_ms": 20}).json()
    assert state["window_ms"] == 20.0 and state["n_neurons"] == N_SYNTH
    spikes = client.get(f"/api/flybrain/sessions/{sid}/spikes", params={"limit": 40}).json()
    assert spikes["session_id"] == sid and spikes["count"] <= 40
    assert len(spikes["flywire_ids"]) == spikes["count"] == len(spikes["times_ms"])
    assert all(fid in SYNTH_IDS for fid in spikes["flywire_ids"])
    assert spikes["count"] > 0
    assert (
        client.get(f"/api/flybrain/sessions/{sid}/spikes", params={"limit": 999999}).status_code
        == 422
    )

    # reset
    reset = client.post(f"/api/flybrain/sessions/{sid}/reset").json()
    assert reset["ticks"] == 0 and reset["t_ms"] == 0.0 and reset["status"] == "ready"
    assert client.get(f"/api/flybrain/sessions/{sid}/state").json()["step"] == 0

    # delete → 404 afterwards
    deleted = client.delete(f"/api/flybrain/sessions/{sid}")
    assert deleted.status_code == 200 and deleted.json()["status"] == "stopped"
    for path in (
        f"/api/flybrain/sessions/{sid}",
        f"/api/flybrain/sessions/{sid}/state",
        f"/api/flybrain/sessions/{sid}/spikes",
    ):
        resp = client.get(path)
        assert resp.status_code == 404, path
        assert resp.json()["detail"]["error"] == "session_not_found"
    assert client.post(f"/api/flybrain/sessions/{sid}/tick").status_code == 404
    assert client.post(f"/api/flybrain/sessions/{sid}/reset").status_code == 404
    assert client.delete(f"/api/flybrain/sessions/{sid}").status_code == 404
    assert client.get("/api/flybrain/sessions").json() == []


def test_session_config_validation_and_limit(client: TestClient, runtime: FlyBrainRuntime):
    assert client.post("/api/flybrain/sessions", json={"plug": "toaster"}).status_code == 422
    assert client.post("/api/flybrain/sessions", json={"dt_ms": 0}).status_code == 422
    # Regression: a sub-minimum dt_ms (1e-9 ms) combined with a 5000 ms window
    # would mean ~5e12 engine steps in one tick; the schema floor rejects it.
    assert client.post("/api/flybrain/sessions", json={"dt_ms": 1e-9}).status_code == 422
    assert client.post("/api/flybrain/sessions", json={"dt_ms": 0.009}).status_code == 422
    runtime.settings.max_sessions = 1
    first = _create(client)
    resp = client.post("/api/flybrain/sessions", json={"plug": "standalone"})
    assert resp.status_code == 429
    assert resp.json()["detail"]["error"] == "session_limit_reached"
    client.delete(f"/api/flybrain/sessions/{first['session_id']}")


def test_autopilot_endpoint_starts_and_stops(client: TestClient, runtime: FlyBrainRuntime):
    info = _create(client, seed=11, window_ms=20.0)
    sid = info["session_id"]
    resp = client.post(
        f"/api/flybrain/sessions/{sid}/autopilot", json={"enabled": True, "period_s": 0.01}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["autopilot"] is True
    assert runtime._session(sid).autopilot_period_s == pytest.approx(0.2)  # clamped
    deadline = time.time() + 3.0
    ticks = 0
    while time.time() < deadline:
        ticks = client.get(f"/api/flybrain/sessions/{sid}").json()["ticks"]
        if ticks >= 2:
            break
        time.sleep(0.1)
    assert ticks >= 2
    assert client.get("/api/flybrain/health").json()["autopilots"] == 1
    resp = client.post(f"/api/flybrain/sessions/{sid}/autopilot", json={"enabled": False})
    assert resp.json()["autopilot"] is False
    stopped_at = client.get(f"/api/flybrain/sessions/{sid}").json()["ticks"]
    time.sleep(0.3)
    assert client.get(f"/api/flybrain/sessions/{sid}").json()["ticks"] == stopped_at
    assert client.get("/api/flybrain/health").json()["autopilots"] == 0
    assert (
        client.post("/api/flybrain/sessions/nope/autopilot", json={"enabled": True}).status_code
        == 404
    )
    client.delete(f"/api/flybrain/sessions/{sid}")


# ---------------------------------------------------------------------------
# Vision (no ultralytics / remote in this environment → honest 503)
# ---------------------------------------------------------------------------


def test_vision_health_and_detect_unavailable(client: TestClient):
    health = client.get("/api/flybrain/vision/health").json()
    assert health["available"] is False
    assert health["reason"]
    png = base64.b64encode(b"not-really-an-image").decode()
    resp = client.post("/api/flybrain/vision/detect", json={"image_b64": png})
    assert resp.status_code == 503, resp.text
    detail = resp.json()["detail"]
    assert detail["error"] == "detector_unavailable" and detail["reason"]
    assert "detections" not in detail  # no synthetic boxes, ever
    # multipart is refused with the same honest 503
    resp = client.post(
        "/api/flybrain/vision/detect",
        files={"image": ("frame.jpg", io.BytesIO(b"\xff\xd8\xff"), "image/jpeg")},
    )
    assert resp.status_code == 503
    assert resp.json()["detail"]["error"] == "detector_unavailable"


def test_vision_detect_request_parsing_precedes_detection(monkeypatch: pytest.MonkeyPatch, runtime):
    """With a detector that reports available, malformed requests are 4xx, not 503."""
    from mycosoft_mas.flybrain.schemas import VisionHealth

    class _AvailableProbe:
        def health(self):
            return VisionHealth(available=True, engine="test-probe", reason="")

        async def adetect(self, image, **kwargs):  # pragma: no cover - never reached
            raise AssertionError("adetect must not run for malformed requests")

    monkeypatch.setattr(runtime, "_detector", lambda: _AvailableProbe())
    with TestClient(_app()) as client:
        resp = client.post("/api/flybrain/vision/detect", json={})
        assert resp.status_code == 400
        assert "image_b64 or image_url" in resp.json()["detail"]["reason"]
        resp = client.post("/api/flybrain/vision/detect", json={"image_b64": "@@not-b64@@"})
        assert resp.status_code == 400
        resp = client.post("/api/flybrain/vision/detect", json={"image_url": "ftp://x/y.jpg"})
        assert resp.status_code == 400
        assert "http(s)" in resp.json()["detail"]["reason"]
        resp = client.post("/api/flybrain/vision/detect", json={"image_b64": "AAAA", "conf": 2})
        assert resp.status_code == 400
        resp = client.post(
            "/api/flybrain/vision/detect",
            content=b"garbage",
            headers={"content-type": "text/plain"},
        )
        assert resp.status_code == 400
        resp = client.post(
            "/api/flybrain/vision/detect",
            files={"image": ("frame.jpg", io.BytesIO(b"\xff\xd8"), "image/jpeg")},
            data={"pose": "{not json"},
        )
        assert resp.status_code == 400


def test_vision_image_url_fetch_limits(monkeypatch: pytest.MonkeyPatch, runtime):
    import httpx

    from mycosoft_mas.flybrain.schemas import VisionHealth

    seen = {}

    class _Probe:
        def health(self):
            return VisionHealth(available=True, engine="test-probe")

        async def adetect(self, image, **kwargs):
            seen["image"] = image
            seen["kwargs"] = kwargs
            return DetectionFrame(engine="test-probe", detections=[], source=kwargs["source"])

    monkeypatch.setattr(runtime, "_detector", lambda: _Probe())

    async def _public(host: str):  # no DNS in tests; cam.local is treated as a public host
        return [PUBLIC_ADDR]

    monkeypatch.setattr(flybrain_api, "_resolve_host", _public)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/big.jpg":
            return httpx.Response(200, content=b"x" * (flybrain_api.IMAGE_MAX_BYTES + 1))
        if request.url.path == "/missing.jpg":
            return httpx.Response(404)
        return httpx.Response(200, content=b"\x89PNG-bytes")

    real_client = httpx.AsyncClient

    def _patched(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", _patched)
    with TestClient(_app()) as client:
        resp = client.post(
            "/api/flybrain/vision/detect",
            json={"image_url": "http://cam.local/big.jpg"},
        )
        assert resp.status_code == 413
        resp = client.post(
            "/api/flybrain/vision/detect", json={"image_url": "http://cam.local/missing.jpg"}
        )
        assert resp.status_code == 502
        resp = client.post(
            "/api/flybrain/vision/detect",
            json={
                "image_url": "http://cam.local/ok.png",
                "sahi": False,
                "conf": 0.4,
                "pose": {"lat": 1.0, "lon": 2.0, "heading_deg": 90},
                "source": "cam",
            },
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["detections"] == [] and resp.json()["engine"] == "test-probe"
        assert seen["image"] == b"\x89PNG-bytes"
        assert seen["kwargs"]["sahi"] is False and seen["kwargs"]["conf"] == 0.4
        assert seen["kwargs"]["pose"] == {"lat": 1.0, "lon": 2.0, "heading_deg": 90.0}
        assert seen["kwargs"]["source"] == "cam"
        # multipart path with form fields
        resp = client.post(
            "/api/flybrain/vision/detect",
            files={"image": ("frame.jpg", io.BytesIO(b"JPEGDATA"), "image/jpeg")},
            data={"sahi": "1", "conf": "0.3", "pose": '{"lat": 3, "lon": 4}'},
        )
        assert resp.status_code == 200, resp.text
        assert seen["image"] == b"JPEGDATA" and seen["kwargs"]["sahi"] is True
        assert seen["kwargs"]["pose"] == {"lat": 3.0, "lon": 4.0}


# ---------------------------------------------------------------------------
# Vision: SSRF guard on image_url and bounded request bodies (review findings)
# ---------------------------------------------------------------------------

PUBLIC_ADDR = "93.184.216.34"


def _available_probe(seen: dict):
    from mycosoft_mas.flybrain.schemas import VisionHealth

    class _Probe:
        def health(self):
            return VisionHealth(available=True, engine="test-probe")

        async def adetect(self, image, **kwargs):
            seen["image"] = image
            seen["kwargs"] = kwargs
            return DetectionFrame(engine="test-probe", detections=[], source=kwargs["source"])

    return _Probe()


def _patch_httpx(monkeypatch: pytest.MonkeyPatch, handler):
    import httpx

    real_client = httpx.AsyncClient

    def _patched(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", _patched)


@pytest.mark.parametrize(
    "target",
    [
        "http://127.0.0.1:8001/api/health",
        "http://192.168.0.189:5432/",
        "http://192.168.0.188:8001/api/flybrain/health",
        "http://10.0.0.7/x.png",
        "http://172.16.4.4/x.png",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]/x.png",
        "http://[::ffff:192.168.0.190]/x.png",
        "http://0.0.0.0/x.png",
        "http://224.0.0.1/x.png",
        "http://100.64.1.1/x.png",
    ],
)
def test_vision_image_url_refuses_internal_targets(
    monkeypatch: pytest.MonkeyPatch, runtime, target: str
):
    import httpx

    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(200, content=b"\x89PNG-bytes")

    monkeypatch.delenv(flybrain_api.IMAGE_URL_ALLOW_HOSTS_ENV, raising=False)
    monkeypatch.setattr(runtime.settings, "remote_detector_url", None)
    monkeypatch.setattr(runtime, "_detector", lambda: _available_probe({}))
    _patch_httpx(monkeypatch, handler)
    with TestClient(_app()) as client:
        resp = client.post("/api/flybrain/vision/detect", json={"image_url": target})
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["error"] == "image_url_forbidden"
    assert calls == []  # the guard fires before any socket is opened


def test_vision_image_url_hostname_resolving_to_private_is_refused(
    monkeypatch: pytest.MonkeyPatch, runtime
):
    import httpx

    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(200, content=b"\x89PNG-bytes")

    async def _private(host: str):
        assert host == "cam.internal"
        return ["192.168.0.190", PUBLIC_ADDR]  # one private record is enough to refuse

    monkeypatch.delenv(flybrain_api.IMAGE_URL_ALLOW_HOSTS_ENV, raising=False)
    monkeypatch.setattr(runtime.settings, "remote_detector_url", None)
    monkeypatch.setattr(runtime, "_detector", lambda: _available_probe({}))
    monkeypatch.setattr(flybrain_api, "_resolve_host", _private)
    _patch_httpx(monkeypatch, handler)
    with TestClient(_app()) as client:
        resp = client.post(
            "/api/flybrain/vision/detect", json={"image_url": "http://cam.internal/f.png"}
        )
    assert resp.status_code == 400 and resp.json()["detail"]["error"] == "image_url_forbidden"
    assert calls == []


def test_vision_image_url_allow_list_permits_lan_cameras(monkeypatch: pytest.MonkeyPatch, runtime):
    import httpx

    seen: dict = {}
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(200, content=b"\x89PNG-bytes")

    async def _never(host: str):  # pragma: no cover - allow-listed hosts skip DNS
        raise AssertionError("allow-listed hosts must not be resolved")

    monkeypatch.setattr(runtime, "_detector", lambda: _available_probe(seen))
    monkeypatch.setattr(flybrain_api, "_resolve_host", _never)
    _patch_httpx(monkeypatch, handler)
    # 1) explicit env allow-list (IP literal and hostname, case-insensitive)
    monkeypatch.setenv(flybrain_api.IMAGE_URL_ALLOW_HOSTS_ENV, " 192.168.0.187 , Cam.Local ")
    monkeypatch.setattr(runtime.settings, "remote_detector_url", None)
    with TestClient(_app()) as client:
        resp = client.post(
            "/api/flybrain/vision/detect", json={"image_url": "http://192.168.0.187:8003/f.png"}
        )
        assert resp.status_code == 200, resp.text
        resp = client.post(
            "/api/flybrain/vision/detect", json={"image_url": "http://CAM.local/f.png"}
        )
        assert resp.status_code == 200, resp.text
        assert seen["image"] == b"\x89PNG-bytes"
        # not on the list → still refused
        resp = client.post(
            "/api/flybrain/vision/detect", json={"image_url": "http://192.168.0.189:5432/"}
        )
        assert resp.status_code == 400
    # 2) the configured remote detector host is implicitly allowed
    monkeypatch.delenv(flybrain_api.IMAGE_URL_ALLOW_HOSTS_ENV, raising=False)
    monkeypatch.setattr(runtime.settings, "remote_detector_url", "http://192.168.0.190:8600/detect")
    with TestClient(_app()) as client:
        resp = client.post(
            "/api/flybrain/vision/detect", json={"image_url": "http://192.168.0.190/cam.jpg"}
        )
        assert resp.status_code == 200, resp.text
        resp = client.post(
            "/api/flybrain/vision/detect", json={"image_url": "http://192.168.0.189/cam.jpg"}
        )
        assert resp.status_code == 400
    assert calls == [
        "http://192.168.0.187:8003/f.png",
        "http://cam.local/f.png",
        "http://192.168.0.190/cam.jpg",
    ]


def test_vision_image_url_no_redirects_and_generic_failure_reason(
    monkeypatch: pytest.MonkeyPatch, runtime
):
    import httpx

    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if request.url.path == "/bounce":
            return httpx.Response(302, headers={"location": "http://192.168.0.189:5432/"})
        if request.url.path == "/auth":
            return httpx.Response(401, content=b"nope")
        if request.url.path == "/boom":
            raise httpx.ConnectError("connection refused to secret-host:9999")
        if request.url.path == "/empty":
            return httpx.Response(200, content=b"")
        return httpx.Response(200, content=b"\x89PNG-bytes")

    async def _public(host: str):
        return [PUBLIC_ADDR]

    monkeypatch.delenv(flybrain_api.IMAGE_URL_ALLOW_HOSTS_ENV, raising=False)
    monkeypatch.setattr(runtime.settings, "remote_detector_url", None)
    monkeypatch.setattr(runtime, "_detector", lambda: _available_probe({}))
    monkeypatch.setattr(flybrain_api, "_resolve_host", _public)
    _patch_httpx(monkeypatch, handler)
    with TestClient(_app()) as client:
        reasons = []
        for path in ("/bounce", "/auth", "/boom", "/empty"):
            resp = client.post(
                "/api/flybrain/vision/detect", json={"image_url": f"http://pub.example{path}"}
            )
            assert resp.status_code == 502, (path, resp.text)
            detail = resp.json()["detail"]
            assert detail["error"] == "image_url_fetch_failed"
            reasons.append(detail["reason"])
    # one generic reason for every failure mode: no status code, URL, host or exception class
    assert len(set(reasons)) == 1
    reason = reasons[0]
    for leak in ("302", "401", "ConnectError", "secret-host", "pub.example", "refused"):
        assert leak not in reason
    # the redirect target (internal) was never requested
    assert calls == [f"http://pub.example{p}" for p in ("/bounce", "/auth", "/boom", "/empty")]


def test_vision_image_url_overall_timeout_budget(monkeypatch: pytest.MonkeyPatch, runtime):
    import httpx

    async def handler(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(2.0)  # slow-drip server: longer than the whole budget
        return httpx.Response(200, content=b"\x89PNG-bytes")

    async def _public(host: str):
        return [PUBLIC_ADDR]

    monkeypatch.delenv(flybrain_api.IMAGE_URL_ALLOW_HOSTS_ENV, raising=False)
    monkeypatch.setattr(runtime.settings, "remote_detector_url", None)
    monkeypatch.setattr(runtime, "_detector", lambda: _available_probe({}))
    monkeypatch.setattr(flybrain_api, "_resolve_host", _public)
    monkeypatch.setattr(flybrain_api, "IMAGE_URL_TIMEOUT_S", 0.3)
    _patch_httpx(monkeypatch, handler)
    with TestClient(_app()) as client:
        t0 = time.monotonic()
        resp = client.post(
            "/api/flybrain/vision/detect", json={"image_url": "http://pub.example/slow.png"}
        )
        elapsed = time.monotonic() - t0
    assert resp.status_code == 502 and resp.json()["detail"]["error"] == "image_url_fetch_failed"
    assert elapsed < 1.5, elapsed
    assert resp.json()["detail"]["reason"] == flybrain_api.IMAGE_URL_FETCH_FAILED_REASON


def test_is_public_address_classification():
    public = flybrain_api._is_public_address
    for addr in ("127.0.0.1", "10.1.2.3", "172.31.0.1", "192.168.0.188", "169.254.169.254"):
        assert public(addr) is False, addr
    for addr in ("::1", "fe80::1%eth0", "fc00::1", "::", "0.0.0.0", "224.0.0.1", "100.64.0.1"):
        assert public(addr) is False, addr
    assert public("::ffff:10.0.0.1") is False
    assert public("not-an-ip") is False
    assert public(PUBLIC_ADDR) is True
    assert public("2606:2800:220:1:248:1893:25c8:1946") is True


def _asgi_request(headers: dict, chunks):
    """Build a starlette Request whose body arrives as ``chunks`` (chunked, no buffering)."""
    from starlette.requests import Request

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/flybrain/vision/detect",
        "query_string": b"",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
    }
    pending = list(chunks)
    delivered = []

    async def receive():
        assert pending, "receive() called after the body was exhausted"
        chunk = pending.pop(0)
        delivered.append(chunk)
        return {"type": "http.request", "body": chunk, "more_body": bool(pending)}

    return Request(scope, receive), delivered


def test_read_bounded_body_rejects_declared_oversize_before_reading():
    from fastapi import HTTPException

    cap = flybrain_api.DETECT_BODY_MAX_BYTES
    assert cap == flybrain_api.IMAGE_MAX_BYTES * 4 // 3 + 64 * 1024
    request, delivered = _asgi_request({"content-length": str(cap + 1)}, [b"x" * 10])
    with pytest.raises(HTTPException) as info:
        asyncio.run(flybrain_api._read_bounded_body(request))
    assert info.value.status_code == 413
    assert info.value.detail["error"] == "request_too_large"
    assert delivered == []  # refused on the header alone; nothing was buffered
    request, _ = _asgi_request({"content-length": "abc"}, [b"x"])
    with pytest.raises(HTTPException) as info:
        asyncio.run(flybrain_api._read_bounded_body(request))
    assert info.value.status_code == 400


def test_read_bounded_body_aborts_chunked_stream_at_cap():
    from fastapi import HTTPException

    cap = flybrain_api.DETECT_BODY_MAX_BYTES
    chunk = b"A" * (1024 * 1024)
    n_chunks = cap // len(chunk) + 3  # a few MB past the cap
    request, delivered = _asgi_request({}, [chunk] * n_chunks)  # no Content-Length (chunked)
    with pytest.raises(HTTPException) as info:
        asyncio.run(flybrain_api._read_bounded_body(request))
    assert info.value.status_code == 413
    assert info.value.detail["error"] == "request_too_large"
    # aborted as soon as the running total passed the cap — the rest was never pulled
    assert cap < sum(map(len, delivered)) <= cap + len(chunk)
    assert len(delivered) < n_chunks
    # an in-budget body round-trips intact
    request, _ = _asgi_request({}, [b'{"a": 1', b"}"])
    assert asyncio.run(flybrain_api._read_bounded_body(request)) == b'{"a": 1}'


def test_vision_detect_oversized_bodies_are_413_before_parsing(
    monkeypatch: pytest.MonkeyPatch, runtime
):
    """End-to-end: a JSON or multipart body over the cap is refused with 413, never parsed."""

    class _NeverParsed(Exception):
        pass

    def _boom(*args, **kwargs):  # pragma: no cover - must not run
        raise _NeverParsed()

    monkeypatch.setattr(runtime, "_detector", lambda: _available_probe({}))
    monkeypatch.setattr(flybrain_api.VisionDetectJSON, "model_validate", _boom)
    monkeypatch.setattr(flybrain_api, "_decode_b64", _boom)
    oversized = flybrain_api.DETECT_BODY_MAX_BYTES + 1024
    with TestClient(_app()) as client:
        resp = client.post(
            "/api/flybrain/vision/detect",
            content=b'{"image_b64": "' + b"A" * oversized + b'"}',
            headers={"content-type": "application/json"},
        )
        assert resp.status_code == 413, resp.text
        assert resp.json()["detail"]["error"] == "request_too_large"
        resp = client.post(
            "/api/flybrain/vision/detect",
            files={"image": ("big.jpg", io.BytesIO(b"\xff" * oversized), "image/jpeg")},
        )
        assert resp.status_code == 413, resp.text
        assert resp.json()["detail"]["error"] == "request_too_large"
        # an image between the image cap and the body cap is still the honest image_too_large
        mid = flybrain_api.IMAGE_MAX_BYTES + 1
        resp = client.post(
            "/api/flybrain/vision/detect",
            files={"image": ("mid.jpg", io.BytesIO(b"\xff" * mid), "image/jpeg")},
        )
        assert resp.status_code == 413, resp.text
        assert resp.json()["detail"]["error"] == "image_too_large"


# ---------------------------------------------------------------------------
# ITDX channels
# ---------------------------------------------------------------------------


def test_itdx_channels_one_off_plans_without_brain(client: TestClient):
    resp = client.post("/api/flybrain/itdx/channels", json={"map_slice": FORT_STEWART_SLICE})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["schema_version"] == "flybrain.itdx_channels/v1"
    assert body["origin"] == "SIMULATED"
    assert body["session_id"] is None and body["tick"] is None
    assert set(body["channels"]) == CHANNEL_KEYS
    nav = body["nav"]
    assert nav["feasible"] is True, nav["note"]
    assert 2 <= len(nav["waypoints"]) <= 12
    assert nav["turn_bias"] == 0.0 and "turn_bias=0" in nav["note"]
    assert nav["start"] == {"lat": 31.8697, "lon": -81.6072}
    # goal lies north-east of the AO centre (toward the far bbox corner)
    assert nav["goal"]["lat"] > 31.8697 and nav["goal"]["lon"] > -81.6072
    navigation = body["channels"]["navigation"]
    assert navigation["status"] == "SCORED"
    assert 0.0 < navigation["p"] <= 1.0
    assert "free-cell fraction" in navigation["note"] and "not P(" in navigation["note"]
    assert navigation["live"]["session_id"] is None and navigation["live"]["tick"] is None
    assert body["channels"]["pathways"]["status"] == "SCORED"
    for key in ("biology", "information"):
        row = body["channels"][key]
        assert row["status"] == "NOT_SUPPLIED", key
        assert row["p"] is None and row["reason"] == "no detection frame this tick"
        assert row["agent_id"] == "flybrain"


def test_itdx_channels_one_off_with_detections_and_bad_input(client: TestClient):
    frame = DetectionFrame(
        engine="remote:test",
        detections=[
            Detection(
                id="d1",
                cls="deer",
                conf=0.8,
                bbox_xyxy=(0, 0, 10, 10),
                category="animal",
                taxon=Taxon(matched=True, scientific_name="Odocoileus virginianus"),
            ),
            Detection(id="d2", cls="truck", conf=0.6, bbox_xyxy=(0, 0, 10, 10), category="vehicle"),
        ],
    )
    resp = client.post(
        "/api/flybrain/itdx/channels",
        json={"map_slice": FORT_STEWART_SLICE, "detections": frame.model_dump(mode="json")},
    )
    assert resp.status_code == 200, resp.text
    rows = resp.json()["channels"]
    assert rows["biology"]["status"] == "SCORED" and rows["biology"]["p"] == pytest.approx(0.5)
    assert rows["information"]["status"] == "SCORED" and rows["information"]["sample_count"] == 2
    assert rows["information"]["p"] is None
    # a slice without an AO → infeasible nav, all rows NOT_SUPPLIED (no invented p)
    resp = client.post("/api/flybrain/itdx/channels", json={"map_slice": {"assets": []}})
    assert resp.status_code == 200
    body = resp.json()
    assert body["nav"]["feasible"] is False and "no AO centre" in body["nav"]["note"]
    assert all(row["status"] == "NOT_SUPPLIED" for row in body["channels"].values())
    resp = client.post(
        "/api/flybrain/itdx/channels",
        json={"map_slice": FORT_STEWART_SLICE, "detections": {"detections": "nope"}},
    )
    assert resp.status_code == 400
    resp = client.post(
        "/api/flybrain/itdx/channels", json={"map_slice": FORT_STEWART_SLICE, "session_id": "ghost"}
    )
    assert resp.status_code == 404


def test_itdx_channels_from_session_last_tick(client: TestClient):
    info = _create(client, plug="itdx", seed=5, plug_config={"map_slice": FORT_STEWART_SLICE})
    sid = info["session_id"]
    # before any tick: honest NOT_SUPPLIED everywhere
    body = client.post(
        "/api/flybrain/itdx/channels", json={"map_slice": FORT_STEWART_SLICE, "session_id": sid}
    ).json()
    assert body["session_id"] == sid and body["nav"] is None
    assert all(row["status"] == "NOT_SUPPLIED" for row in body["channels"].values())
    tick = client.post(
        f"/api/flybrain/sessions/{sid}/tick",
        json={"observations": [{"kind": "raw_rates", "payload": {"p9_right": 100}}]},
    ).json()
    assert tick["nav"]["feasible"] is True, tick["nav"]["note"]
    assert tick["plug_result"]["channels"]["navigation"]["status"] == "SCORED"
    body = client.post(
        "/api/flybrain/itdx/channels", json={"map_slice": FORT_STEWART_SLICE, "session_id": sid}
    ).json()
    assert body["tick"] == tick["tick"] == 1
    assert body["step"] == tick["brain"]["step"]
    assert body["channels"]["navigation"]["status"] == "SCORED"
    assert body["channels"]["navigation"]["live"]["session_id"] == sid
    assert body["channels"]["navigation"]["live"]["tick"] == 1
    assert body["channels"]["navigation"]["live"]["step"] == tick["brain"]["step"]
    assert body["channels"]["navigation"]["live"]["ao_source"] == "session plug map_slice"
    assert body["nav"]["feasible"] is True
    assert body["channels"]["biology"]["status"] == "NOT_SUPPLIED"
    client.delete(f"/api/flybrain/sessions/{sid}")


# ---------------------------------------------------------------------------
# NLM observation / droid guidance
# ---------------------------------------------------------------------------


def test_nlm_observation_endpoint(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    from mycosoft_mas.flybrain.plugs import nlm as nlm_mod
    from mycosoft_mas.nlm.formspace import observation_pipeline as pipe_mod

    monkeypatch.setattr(
        nlm_mod, "probe_nlm", lambda: {"model_loaded": False, "reason": "no weights"}
    )
    monkeypatch.setattr(pipe_mod, "_PIPELINE", None)
    info = _create(client, plug="standalone", seed=2)
    sid = info["session_id"]
    client.post(f"/api/flybrain/sessions/{sid}/tick")
    resp = client.post("/api/flybrain/nlm/observation", json={"session_id": sid})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["origin"] == "SIMULATED" and body["session_id"] == sid and body["tick"] == 1
    assert body["pipeline_result"]["status"] == "accepted"
    assert body["pipeline_result"]["consumed"] is True
    env = body["envelope"]
    assert env["schema_version"] == "formspace.observation/v1"
    assert env["origin"] == "SYNTHETIC" and env["provenance"]["origin"] == "SIMULATED"
    assert env["root_evidence_id"] == f"flybrain:{sid}:1"
    assert env["chart_id"] == "flybrain.population_rates"
    assert body["forecast"]["support_status"] == "UNSUPPORTED"
    # replaying the same tick is a duplicate reading, never a second update
    again = client.post("/api/flybrain/nlm/observation", json={"session_id": sid}).json()
    assert again["pipeline_result"]["status"] == "duplicate_root_evidence"
    # an explicit cutoff before available_at is honestly excluded
    early = client.post(
        "/api/flybrain/nlm/observation",
        json={"session_id": sid, "cutoff": "2000-01-01T00:00:00Z"},
    ).json()
    assert early["pipeline_result"]["status"] == "excluded_future_available_at"
    assert (
        client.post("/api/flybrain/nlm/observation", json={"session_id": "ghost"}).status_code
        == 404
    )
    assert client.post("/api/flybrain/nlm/observation", json={}).status_code == 422
    client.delete(f"/api/flybrain/sessions/{sid}")


def test_droid_guidance_is_dry_run_and_never_actuates(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    from mycosoft_mas.core.routers import device_registry_api, psathyrella_api
    from mycosoft_mas.flybrain.plugs import droid as droid_mod

    calls = {"save": 0, "camera": 0, "avani": 0}

    async def _boom_save(device_id, waypoints):
        calls["save"] += 1
        raise AssertionError("_save_waypoints must not be called")

    async def _boom_cmd(**kwargs):
        calls["camera"] += 1
        raise AssertionError("send_device_command must not be called")

    async def _avani(*args, **kwargs):
        calls["avani"] += 1
        return {"approved": True, "reason": "test"}

    async def _telemetry(device_id):
        return {"gps": {"lat": 32.5629, "lon": -117.1357, "heading": 90.0, "sog": 1.2}}

    monkeypatch.setattr(psathyrella_api, "_save_waypoints", _boom_save)
    monkeypatch.setattr(device_registry_api, "send_device_command", _boom_cmd)
    monkeypatch.setattr(droid_mod, "evaluate_navigation_proposal", _avani)
    monkeypatch.setattr(droid_mod, "get_device_telemetry", _telemetry)

    # no session → hold, dry-run
    body = client.get("/api/flybrain/droid/psathyrella-test/guidance").json()
    assert body["dry_run"] is True and body["actuated"] is False
    assert body["mode"] == "hold" and body["origin"] == "SIMULATED"
    assert body["waypoints"] == [] and body["session_id"] is None
    assert (
        client.get(
            "/api/flybrain/droid/psathyrella-test/guidance", params={"session_id": "ghost"}
        ).status_code
        == 404
    )

    info = _create(
        client,
        plug="droid",
        seed=4,
        device_id="psathyrella-test",
        plug_config={"goal": {"lat": 32.5640, "lon": -117.1357}},
    )
    sid = info["session_id"]
    assert info["plug"]["gates"]["dry_run"] is True
    body = client.get(
        "/api/flybrain/droid/psathyrella-test/guidance", params={"session_id": sid}
    ).json()
    assert body["dry_run"] is True and body["actuated"] is False and body["tick"] == 0
    tick = client.post(
        f"/api/flybrain/sessions/{sid}/tick",
        json={"observations": [{"kind": "raw_rates", "payload": {"p9_left": 100}}]},
    ).json()
    assert tick["plug_result"]["actuated"] is False and tick["avani"] is None
    assert tick["nav"]["feasible"] is True, tick["nav"]["note"]
    body = client.get(
        "/api/flybrain/droid/psathyrella-test/guidance", params={"session_id": sid}
    ).json()
    assert body["dry_run"] is True and body["actuated"] is False
    assert body["device_id"] == "psathyrella-test" and body["session_id"] == sid
    assert body["tick"] == 1 and body["origin"] == "SIMULATED"
    assert body["mode"] == "flybrain_locomotion"
    assert body["waypoints"] and body["waypoints"][-1]["note"] == "goal"
    assert body["camera_point_at"]["bearing_deg"] == pytest.approx(
        (90.0 + body["heading_delta_deg"]) % 360.0
    )
    assert "dry_run" in body["reason"]  # the tick's own reason, not overwritten
    assert "read-only" in body["endpoint_note"]
    assert body["actuated_by_this_call"] is False and body["session_dry_run"] is True
    assert body["last_tick_actuated"] is False
    assert calls == {"save": 0, "camera": 0, "avani": 0}
    client.delete(f"/api/flybrain/sessions/{sid}")


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


def test_agent_status_and_unknown_type(runtime: FlyBrainRuntime):
    agent = FlyBrainAgent()
    assert agent.agent_id == "flybrain"
    assert CAPABILITIES <= agent.capabilities
    status = run(agent.process_task({"type": "status"}))
    assert status["status"] == "success" and status["origin"] == "SIMULATED"
    assert status["health"]["schema_version"] == "flybrain/v1"
    assert status["health"]["connectome"]["loaded"] is True
    assert status["flybrain_status"] in ("healthy", "degraded")
    assert status["sessions"] == [] and status["fetch"] is None
    assert "flybrain_simulate" in status["capabilities"]
    unknown = run(agent.process_task({"type": "dance"}))
    assert unknown["status"] == "error" and unknown["unavailable"] is False
    assert "Unknown task type" in unknown["message"] and "status" in unknown["message"]
    empty = run(agent.process_task({}))
    assert empty["status"] == "error"
    assert run(agent._check_services_health())["status"] in ("healthy", "degraded")
    assert run(agent._check_resource_usage())["sessions"] == 0
    assert run(agent._handle_error_type("x", "boom"))["status"] == "error"
    assert run(agent._handle_notification({"a": 1}))["status"] == "received"
    run(agent._initialize_services())


def test_agent_resource_usage_is_measured_not_fabricated(runtime: FlyBrainRuntime):
    """Regression: resource_usage must never publish a hard-coded cpu=0 / memory=0."""
    agent = FlyBrainAgent()
    first = run(agent._check_resource_usage())
    assert first["sessions"] == 0 and first["neurons_simulated"] == 0
    assert first["synapses_simulated"] == 0 and first["estimated_engine_bytes"] == 0
    assert first["cpu"] != 0 and first["memory"] != 0  # never a fabricated zero
    try:
        import psutil  # noqa: F401

        have_psutil = True
    except Exception:  # noqa: BLE001
        have_psutil = False
    if not have_psutil:
        assert first["cpu"] is None and first["memory"] is None
        assert "not measured" in first["note"]
        return
    # psutil present: RSS is a real positive byte count; the first cpu sample only primes.
    assert isinstance(first["memory"], int) and first["memory"] > 0
    assert first["cpu"] is None and "primes" in first["note"]
    created = run(agent.process_task({"type": "create_session", "config": {"plug": "standalone"}}))
    assert created["status"] == "success"
    info = created["session"]
    second = run(agent._check_resource_usage())
    assert second["sessions"] == 1
    assert second["neurons_simulated"] == info["n_neurons"] > 0
    assert second["synapses_simulated"] == info["n_synapses"] > 0
    assert second["estimated_engine_bytes"] == info["n_synapses"] * 8
    assert isinstance(second["cpu"], float) and second["cpu"] >= 0.0
    assert isinstance(second["memory"], int) and second["memory"] > 0
    assert "note" not in second
    # BaseAgent.health_check() publishes this verbatim.
    status = run(agent.health_check())
    assert status["resource_usage"]["estimated_engine_bytes"] == info["n_synapses"] * 8
    assert status["resource_usage"]["memory"] > 0
    run(agent.process_task({"type": "stop_session", "session_id": info["session_id"]}))


def test_agent_reports_unavailable_without_connectome(no_connectome: FlyBrainRuntime):
    agent = FlyBrainAgent()
    status = run(agent.process_task({"type": "status"}))
    assert status["status"] == "unavailable" and status["flybrain_status"] == "unavailable"
    assert status["fetch"].startswith("poetry run python scripts/flybrain_fetch_connectome.py")
    created = run(agent.process_task({"type": "create_session", "config": {"plug": "standalone"}}))
    assert created["status"] == "error" and created["unavailable"] is True
    assert "flybrain_fetch_connectome.py" in created["message"]
    detect = run(agent.process_task({"type": "detect", "image_path": "/nonexistent.jpg"}))
    assert detect["status"] == "error" and detect["unavailable"] is True
    assert "detector unavailable" in detect["message"]


def test_agent_session_tick_nlm_situation_navigate_stop(
    runtime: FlyBrainRuntime, monkeypatch: pytest.MonkeyPatch
):
    from mycosoft_mas.flybrain.plugs import nlm as nlm_mod
    from mycosoft_mas.nlm.formspace import observation_pipeline as pipe_mod

    monkeypatch.setattr(nlm_mod, "probe_nlm", lambda: {"model_loaded": False, "reason": "none"})
    monkeypatch.setattr(pipe_mod, "_PIPELINE", None)
    agent = FlyBrainAgent()

    bad = run(agent.process_task({"type": "create_session", "config": {"plug": "toaster"}}))
    assert bad["status"] == "error" and bad["unavailable"] is False
    created = run(
        agent.process_task(
            {
                "type": "create_session",
                "config": {
                    "plug": "itdx",
                    "seed": 5,
                    "plug_config": {"map_slice": FORT_STEWART_SLICE},
                },
            }
        )
    )
    assert created["status"] == "success", created
    sid = created["session"]["session_id"]
    assert created["session"]["plug"]["name"] == "itdx"

    missing = run(agent.process_task({"type": "tick"}))
    assert missing["status"] == "error" and "session_id" in missing["message"]
    ticked = run(
        agent.process_task(
            {
                "type": "tick",
                "session_id": sid,
                "observations": [{"kind": "raw_rates", "payload": {"p9_right": 100}}],
            }
        )
    )
    assert ticked["status"] == "success"
    result = ticked["result"]
    assert result["origin"] == "SIMULATED" and result["tick"] == 1
    # the itdx slice's assets add their own left/right drive, so only the driven
    # population and the planned path are asserted here (turn sign is not fixed)
    assert result["brain"]["rates_hz"]["p9_right"] > 0.0
    assert result["encoded_rates_hz"]["p9_right"] == 100.0
    assert result["nav"]["feasible"] is True and "drive side=" in result["nav"]["note"]
    ghost = run(agent.process_task({"type": "tick", "session_id": "ghost"}))
    assert ghost["status"] == "error" and ghost["unavailable"] is False
    assert ghost["error_type"] == "SessionNotFound"

    status = run(agent.process_task({"type": "status", "session_id": sid}))
    assert status["session"]["ticks"] == 1 and len(status["sessions"]) == 1

    coupled = run(agent.process_task({"type": "couple_nlm", "session_id": sid}))
    assert coupled["status"] == "success" and coupled["emits_probability"] is False
    assert coupled["pipeline_result"]["status"] == "accepted"
    assert coupled["forecast"]["support_status"] == "UNSUPPORTED"
    assert coupled["envelope"]["origin"] == "SYNTHETIC"

    situation = run(
        agent.process_task(
            {"type": "assess_situation", "map_slice": FORT_STEWART_SLICE, "session_id": sid}
        )
    )
    assert situation["status"] == "success" and set(situation["channels"]) == CHANNEL_KEYS
    assert situation["channels"]["navigation"]["status"] == "SCORED"
    assert situation["channels"]["biology"]["status"] == "NOT_SUPPLIED"
    one_off = run(agent.process_task({"type": "assess_situation", "map_slice": FORT_STEWART_SLICE}))
    assert one_off["status"] == "success" and one_off["session_id"] is None
    assert one_off["nav"]["feasible"] is True and one_off["nav"]["turn_bias"] == 0.0
    assert one_off["channels"]["information"]["status"] == "NOT_SUPPLIED"
    assert run(agent.process_task({"type": "assess_situation"}))["status"] == "error"

    # navigate: session's last path, then an explicit start/goal plan with an obstacle
    last = run(agent.process_task({"type": "navigate", "session_id": sid}))
    assert last["status"] == "success" and last["feasible"] is True
    planned = run(
        agent.process_task(
            {
                "type": "navigate",
                "start": {"lat": 31.8697, "lon": -81.6072},
                "goal": {"lat": 31.8703, "lon": -81.6072},
                "obstacles": [{"lat": 31.8699, "lon": -81.6072, "radius_m": 10.0}],
                "turn_bias": -0.3,
            }
        )
    )
    assert planned["status"] == "success" and planned["feasible"] is True, planned
    assert planned["nav"]["blocked_cells"] > 0 and planned["nav"]["turn_bias"] == pytest.approx(
        -0.3
    )
    assert "task.turn_bias" in planned["nav"]["note"]
    assert 2 <= len(planned["nav"]["waypoints"]) <= 12
    assert run(agent.process_task({"type": "navigate", "start": {"lat": 1}}))["status"] == "error"

    stopped = run(agent.process_task({"type": "stop_session", "session_id": sid}))
    assert stopped["status"] == "success" and stopped["session"]["status"] == "stopped"
    assert run(agent.process_task({"type": "stop_session", "session_id": sid}))["status"] == "error"
    assert run(agent.process_task({"type": "stop_session"}))["status"] == "error"
    assert runtime.list_sessions() == []


def test_agent_detect_requires_image_and_honours_detector(
    runtime: FlyBrainRuntime, monkeypatch: pytest.MonkeyPatch
):
    from mycosoft_mas.flybrain.schemas import VisionHealth

    class _Probe:
        def health(self):
            return VisionHealth(available=True, engine="test-probe")

        async def adetect(self, image, **kwargs):
            return DetectionFrame(engine="test-probe", detections=[], source=kwargs["source"])

    monkeypatch.setattr(runtime, "_detector", lambda: _Probe())
    agent = FlyBrainAgent()
    assert run(agent.process_task({"type": "detect"}))["status"] == "error"
    bad = run(agent.process_task({"type": "detect", "image_b64": "@@"}))
    assert bad["status"] == "error" and bad["unavailable"] is False
    ok = run(agent.process_task({"type": "detect", "image_b64": base64.b64encode(b"x").decode()}))
    assert ok["status"] == "success" and ok["n_detections"] == 0
    assert ok["frame"]["engine"] == "test-probe"


# ---------------------------------------------------------------------------
# Real FlyWire data (skipped unless FLYBRAIN_DATA_DIR holds the files)
# ---------------------------------------------------------------------------


@requires_real_data
def test_real_data_api_session_and_tick(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("FLYBRAIN_RECORD_DIR", str(tmp_path / "records"))
    monkeypatch.setenv("FLYBRAIN_BACKEND", "numpy")
    monkeypatch.delenv("FLYBRAIN_ATLAS_PATH", raising=False)
    monkeypatch.delenv("FLYBRAIN_REMOTE_DETECTOR_URL", raising=False)
    monkeypatch.delenv("PSATHYRELLA_CAM_DETECT_URL", raising=False)
    reset_connectome_cache()
    set_detector_for_tests(None)
    rt = reset_runtime_for_tests()
    try:
        with TestClient(_app()) as client:
            health = client.get("/api/flybrain/health").json()
            assert health["status"] in ("healthy", "degraded")
            assert health["connectome"]["loaded"] is False  # lazy until the first session
            t0 = time.perf_counter()
            resp = client.post(
                "/api/flybrain/sessions", json={"plug": "standalone", "seed": 42, "window_ms": 50.0}
            )
            t_create = time.perf_counter() - t0
            assert resp.status_code == 200, resp.text
            info = resp.json()
            assert info["n_neurons"] == 138_639 and info["n_synapses"] > 10_000_000
            t1 = time.perf_counter()
            tick = client.post(
                f"/api/flybrain/sessions/{info['session_id']}/tick",
                json={
                    "observations": [
                        {"kind": "raw_rates", "payload": {"p9_left": 100.0, "p9_right": 100.0}}
                    ]
                },
            ).json()
            t_tick = time.perf_counter() - t1
            print(
                f"\nreal-data API: create {t_create:.2f}s, 50 ms tick {t_tick:.2f}s "
                f"(wall_ms={tick['wall_ms']:.0f}), spikes={tick['brain']['spike_count_window']}"
            )
            assert tick["brain"]["n_neurons"] == 138_639
            assert tick["brain"]["rates_hz"]["p9_left"] > 0.0
            manifest = client.get("/api/flybrain/connectome/manifest").json()
            assert manifest["loaded"] is True and manifest["sha256_ok"] is not False
            assert client.delete(f"/api/flybrain/sessions/{info['session_id']}").status_code == 200
    finally:
        run(rt.close())
        reset_connectome_cache()
        reset_runtime_for_tests()
