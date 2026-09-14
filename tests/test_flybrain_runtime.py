"""Tests for the FlyBrain runtime and plugs (spec §2, §10, §11).

All tests run on an explicit in-memory synthetic connectome (a test
fixture — not production data) pinned through
``connectome.set_cached_connectome`` plus a temporary atlas YAML whose ids
exist in that fixture. No network. The real-data test is skipped unless
``FLYBRAIN_DATA_DIR`` holds ``2025_Completeness_783.csv`` and
``2025_Connectivity_783.npz``.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path

import pytest
import yaml

from mycosoft_mas.flybrain.connectome import (
    Connectome,
    ConnectomeUnavailable,
    reset_connectome_cache,
    set_cached_connectome,
)
from mycosoft_mas.flybrain.navigation import OccupancyGrid, plan
from mycosoft_mas.flybrain.plugs import PLUG_REGISTRY
from mycosoft_mas.flybrain.plugs import droid as droid_mod
from mycosoft_mas.flybrain.plugs import get_plug
from mycosoft_mas.flybrain.plugs.itdx import itdx_channel_rows
from mycosoft_mas.flybrain.plugs.nlm import NLMPlug, RateAnomalyTracker, build_envelope
from mycosoft_mas.flybrain.runtime import (
    FlyBrainRuntime,
    SessionNotFound,
    get_runtime,
    reset_runtime_for_tests,
)
from mycosoft_mas.flybrain.schemas import (
    BrainState,
    Detection,
    DetectionFrame,
    GeoPoint,
    MotorAction,
    NavPath,
    Observation,
    SessionConfig,
    StimulusCommand,
    Taxon,
    TickRequest,
    TickResult,
)
from mycosoft_mas.flybrain.vision.detector import set_detector_for_tests

# ---------------------------------------------------------------------------
# Synthetic fixture (indices into SYNTH_IDS)
#   0 (p9_left)  -> 1 (w=+1000), 0 -> 4 (w=+1000)
#   2 (p9_right) -> 3 (w=+1000), 2 -> 4 (w=+1000)   4 = shared downstream
#   5, 6 (sugar_grn) -> 7 (w=+1000)
#   1 -> 8 (w=+2)  weak, filtered by min_weight=5 in derived groups
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


@pytest.fixture
def synth() -> Connectome:
    return Connectome.from_arrays(SYNTH_IDS, SYNTH_PRE, SYNTH_POST, SYNTH_W)


@pytest.fixture
def runtime(tmp_path: Path, synth: Connectome, monkeypatch: pytest.MonkeyPatch) -> FlyBrainRuntime:
    """Runtime over the synthetic connectome with a temp atlas + record dir."""
    atlas_path = tmp_path / "atlas.yaml"
    atlas_path.write_text(yaml.safe_dump(ATLAS_DOC), encoding="utf-8")
    monkeypatch.setenv("FLYBRAIN_ATLAS_PATH", str(atlas_path))
    monkeypatch.setenv("FLYBRAIN_RECORD_DIR", str(tmp_path / "records"))
    monkeypatch.setenv("FLYBRAIN_DATA_DIR", str(tmp_path / "no-data"))
    monkeypatch.setenv("FLYBRAIN_BACKEND", "numpy")
    monkeypatch.delenv("FLYBRAIN_DROID_ACTUATE", raising=False)
    monkeypatch.delenv("FLYBRAIN_REMOTE_DETECTOR_URL", raising=False)
    monkeypatch.delenv("PSATHYRELLA_CAM_DETECT_URL", raising=False)
    set_cached_connectome(synth)
    set_detector_for_tests(None)
    rt = reset_runtime_for_tests()
    yield rt
    run(rt.close())
    reset_connectome_cache()
    set_detector_for_tests(None)
    reset_runtime_for_tests()


# ---------------------------------------------------------------------------
# Sessions and ticks
# ---------------------------------------------------------------------------


def test_get_runtime_singleton_and_registry():
    rt = get_runtime()
    assert rt is get_runtime()
    assert set(PLUG_REGISTRY) == {"standalone", "droid", "earthsim", "nlm", "itdx"}
    for name in PLUG_REGISTRY:
        plug = get_plug(name, SessionConfig(plug=name))  # type: ignore[arg-type]
        desc = plug.describe()
        assert desc["name"] == name and desc["origin"] == "SIMULATED"


def test_create_session_requires_connectome(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("FLYBRAIN_DATA_DIR", str(tmp_path / "empty"))
    reset_connectome_cache()
    rt = reset_runtime_for_tests()
    with pytest.raises(ConnectomeUnavailable) as excinfo:
        rt.create_session(SessionConfig())
    assert "flybrain_fetch_connectome.py" in str(excinfo.value)
    assert rt.list_sessions() == []


def test_standalone_tick_raw_rates(runtime: FlyBrainRuntime):
    info = runtime.create_session(SessionConfig(plug="standalone", seed=7, window_ms=50.0))
    assert info.status == "ready" and info.backend == "numpy"
    assert info.n_neurons == N_SYNTH and info.n_synapses == len(SYNTH_W)
    assert info.plug["name"] == "standalone"
    assert runtime.get_session(info.session_id).session_id == info.session_id

    req = TickRequest(
        observations=[Observation(kind="raw_rates", payload={"p9_left": 100.0, "bogus": 5})]
    )
    result = run(runtime.tick(info.session_id, req))
    assert isinstance(result, TickResult)
    assert result.origin == "SIMULATED" and result.brain.origin == "SIMULATED"
    assert result.tick == 1 and result.t_ms == pytest.approx(50.0)
    assert result.encoded_rates_hz == {"p9_left": 100.0}
    assert any("bogus" in n for n in result.notes)
    rates = result.brain.rates_hz
    assert "p9_left" in rates and "p9_left_downstream" in rates
    assert "ghost" not in rates  # no resolved neurons → no fabricated rate
    assert rates["p9_left"] > 0.0
    assert rates["p9_left_downstream"] > 0.0
    assert rates["p9_right"] == 0.0
    # p9_right_downstream = {3, 4}; 4 is the shared partner so it fires from left drive too
    assert rates["p9_right_downstream"] < rates["p9_left_downstream"]
    assert rates["p9_shared_downstream"] > 0.0
    assert result.brain.stimulated_hz == {"p9_left": 100.0}
    assert result.brain.spike_count_window > 0
    # left drive → left readout stronger → negative turn
    assert result.action.turn < 0.0
    assert result.action.evidence["formula"] == "locomotion_v1"
    assert result.action.evidence["origin"] == "SIMULATED"
    assert result.nav is None and result.detections is None
    assert result.plug_result["actuated"] is False
    assert result.wall_ms > 0.0
    assert result.dry_run is True

    # JSONL record written
    rec = Path(os.environ["FLYBRAIN_RECORD_DIR"]) / info.session_id / "ticks.jsonl"
    assert rec.is_file()
    lines = rec.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1 and json.loads(lines[0])["tick"] == 1

    # second tick without observations clears the encoded drive
    result2 = run(runtime.tick(info.session_id, TickRequest()))
    assert result2.tick == 2 and result2.encoded_rates_hz == {}
    assert result2.brain.stimulated_hz == {}
    assert runtime.get_session(info.session_id).ticks == 2

    # state / spikes / reset
    state = run(runtime.state(info.session_id))
    assert isinstance(state, BrainState) and state.step == 1000
    spikes = run(runtime.spikes(info.session_id, limit=50))
    assert spikes.count <= 50 and len(spikes.flywire_ids) == spikes.count
    assert all(fid in SYNTH_IDS for fid in spikes.flywire_ids)
    reset_info = run(runtime.reset(info.session_id))
    assert reset_info.ticks == 0 and reset_info.t_ms == 0.0
    assert run(runtime.state(info.session_id)).step == 0

    deleted = run(runtime.delete_session(info.session_id))
    assert deleted.status == "stopped"
    with pytest.raises(SessionNotFound):
        runtime.get_session(info.session_id)


def test_stimulate_and_silence_change_rates(runtime: FlyBrainRuntime):
    info = runtime.create_session(SessionConfig(plug="standalone", seed=3))
    sid = info.session_id
    state = run(runtime.stimulate(sid, [StimulusCommand(group="p9_right", rate_hz=100.0)]))
    assert state.stimulated_hz == {"p9_right": 100.0}
    result = run(runtime.tick(sid, TickRequest()))
    assert result.brain.rates_hz["p9_right"] > 0.0
    assert result.brain.rates_hz["p9_right_downstream"] > 0.0
    assert result.action.turn > 0.0  # right drive → right turn
    # manual stimulus persists across ticks (unlike encoded drive)
    assert result.brain.stimulated_hz == {"p9_right": 100.0}

    # silence p9_right: it still fires, its downstream goes quiet
    state = run(runtime.stimulate(sid, [StimulusCommand(group="p9_right", mode="silence")]))
    assert state.silenced == ["p9_right"]
    result = run(runtime.tick(sid, TickRequest()))
    assert result.brain.rates_hz["p9_right"] > 0.0
    assert result.brain.rates_hz["p9_right_downstream"] == 0.0
    assert result.brain.silenced == ["p9_right"]

    state = run(runtime.stimulate(sid, [StimulusCommand(group="p9_right", mode="unsilence")]))
    assert state.silenced == []
    result = run(runtime.tick(sid, TickRequest()))
    assert result.brain.rates_hz["p9_right_downstream"] > 0.0

    # clear removes the manual drive
    state = run(runtime.stimulate(sid, [StimulusCommand(group="p9_right", mode="clear")]))
    assert state.stimulated_hz == {}
    result = run(runtime.tick(sid, TickRequest()))
    assert result.brain.rates_hz["p9_right"] == 0.0

    # flywire ids path, with a missing id reported
    state = run(
        runtime.stimulate(sid, [StimulusCommand(flywire_ids=[SYNTH_IDS[5], 424242], rate_hz=50.0)])
    )
    assert "flywire_ids[2]" in state.stimulated_hz
    with pytest.raises(ValueError):
        run(runtime.stimulate(sid, [StimulusCommand(group="nope", rate_hz=10.0)]))


def test_tick_stimuli_and_subgraph_session(runtime: FlyBrainRuntime):
    from mycosoft_mas.flybrain.schemas import SubgraphSpec

    cfg = SessionConfig(
        plug="standalone",
        seed=1,
        subgraph=SubgraphSpec(seed_groups=["p9_left"], hops=1, min_weight=5.0, max_neurons=10),
    )
    info = runtime.create_session(cfg)
    assert info.subgraph is not None and info.n_neurons < N_SYNTH
    result = run(
        runtime.tick(
            info.session_id,
            TickRequest(stimuli=[StimulusCommand(group="p9_left", rate_hz=100.0)], act=False),
        )
    )
    assert result.plug_result == {"skipped": "act=false", "actuated": False}
    assert result.brain.rates_hz["p9_left_downstream"] > 0.0
    assert result.brain.subgraph["n_neurons"] == info.n_neurons
    # groups outside the subgraph are reported, never silently dropped
    assert "sugar_grn" not in result.brain.rates_hz
    res2 = run(
        runtime.tick(
            info.session_id,
            TickRequest(observations=[Observation(kind="raw_rates", payload={"sugar_grn": 50})]),
        )
    )
    assert any("sugar_grn" in n and "no neurons" in n for n in res2.notes)


# ---------------------------------------------------------------------------
# ITDX channel rows (spec §11.5)
# ---------------------------------------------------------------------------


def _brain(sid: str = "fb-test") -> BrainState:
    return BrainState(
        session_id=sid,
        t_ms=50.0,
        step=500,
        n_neurons=N_SYNTH,
        n_active=3,
        spike_count_window=40,
        window_ms=50.0,
        rates_hz={"p9_left": 100.0},
        backend="numpy",
    )


def test_itdx_channel_rows_not_supplied_without_nav_or_detections():
    rows = itdx_channel_rows(FORT_STEWART_SLICE, _brain(), MotorAction(), None, None)
    assert set(rows) == {"pathways", "navigation", "biology", "information"}
    for key, row in rows.items():
        assert row["status"] == "NOT_SUPPLIED", key
        assert row["p"] is None and row["agent_id"] == "flybrain"
        assert row["live"]["origin"] == "SIMULATED"
        assert row["live"]["session_id"] == "fb-test" and row["live"]["tick"] == 500
        assert row["reason"]
    infeasible = NavPath(
        feasible=False, note="goal cell is blocked", blocked_cells=5, total_cells=10
    )
    rows = itdx_channel_rows(FORT_STEWART_SLICE, _brain(), MotorAction(), infeasible, None)
    assert rows["navigation"]["status"] == "NOT_SUPPLIED"
    assert rows["navigation"]["reason"] == "goal cell is blocked"
    assert rows["pathways"]["status"] == "NOT_SUPPLIED"


def test_itdx_channel_rows_scored_with_feasible_nav_and_detections():
    center = GeoPoint(lat=31.8697, lon=-81.6072)
    grid = OccupancyGrid(center, size_m=200.0, cell_m=5.0)
    grid.add_point(31.8699, -81.6072, radius_m=10.0)
    goal = GeoPoint(lat=31.8703, lon=-81.6072)
    nav = plan(grid, center, goal, turn_bias=-0.3)
    assert nav.feasible and nav.blocked_cells > 0
    frame = DetectionFrame(
        engine="ultralytics",
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
    rows = itdx_channel_rows(
        FORT_STEWART_SLICE, _brain(), MotorAction(kind="locomotion", turn=-0.3), nav, frame
    )
    navr = rows["navigation"]
    assert navr["status"] == "SCORED"
    assert navr["p"] == pytest.approx(1.0 - nav.blocked_cells / nav.total_cells)
    assert "free-cell fraction" in navr["note"] and "not P(" in navr["note"]
    assert navr["live"]["blocked_cells"] == nav.blocked_cells
    pw = rows["pathways"]
    assert pw["status"] == "SCORED"
    assert pw["p"] == pytest.approx(min(1.0, len(nav.waypoints) / 12))
    assert pw["sample_count"] == len(nav.waypoints)
    bio = rows["biology"]
    assert bio["status"] == "SCORED" and bio["p"] == pytest.approx(0.5)
    assert bio["sample_count"] == 2
    inf = rows["information"]
    assert inf["status"] == "SCORED" and inf["sample_count"] == 2 and inf["p"] is None

    # detector ran but found nothing → biology NOT_SUPPLIED, information counts 0
    empty = DetectionFrame(engine="ultralytics", detections=[])
    rows = itdx_channel_rows(FORT_STEWART_SLICE, _brain(), MotorAction(), nav, empty)
    assert rows["biology"]["status"] == "NOT_SUPPLIED"
    assert rows["information"]["status"] == "SCORED" and rows["information"]["sample_count"] == 0
    # detector unavailable → both NOT_SUPPLIED with the detector's reason
    unavailable = DetectionFrame(available=False, note="ultralytics not importable")
    rows = itdx_channel_rows(FORT_STEWART_SLICE, _brain(), MotorAction(), nav, unavailable)
    assert rows["biology"]["status"] == "NOT_SUPPLIED"
    assert "ultralytics not importable" in rows["information"]["reason"]


def test_itdx_session_tick_and_channels_endpoint_helper(runtime: FlyBrainRuntime):
    cfg = SessionConfig(plug="itdx", seed=5, plug_config={"map_slice": FORT_STEWART_SLICE})
    info = runtime.create_session(cfg)
    result = run(
        runtime.tick(
            info.session_id,
            TickRequest(observations=[Observation(kind="raw_rates", payload={"p9_right": 100})]),
        )
    )
    assert isinstance(result.nav, NavPath)
    assert result.nav.feasible, result.nav.note
    assert 2 <= len(result.nav.waypoints) <= 12
    assert "drive side=right" in result.nav.note
    channels = result.plug_result["channels"]
    assert channels["navigation"]["status"] == "SCORED"
    assert channels["biology"]["status"] == "NOT_SUPPLIED"
    payload = runtime.itdx_channels(FORT_STEWART_SLICE, session_id=info.session_id)
    assert payload["channels"]["navigation"]["status"] == "SCORED"
    assert payload["nav"]["feasible"] is True and payload["session_id"] == info.session_id
    # tick is the session tick number; the engine step count is a separate key
    assert payload["tick"] == result.tick == 1
    assert payload["step"] == result.brain.step == 500
    for row in payload["channels"].values():
        assert row["live"]["tick"] == 1 and row["live"]["step"] == 500
        assert row["live"]["ao_source"] == "session plug map_slice"
        assert row["live"]["ao"] == "Fort Stewart"
    assert payload["ao_mismatch"] is None
    cold = runtime.itdx_channels(FORT_STEWART_SLICE)
    assert all(row["status"] == "NOT_SUPPLIED" for row in cold["channels"].values())
    assert cold["nav"] is None and cold["tick"] is None and cold["step"] is None
    assert cold["ao_source"] == "request map_slice"


def test_itdx_channels_session_rows_labelled_with_plug_slice(runtime: FlyBrainRuntime):
    """Regression: SCORED rows must carry the AO they were computed on, and a
    request for a different AO must not be answered with the session's numbers."""
    cfg = SessionConfig(plug="itdx", seed=5, plug_config={"map_slice": FORT_STEWART_SLICE})
    info = runtime.create_session(cfg)
    result = run(
        runtime.tick(
            info.session_id,
            TickRequest(observations=[Observation(kind="raw_rates", payload={"p9_right": 100})]),
        )
    )
    assert result.nav is not None and result.nav.feasible
    # request slice with a different AO name / bbox
    pendleton = {
        "ao": {
            "name": "Camp Pendleton",
            "bbox": [-117.6, 33.2, -117.2, 33.5],
            "center": {"lat": 33.38, "lon": -117.42},
        }
    }
    payload = runtime.itdx_channels(pendleton, session_id=info.session_id)
    assert payload["ao_mismatch"] and "different AO" in payload["ao_mismatch"]
    assert payload["nav"] is None
    for key in ("navigation", "pathways"):
        row = payload["channels"][key]
        assert row["status"] == "NOT_SUPPLIED" and row["p"] is None
        assert row["reason"] == payload["ao_mismatch"]
        assert row["live"]["ao"] == "Fort Stewart"  # never labelled with the request AO
        assert row["live"]["ao_source"] == "session plug map_slice"
    # same AO (name only, no geometry) → SCORED rows, labelled with the plug's slice
    same = runtime.itdx_channels({"ao": {"name": "fort stewart"}}, session_id=info.session_id)
    assert same["ao_mismatch"] is None
    assert same["channels"]["navigation"]["status"] == "SCORED"
    assert same["channels"]["navigation"]["live"]["ao"] == "Fort Stewart"
    # request without an ao never mismatches; a None slice is labelled from the plug
    assert runtime.itdx_channels(None, session_id=info.session_id)["ao_mismatch"] is None
    assert runtime.itdx_channels({}, session_id=info.session_id)["ao_mismatch"] is None
    # a standalone session has no plug slice → request slice labels the rows
    other = runtime.create_session(SessionConfig(plug="standalone", seed=1))
    run(runtime.tick(other.session_id, TickRequest()))
    cold = runtime.itdx_channels(pendleton, session_id=other.session_id)
    assert cold["ao_mismatch"] is None and cold["tick"] == 1
    assert cold["channels"]["navigation"]["live"]["ao"] == "Camp Pendleton"
    assert cold["channels"]["navigation"]["live"]["ao_source"].startswith("request map_slice")


def test_earthsim_session_plans_and_narrates(
    runtime: FlyBrainRuntime, monkeypatch: pytest.MonkeyPatch
):
    from mycosoft_mas.flybrain.plugs import earthsim as earthsim_mod

    monkeypatch.setattr(earthsim_mod, "devices_snapshot", lambda: {"devices": {}})

    async def _no_earth2():
        raise RuntimeError("earth2 router not reachable in tests")

    monkeypatch.setattr(earthsim_mod, "earth2_status", _no_earth2)
    cfg = SessionConfig(plug="earthsim", seed=9, plug_config={"map_slice": FORT_STEWART_SLICE})
    info = runtime.create_session(cfg)
    result = run(runtime.tick(info.session_id, TickRequest()))
    # the slice's assets drive the brain (earthsim encoder) → some encoded rate
    assert result.encoded_rates_hz
    assert isinstance(result.nav, NavPath) and result.nav.feasible, result.nav.note
    narration = result.plug_result["narration"]
    assert narration and narration[0].startswith("FlyBrain (SIMULATED)")
    assert any("Navigation: feasible path" in line for line in narration)
    assert any("Earth-2" in line and "not reachable" in line for line in narration)
    assert result.plug_result["actuated"] is False
    assert any("Earth-2 status unavailable" in n for n in result.notes)


# ---------------------------------------------------------------------------
# NLM plug (spec §11.4)
# ---------------------------------------------------------------------------


def test_nlm_envelope_validates_and_pipeline_flags_duplicate():
    from mycosoft_mas.nlm.formspace.contracts import ObservationEnvelope
    from mycosoft_mas.nlm.formspace.observation_pipeline import CausalObservationPipeline

    env = build_envelope("fb-abc", 3, {"p9_left": 12.5, "sugar_grn": 0.0, "bad": "x"}, t_ms=150.0)
    assert isinstance(env, ObservationEnvelope)
    assert env.schema_version == "formspace.observation/v1"
    assert env.chart_id == "flybrain.population_rates" and env.chart_version == "v1"
    assert env.subject_id == "fb-abc" and env.source_id == "flybrain"
    assert env.root_evidence_id == "flybrain:fb-abc:3"
    assert env.values == {"p9_left": 12.5, "sugar_grn": 0.0}
    assert env.units == {"p9_left": "Hz", "sugar_grn": "Hz"}
    assert env.observed_mask == {"p9_left": True, "sugar_grn": True}
    assert env.origin == "SYNTHETIC"
    assert env.provenance["origin"] == "SIMULATED"
    assert env.provenance["connectome"] == "flywire-783"
    assert env.provenance["model"] == "shiu2024-lif"
    ObservationEnvelope.model_validate(env.model_dump(mode="json"))

    pipeline = CausalObservationPipeline()
    first = pipeline.process(env, cutoff=env.available_at)
    assert first["status"] == "accepted" and first["consumed"] is True
    again = build_envelope("fb-abc", 3, {"p9_left": 99.0})
    second = pipeline.process(again, cutoff=again.available_at)
    assert second["status"] == "duplicate_root_evidence" and second["consumed"] is False
    third = pipeline.process(build_envelope("fb-abc", 4, {"p9_left": 1.0}), cutoff=env.available_at)
    assert third["status"] == "excluded_future_available_at"


def test_nlm_anomaly_none_until_five_ticks():
    tracker = RateAnomalyTracker()
    for i in range(5):
        res = tracker.evaluate({"a": 10.0 + i, "b": 1.0})
        assert res["score"] is None and res["n_history"] == i
    res = tracker.evaluate({"a": 12.0, "b": 1.0})
    assert res["score"] is not None and res["n_history"] == 5
    spike = tracker.evaluate({"a": 100.0, "b": 1.0})
    assert spike["score"] > res["score"] and spike["max_abs_z_group"] == "a"


def test_nlm_session_tick(runtime: FlyBrainRuntime, monkeypatch: pytest.MonkeyPatch):
    from mycosoft_mas.flybrain.plugs import nlm as nlm_mod
    from mycosoft_mas.nlm.formspace import observation_pipeline as pipe_mod

    monkeypatch.setattr(
        nlm_mod, "probe_nlm", lambda: {"model_loaded": False, "reason": "no weights in test"}
    )
    monkeypatch.setattr(pipe_mod, "_PIPELINE", None)
    info = runtime.create_session(SessionConfig(plug="nlm", seed=2))
    assert isinstance(runtime._session(info.session_id).plug, NLMPlug)
    result = run(runtime.tick(info.session_id, TickRequest()))
    pr = result.plug_result
    assert pr["nlm_qualification"] == "UNQUALIFIED"
    assert pr["pipeline_result"]["status"] == "accepted"
    assert pr["root_evidence_id"] == f"flybrain:{info.session_id}:1"
    assert pr["anomaly"]["score"] is None
    assert pr["forecast"]["support_status"] == "UNSUPPORTED"
    assert any("UNQUALIFIED" in n for n in result.notes)
    assert result.encoded_rates_hz == {}  # unloaded NLM never drives the brain
    for _ in range(5):
        result = run(runtime.tick(info.session_id, TickRequest()))
    assert result.plug_result["anomaly"]["score"] is not None
    payload = run(runtime.nlm_observation(info.session_id))
    assert payload["pipeline_result"]["status"] == "duplicate_root_evidence"
    assert payload["forecast"]["support_status"] == "UNSUPPORTED"


# ---------------------------------------------------------------------------
# Droid plug (spec §11.3 triple gate)
# ---------------------------------------------------------------------------


@pytest.fixture
def droid_guard(monkeypatch: pytest.MonkeyPatch):
    """Fail loudly if anything reaches the actuation helpers."""
    from mycosoft_mas.core.routers import psathyrella_api

    calls = {"save": 0, "camera": 0, "avani": 0}

    async def _boom_save(device_id, waypoints):
        calls["save"] += 1
        raise AssertionError("_save_waypoints must not be called")

    async def _boom_cmd(**kwargs):
        calls["camera"] += 1
        raise AssertionError("send_device_command must not be called")

    async def _telemetry(device_id):
        return {
            "gps": {"lat": 32.5629, "lon": -117.1357, "heading": 90.0, "sog": 1.2},
            "device_id": device_id,
        }

    monkeypatch.setattr(psathyrella_api, "_save_waypoints", _boom_save)
    from mycosoft_mas.core.routers import device_registry_api

    monkeypatch.setattr(device_registry_api, "send_device_command", _boom_cmd)
    monkeypatch.setattr(droid_mod, "get_device_telemetry", _telemetry)
    return calls


def test_droid_dry_run_never_actuates(runtime: FlyBrainRuntime, droid_guard, monkeypatch):
    async def _avani(*args, **kwargs):
        droid_guard["avani"] += 1
        return {"approved": True, "reason": "test"}

    monkeypatch.setattr(droid_mod, "evaluate_navigation_proposal", _avani)
    cfg = SessionConfig(
        plug="droid",
        seed=4,
        device_id="psathyrella-test",
        plug_config={"goal": {"lat": 32.5640, "lon": -117.1357}},
    )
    info = runtime.create_session(cfg)
    assert info.plug["gates"]["dry_run"] is True
    result = run(
        runtime.tick(
            info.session_id,
            TickRequest(observations=[Observation(kind="raw_rates", payload={"p9_left": 100})]),
        )
    )
    g = result.plug_result
    assert g["actuated"] is False and g["dry_run"] is True
    assert "dry_run" in g["reason"]
    assert g["avani"] is None and result.avani is None
    assert g["camera_point_at"]["bearing_deg"] == pytest.approx(
        (90.0 + g["heading_delta_deg"]) % 360.0
    )
    assert g["heading_delta_deg"] == pytest.approx(result.action.heading_delta_deg)
    assert result.nav is not None and result.nav.feasible, result.nav.note
    assert g["waypoints"] and g["waypoints"][-1]["note"] == "goal"
    assert droid_guard == {"save": 0, "camera": 0, "avani": 0}
    # telemetry drove the encoder: goal ~120 m north of the fix, heading east →
    # left turn drive (p9_left) and forward drive (both P9s via inputs.forward)
    kinds = [n for n in result.notes if n.startswith("droid:")]
    assert any("detections unavailable" in n for n in kinds)
    assert result.encoded_rates_hz["p9_left"] == 100.0
    assert 0.0 < result.encoded_rates_hz["p9_right"] <= 100.0


def test_droid_env_gate_blocks_without_flag(runtime: FlyBrainRuntime, droid_guard, monkeypatch):
    async def _avani(*args, **kwargs):
        droid_guard["avani"] += 1
        return {"approved": True, "reason": "test"}

    monkeypatch.setattr(droid_mod, "evaluate_navigation_proposal", _avani)
    monkeypatch.delenv("FLYBRAIN_DROID_ACTUATE", raising=False)
    cfg = SessionConfig(plug="droid", seed=4, dry_run=False, device_id="psathyrella-test")
    info = runtime.create_session(cfg)
    g = run(runtime.tick(info.session_id, TickRequest())).plug_result
    assert g["actuated"] is False and "FLYBRAIN_DROID_ACTUATE" in g["reason"]
    assert droid_guard["avani"] == 0 and droid_guard["save"] == 0


def test_droid_avani_denial_blocks(runtime: FlyBrainRuntime, droid_guard, monkeypatch):
    async def _deny(*args, **kwargs):
        droid_guard["avani"] += 1
        return {"approved": False, "reason": "season ceiling", "stage_failed": "season"}

    monkeypatch.setattr(droid_mod, "evaluate_navigation_proposal", _deny)
    monkeypatch.setenv("FLYBRAIN_DROID_ACTUATE", "1")
    cfg = SessionConfig(plug="droid", seed=4, dry_run=False, device_id="psathyrella-test")
    info = runtime.create_session(cfg)
    result = run(runtime.tick(info.session_id, TickRequest()))
    g = result.plug_result
    assert droid_guard["avani"] == 1
    assert g["actuated"] is False and "AVANI did not approve" in g["reason"]
    assert result.avani["approved"] is False and result.avani["reason"] == "season ceiling"
    assert droid_guard["save"] == 0 and droid_guard["camera"] == 0
    guidance = run(runtime.droid_guidance("psathyrella-test", info.session_id))
    # the read-only endpoint reports the tick's real values: session was dry_run=False
    assert guidance["dry_run"] is False and guidance["actuated"] is False
    assert guidance["session_dry_run"] is False and guidance["last_tick_actuated"] is False
    assert guidance["actuated_by_this_call"] is False
    assert "AVANI did not approve" in guidance["reason"]


def test_droid_guidance_reports_real_actuation_of_last_tick(
    runtime: FlyBrainRuntime, droid_guard, monkeypatch
):
    """Regression: after a tick that actually pushed waypoints/camera commands the
    guidance endpoint must not claim nothing was actuated / dry-run."""

    async def _avani(*args, **kwargs):
        droid_guard["avani"] += 1
        return {"approved": True, "reason": "test"}

    pushed = {"waypoints": 0, "camera": 0}

    async def _save(device_id, waypoints):
        pushed["waypoints"] += 1
        return {"ok": True, "count": len(waypoints)}

    async def _cam(device_id, bearing_deg):
        pushed["camera"] += 1
        return {"ok": True, "bearing_deg": bearing_deg}

    monkeypatch.setattr(droid_mod, "evaluate_navigation_proposal", _avani)
    monkeypatch.setattr(droid_mod, "save_waypoints", _save)
    monkeypatch.setattr(droid_mod, "point_camera", _cam)
    monkeypatch.setenv("FLYBRAIN_DROID_ACTUATE", "1")
    cfg = SessionConfig(
        plug="droid",
        seed=4,
        dry_run=False,
        device_id="psathyrella-test",
        plug_config={"goal": {"lat": 32.5640, "lon": -117.1357}},
    )
    info = runtime.create_session(cfg)
    result = run(
        runtime.tick(
            info.session_id,
            TickRequest(observations=[Observation(kind="raw_rates", payload={"p9_left": 100})]),
        )
    )
    assert result.plug_result["actuated"] is True and pushed["waypoints"] == 1
    guidance = run(runtime.droid_guidance("psathyrella-test", info.session_id))
    assert guidance["actuated"] is True and guidance["dry_run"] is False
    assert guidance["last_tick_actuated"] is True and guidance["session_dry_run"] is False
    assert guidance["actuated_by_this_call"] is False
    assert guidance["reason"] == "actuated: all three gates passed"
    assert "waypoints" in guidance["actuation"]
    assert "read-only" in guidance["endpoint_note"]
    assert guidance["tick"] == 1 and guidance["device_id"] == "psathyrella-test"
    # the guidance call itself pushed nothing
    assert pushed == {"waypoints": 1, "camera": 1}
    # no session → hold; not-yet-ticked / non-droid sessions carry the same call fields
    cold = run(runtime.droid_guidance("psathyrella-test"))
    assert cold["actuated_by_this_call"] is False and cold["last_tick_actuated"] is False
    other = runtime.create_session(SessionConfig(plug="standalone", seed=1, dry_run=False))
    fresh = run(runtime.droid_guidance("psathyrella-test", other.session_id))
    assert fresh["tick"] == 0 and fresh["session_dry_run"] is False
    assert fresh["dry_run"] is False and fresh["actuated_by_this_call"] is False


def test_droid_telemetry_unavailable_is_a_note(runtime: FlyBrainRuntime, monkeypatch):
    async def _fail(device_id):
        raise RuntimeError("Device not found: " + device_id)

    monkeypatch.setattr(droid_mod, "get_device_telemetry", _fail)
    info = runtime.create_session(SessionConfig(plug="droid", seed=4, device_id="ghost-device"))
    result = run(runtime.tick(info.session_id, TickRequest()))
    assert any("telemetry unavailable for ghost-device" in n for n in result.notes)
    g = result.plug_result
    assert g["telemetry_ok"] is False and g["camera_point_at"] is None
    assert g["actuated"] is False and g["waypoints"] == []


# ---------------------------------------------------------------------------
# Health / atlas / autopilot
# ---------------------------------------------------------------------------


def test_health_without_connectome_is_unavailable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setenv("FLYBRAIN_DATA_DIR", str(empty))
    monkeypatch.setenv("FLYBRAIN_BACKEND", "numpy")
    monkeypatch.delenv("FLYBRAIN_REMOTE_DETECTOR_URL", raising=False)
    monkeypatch.delenv("PSATHYRELLA_CAM_DETECT_URL", raising=False)
    reset_connectome_cache()
    set_detector_for_tests(None)
    rt = reset_runtime_for_tests()
    health = rt.health()
    assert health.status == "unavailable"
    assert health.connectome.loaded is False
    assert "flybrain_fetch_connectome.py" in health.connectome.reason
    assert health.connectome.data_dir == str(empty)
    assert health.backend == "numpy"
    assert health.sessions == 0 and health.autopilots == 0
    assert set(health.plugs) == set(PLUG_REGISTRY)
    assert health.vision.available in (True, False)  # honest either way
    summary = rt.atlas_summary()
    assert summary.connectome_loaded is False
    assert summary.source["n_groups"] > 0
    set_detector_for_tests(None)


def test_health_with_pinned_synthetic_connectome(runtime: FlyBrainRuntime):
    health = runtime.health()
    assert health.connectome.loaded is True
    assert health.connectome.n_neurons == N_SYNTH
    assert health.connectome.sha256_ok is None  # in-memory fixture: nothing to verify
    assert health.status in ("healthy", "degraded")
    summary = runtime.atlas_summary()
    assert summary.connectome_loaded is True
    ghost = next(g for g in summary.groups if g["name"] == "ghost")
    assert ghost["missing_ids"] == [999_999]


def test_session_limit_counts_creates_in_flight(runtime: FlyBrainRuntime, monkeypatch):
    """Regression: concurrent create_session calls must not exceed FLYBRAIN_MAX_SESSIONS
    while engines are still being built (the cap used to be a TOCTOU)."""
    import threading

    from mycosoft_mas.flybrain import runtime as runtime_mod
    from mycosoft_mas.flybrain.runtime import SessionLimitReached

    real_engine = runtime_mod.FlyBrainEngine

    class SlowEngine(real_engine):  # type: ignore[misc,valid-type]
        def __init__(self, *args, **kwargs):
            time.sleep(0.25)  # widen the build window so the threads overlap
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(runtime_mod, "FlyBrainEngine", SlowEngine)
    runtime.settings.max_sessions = 2
    outcomes = []
    lock = threading.Lock()

    def worker():
        try:
            runtime.create_session(SessionConfig(plug="standalone", seed=1))
            res = "ok"
        except SessionLimitReached:
            res = "limit"
        with lock:
            outcomes.append(res)

    threads = [threading.Thread(target=worker) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(outcomes) == ["limit"] * 4 + ["ok"] * 2
    assert len(runtime.list_sessions()) == 2
    assert runtime.pending_sessions() == 0
    # a failed build releases its reservation
    monkeypatch.setattr(runtime_mod, "FlyBrainEngine", real_engine)
    runtime.settings.max_sessions = 3
    monkeypatch.setattr(
        runtime_mod, "get_plug", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    with pytest.raises(RuntimeError):
        runtime.create_session(SessionConfig(plug="standalone", seed=1))
    assert runtime.pending_sessions() == 0 and len(runtime.list_sessions()) == 2


def test_record_cap_stops_recording_and_reports_it(
    runtime: FlyBrainRuntime, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("FLYBRAIN_RECORD_MAX_TICKS", "2")
    info = runtime.create_session(SessionConfig(plug="standalone", seed=7, window_ms=10.0))
    rec_status = runtime.get_session(info.session_id).plug["recording"]
    assert rec_status["active"] is True and rec_status["max_ticks"] == 2
    sid = info.session_id
    r1 = run(runtime.tick(sid, TickRequest()))
    r2 = run(runtime.tick(sid, TickRequest()))
    assert not any(n.startswith("recording stopped") for n in r1.notes + r2.notes)
    r3 = run(runtime.tick(sid, TickRequest()))
    assert any("recording stopped" in n and "MAX_TICKS=2" in n for n in r3.notes)
    r4 = run(runtime.tick(sid, TickRequest()))
    assert not any("recording stopped" in n for n in r4.notes)  # reported once
    rec = Path(os.environ["FLYBRAIN_RECORD_DIR"]) / sid / "ticks.jsonl"
    lines = rec.read_text(encoding="utf-8").strip().splitlines()
    assert [json.loads(line)["tick"] for line in lines] == [1, 2]
    status = runtime.get_session(sid).plug["recording"]
    assert status["active"] is False and status["ticks"] == 2
    assert status["bytes"] == sum(len(line.encode("utf-8")) + 1 for line in lines)
    assert "MAX_TICKS=2" in status["stopped_reason"]
    # byte cap
    monkeypatch.delenv("FLYBRAIN_RECORD_MAX_TICKS", raising=False)
    monkeypatch.setenv("FLYBRAIN_RECORD_MAX_BYTES", "10")
    info2 = runtime.create_session(SessionConfig(plug="standalone", seed=7, window_ms=10.0))
    r = run(runtime.tick(info2.session_id, TickRequest()))
    assert any("MAX_BYTES=10" in n for n in r.notes)
    assert not (Path(os.environ["FLYBRAIN_RECORD_DIR"]) / info2.session_id / "ticks.jsonl").exists()
    # record=False sessions never get a recording entry
    info3 = runtime.create_session(SessionConfig(plug="standalone", seed=7, record=False))
    assert "recording" not in runtime.get_session(info3.session_id).plug


def test_autopilot_period_change_applies_to_running_loop(runtime: FlyBrainRuntime):
    async def scenario():
        info = runtime.create_session(SessionConfig(plug="standalone", seed=11, window_ms=10.0))
        sid = info.session_id
        await runtime.set_autopilot(sid, True, period_s=0.2)
        task = runtime._session(sid).autopilot_task
        await asyncio.sleep(0.5)
        assert runtime.get_session(sid).ticks >= 2
        # slow it down without restarting the task
        info = await runtime.set_autopilot(sid, True, period_s=5.0)
        assert info.autopilot is True and runtime._session(sid).autopilot_task is task
        assert runtime._session(sid).autopilot_period_s == pytest.approx(5.0)
        await asyncio.sleep(0.25)  # let the in-flight 0.2 s sleep finish
        ticks = runtime.get_session(sid).ticks
        await asyncio.sleep(0.7)
        assert runtime.get_session(sid).ticks == ticks  # 5 s period: no more ticks yet
        await runtime.set_autopilot(sid, False)

    run(scenario())


def test_autopilot_start_stop(runtime: FlyBrainRuntime):
    async def scenario():
        info = runtime.create_session(SessionConfig(plug="standalone", seed=11, window_ms=20.0))
        sid = info.session_id
        started = await runtime.set_autopilot(sid, True, period_s=0.01)  # clamped to 0.2 s
        assert started.autopilot is True
        assert runtime._session(sid).autopilot_period_s == pytest.approx(0.2)
        await asyncio.sleep(0.55)
        mid = runtime.get_session(sid)
        assert mid.ticks >= 2 and mid.autopilot is True
        assert runtime.health().autopilots == 1
        stopped = await runtime.set_autopilot(sid, False)
        assert stopped.autopilot is False
        ticks = runtime.get_session(sid).ticks
        await asyncio.sleep(0.3)
        assert runtime.get_session(sid).ticks == ticks  # no more ticks after stop
        # restart, then delete cancels it
        await runtime.set_autopilot(sid, True, period_s=0.2)
        await asyncio.sleep(0.05)
        deleted = await runtime.delete_session(sid)
        assert deleted.status == "stopped" and deleted.autopilot is False
        assert runtime.autopilot_count() == 0

    run(scenario())


# ---------------------------------------------------------------------------
# Real FlyWire data (skipped unless FLYBRAIN_DATA_DIR holds the files)
# ---------------------------------------------------------------------------


@requires_real_data
def test_real_full_brain_standalone_tick(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("FLYBRAIN_RECORD_DIR", str(tmp_path / "records"))
    monkeypatch.setenv("FLYBRAIN_BACKEND", "numpy")
    monkeypatch.delenv("FLYBRAIN_ATLAS_PATH", raising=False)
    reset_connectome_cache()
    rt = reset_runtime_for_tests()
    t0 = time.perf_counter()
    info = rt.create_session(SessionConfig(plug="standalone", seed=42, window_ms=50.0))
    t_create = time.perf_counter() - t0
    assert info.n_neurons == 138_639
    assert info.n_synapses > 10_000_000
    req = TickRequest(
        observations=[Observation(kind="raw_rates", payload={"p9_left": 100.0, "p9_right": 100.0})]
    )
    t1 = time.perf_counter()
    result = run(rt.tick(info.session_id, req))
    t_tick = time.perf_counter() - t1
    print(
        f"\nreal-data: create {t_create:.2f}s, 50 ms tick {t_tick:.2f}s "
        f"(wall_ms={result.wall_ms:.0f}, realtime_ratio={result.brain.realtime_ratio}), "
        f"spikes in window={result.brain.spike_count_window}, "
        f"fwd={result.brain.rates_hz.get('p9_shared_downstream')}"
    )
    assert result.brain.n_neurons == 138_639
    assert result.brain.rates_hz["p9_left"] > 0.0 and result.brain.rates_hz["p9_right"] > 0.0
    assert result.wall_ms < 30_000
    health = rt.health()
    assert health.connectome.loaded is True and health.connectome.n_neurons == 138_639
    run(rt.close())
    reset_connectome_cache()
