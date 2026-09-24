"""Tests for the FlyBrain connectome loader, atlas and LIF engine (spec §1, §4, §5).

All tests run on an explicit in-memory synthetic connectome (a test fixture,
not production data). The real-data test is skipped unless
``FLYBRAIN_DATA_DIR`` points at a directory containing
``2025_Completeness_783.csv`` and ``2025_Connectivity_783.npz``.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest

from mycosoft_mas.flybrain.atlas import Atlas
from mycosoft_mas.flybrain.connectome import (
    Connectome,
    ConnectomeUnavailable,
    get_connectome,
    reset_connectome_cache,
    set_cached_connectome,
)
from mycosoft_mas.flybrain.model import (
    BackendUnavailable,
    FlyBrainEngine,
    LIFParams,
    resolve_backend,
    torch_available,
)
from mycosoft_mas.flybrain.schemas import AtlasSummary, ConnectomeManifest, SubgraphSpec

N_SYNTH = 60
SYNTH_IDS = [10_000 + i for i in range(N_SYNTH)]  # deliberately NOT FlyWire ids

# Synthetic circuit (indices into SYNTH_IDS):
#   0 -> 1   strong excitation (w=+1000)
#   2 -> 3   moderate excitation (w=+40)
#   4 -> 3   inhibition (w=-40)
#   5 -> 6 -> 7  two-hop chain (w=+400 each)
#   8 -> 9   weak (w=+2) -- filtered out by min_weight=5 in subgraph tests
SYNTH_PRE = [0, 2, 4, 5, 6, 8]
SYNTH_POST = [1, 3, 3, 6, 7, 9]
SYNTH_W = [1000.0, 40.0, -40.0, 400.0, 400.0, 2.0]


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


@pytest.fixture
def synth() -> Connectome:
    return Connectome.from_arrays(SYNTH_IDS, SYNTH_PRE, SYNTH_POST, SYNTH_W)


@pytest.fixture(autouse=True)
def _clean_cache():
    reset_connectome_cache()
    yield
    reset_connectome_cache()


# ---------------------------------------------------------------------------
# Connectome
# ---------------------------------------------------------------------------


def test_from_arrays_shapes_and_lookup(synth: Connectome):
    assert synth.n_neurons == N_SYNTH
    assert synth.n_synapses == len(SYNTH_PRE)
    assert synth.csc.shape == (N_SYNTH, N_SYNTH)
    assert synth.csc.dtype == np.float32
    assert synth.flywire_ids.dtype == np.int64
    # csc is (post, pre): column 0 lists the targets of neuron 0
    assert synth.csc[:, 0].indices.tolist() == [1]
    assert synth.csc[1, 0] == pytest.approx(1000.0)
    assert synth.csr[3, :].indices.tolist() == [2, 4]
    assert synth.id_to_index[SYNTH_IDS[7]] == 7
    found, missing = synth.indices_for_ids([SYNTH_IDS[3], 1, 2])
    assert found == [3] and missing == [1, 2]
    assert synth.downstream([5], min_weight=5).tolist() == [6]
    assert synth.upstream([3]).tolist() == [2, 4]


def test_from_arrays_sums_duplicates_and_validates():
    c = Connectome.from_arrays([1, 2], [0, 0], [1, 1], [3.0, 4.0])
    assert c.n_synapses == 1
    assert c.csc[1, 0] == pytest.approx(7.0)
    with pytest.raises(ValueError):
        Connectome.from_arrays([1, 2], [0, 5], [1, 1], [1.0, 1.0])


def test_manifest_for_in_memory_connectome(synth: Connectome):
    m = synth.manifest()
    assert isinstance(m, ConnectomeManifest)
    assert m.loaded is True
    assert m.n_neurons == N_SYNTH
    assert m.sha256_ok is None  # nothing on disk to verify -- never a fake green
    assert "in-memory" in m.reason


def test_load_missing_dir_raises_with_fetch_hint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    with pytest.raises(ConnectomeUnavailable) as exc:
        Connectome.load(tmp_path)
    assert "flybrain_fetch_connectome.py" in str(exc.value)
    # Isolate the default-settings path from the host env: FLYBRAIN_DATA_DIR may point
    # at the real FlyWire files (the configuration the @requires_real_data tests need).
    monkeypatch.setenv("FLYBRAIN_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("FLYBRAIN_ATLAS_PATH", raising=False)
    with pytest.raises(ConnectomeUnavailable):
        get_connectome()  # default settings now resolve to the empty tmp_path


def test_load_from_npz_written_to_disk(tmp_path: Path):
    """Round-trip the on-disk format with numpy only (CSV header ',Completed')."""
    csv = tmp_path / "2025_Completeness_783.csv"
    csv.write_text(",Completed\n" + "".join(f"{fid},True\n" for fid in SYNTH_IDS), encoding="utf-8")
    np.savez(
        tmp_path / "2025_Connectivity_783.npz",
        pre=np.asarray(SYNTH_PRE, dtype=np.int32),
        post=np.asarray(SYNTH_POST, dtype=np.int32),
        weight=np.asarray(SYNTH_W, dtype=np.float32),
        n_neurons=np.int64(N_SYNTH),
        source_sha256=np.str_("0" * 64),
    )
    c = Connectome.load(tmp_path)
    assert c.n_neurons == N_SYNTH and c.n_synapses == len(SYNTH_PRE)
    assert c.csc[1, 0] == pytest.approx(1000.0)
    m = c.manifest()
    assert m.loaded and m.sha256_ok is False  # synthetic files never match FlyWire hashes
    assert "2025_Completeness_783.csv" in m.sha256
    assert m.connectivity_path is not None and m.connectivity_path.endswith(".npz")
    # process-wide cache
    from mycosoft_mas.flybrain.config import FlyBrainSettings

    settings = FlyBrainSettings(data_dir=tmp_path, atlas_path=tmp_path / "atlas.yaml")
    c1 = get_connectome(settings)
    assert get_connectome(settings) is c1
    reset_connectome_cache()
    assert get_connectome(settings) is not c1


def test_set_cached_connectome_pins_fixture(synth: Connectome, tmp_path: Path):
    from mycosoft_mas.flybrain.config import FlyBrainSettings

    empty = FlyBrainSettings(data_dir=tmp_path, atlas_path=tmp_path / "atlas.yaml")
    set_cached_connectome(synth)
    assert get_connectome(empty) is synth  # pinned fixture wins regardless of data_dir
    reset_connectome_cache()
    with pytest.raises(ConnectomeUnavailable):
        get_connectome(empty)


# ---------------------------------------------------------------------------
# Engine dynamics (synthetic 60-neuron fixture)
# ---------------------------------------------------------------------------


def test_backend_resolution_without_torch_is_numpy():
    assert resolve_backend("numpy") == "numpy"
    assert resolve_backend("auto") in {"numpy", "torch:cuda"}
    if not torch_available():
        assert resolve_backend("auto") == "numpy"
        with pytest.raises(BackendUnavailable):
            resolve_backend("torch")
    with pytest.raises(ValueError):
        resolve_backend("brian2")


def test_lif_params_published_defaults():
    p = LIFParams()
    assert (p.tau_syn_ms, p.t_delay_ms, p.tau_mem_ms, p.t_refrac_ms) == (5.0, 1.8, 20.0, 2.2)
    assert (p.v0_mv, p.v_reset_mv, p.v_rest_mv, p.v_threshold_mv) == (-52, -52, -52, -45)
    assert (p.scale_poisson, p.w_scale_mv) == (250, 0.275)
    assert p.steps_delay(0.1) == 18
    assert p.refrac_steps(0.1) == 22
    assert p.stim_mv == pytest.approx(68.75)


def test_driven_neuron_spikes_at_poisson_rate(synth: Connectome):
    """(1) An isolated driven neuron fires at ~bernoulli(rate*dt/1000) per step."""
    engine = FlyBrainEngine(synth, seed=123, backend="numpy")
    assert engine.backend == "numpy"
    target = 20  # no synapses at all
    rate = 200.0
    duration = 2000.0
    engine.set_rates([target], rate)
    times, idx = engine.run(duration)
    n = int((idx == target).sum())
    expected = rate * duration / 1000.0  # 400
    sigma = np.sqrt(expected)
    assert abs(n - expected) < 4 * sigma, (n, expected)
    assert engine.mean_rates([target], duration) == pytest.approx(n / (duration / 1000.0))
    # nothing else fired
    assert set(np.unique(idx).tolist()) == {target}
    assert engine.t_ms == pytest.approx(duration)
    assert engine.step_count == 20000


def test_strong_excitatory_synapse_respects_delay(synth: Connectome):
    """(2) 0 -> 1 with w=1000: 1 spikes shortly after 0, never before ~1.8 ms."""
    engine = FlyBrainEngine(synth, seed=7, backend="numpy")
    engine.set_rates([0], 100.0)
    times, idx = engine.run(500.0)
    t_pre = times[idx == 0]
    t_post = times[idx == 1]
    assert t_pre.size > 20
    assert t_post.size > 10
    assert t_post[0] - t_pre[0] >= 1.8 - 1e-9
    assert t_post[0] - t_pre[0] <= 4.0
    # every post spike is preceded by a pre spike at least 1.8 ms earlier
    for tp in t_post:
        earlier = t_pre[t_pre <= tp - 1.8 + 1e-9]
        assert earlier.size > 0, tp
    # and no post spike happens before the first pre spike
    assert t_post.min() > t_pre.min()


def test_synaptic_delay_matches_brian2_timing():
    """Regression: a pre spike at step s reaches g at s+18 and first moves v at s+19.

    Brian2 (ground truth) delivers ``g += w`` at spike+18 and integrates it into
    ``v`` at spike+19, so the earliest post-synaptic spike is 1.9 ms after the
    pre spike (dt = 0.1 ms). A 2-neuron probe with a huge weight makes the
    post neuron cross threshold on the very first step v moves.
    """
    conn = Connectome.from_arrays([1, 2], [0], [1], [100_000.0])
    engine = FlyBrainEngine(conn, seed=0, backend="numpy")
    core = engine._core
    assert core.steps_delay == 18
    assert core.ring_slots == 17
    # force neuron 0 above threshold so it spikes deterministically at step 5
    pre_step = 5
    g_first = post_step = None
    for k in range(0, 40):
        if k == pre_step:
            core.v[0] = 0.0
        spk = engine.step()
        if k == pre_step:
            assert spk.tolist() == [0]
        if g_first is None and float(core.g[1]) != 0.0:
            g_first = k
        if post_step is None and 1 in spk.tolist():
            post_step = k
    assert g_first == pre_step + 18, g_first
    # v first integrates g at s+19; with this weight it crosses threshold (and is
    # reset) on that same step, so the post spike is the observable v movement.
    assert post_step == pre_step + 19, post_step


def test_earliest_post_synaptic_spike_latency_is_1_9_ms():
    """Public-API pin of the delay: first post spike exactly 1.9 ms after the first pre spike."""
    conn = Connectome.from_arrays([1, 2], [0], [1], [100_000.0])
    engine = FlyBrainEngine(conn, seed=3, backend="numpy")
    engine.set_rates([0], 500.0)
    times, idx = engine.run(200.0)
    t_pre = times[idx == 0]
    t_post = times[idx == 1]
    assert t_pre.size > 0 and t_post.size > 0
    assert t_post[0] - t_pre[0] == pytest.approx(1.9, abs=1e-9)


def test_set_rates_pairs_rates_with_unsorted_indices(synth: Connectome):
    """Regression: per-index rates follow the caller's order, not np.unique order."""
    engine = FlyBrainEngine(synth, seed=1, backend="numpy")
    engine.set_rates([5, 2], [100.0, 200.0])
    assert engine.rates == {5: 100.0, 2: 200.0}
    core = engine._core
    assert core.driven_idx.tolist() == [2, 5]
    assert core.driven_p.tolist() == pytest.approx([0.02, 0.01])
    # duplicates: last write wins, no broadcast error
    engine.set_rates([3, 3], [10.0, 20.0])
    assert engine.rates[3] == 20.0
    # a zero rate in per-index form removes only that neuron
    engine.set_rates([5, 2], [0.0, 250.0])
    assert engine.rates == {2: 250.0, 3: 20.0}
    # scalar rate still broadcasts; range check still applies
    engine.set_rates([7, 6], 50.0)
    assert engine.rates[6] == 50.0 and engine.rates[7] == 50.0
    with pytest.raises(IndexError):
        engine.set_rates([0, N_SYNTH], [1.0, 2.0])
    with pytest.raises(ValueError):
        engine.set_rates([0], -1.0)


def test_inhibitory_synapse_reduces_target_firing(synth: Connectome):
    """(3) 2 -> 3 (+40) drives 3; adding 4 -> 3 (-40) at the same rate lowers 3's rate."""
    exc_only = FlyBrainEngine(synth, seed=11, backend="numpy")
    exc_only.set_rates([2], 200.0)
    _, idx_a = exc_only.run(1000.0)
    n_exc = int((idx_a == 3).sum())

    with_inh = FlyBrainEngine(synth, seed=11, backend="numpy")
    with_inh.set_rates([2], 200.0)
    with_inh.set_rates([4], 200.0)
    _, idx_b = with_inh.run(1000.0)
    n_inh = int((idx_b == 3).sum())

    assert n_exc > 10
    assert n_inh < n_exc / 2, (n_exc, n_inh)


def test_silence_stops_propagation(synth: Connectome):
    """(4) silence(pre) zeroes its outgoing synapses; unsilence restores them."""
    engine = FlyBrainEngine(synth, seed=3, backend="numpy")
    engine.set_rates([0], 200.0)
    engine.silence([0])
    assert engine.silenced == [0]
    _, idx = engine.run(500.0)
    assert (idx == 0).sum() > 50  # the silenced neuron itself still fires
    assert (idx == 1).sum() == 0  # but nothing propagates
    engine.unsilence([0])
    assert engine.silenced == []
    _, idx2 = engine.run(500.0)
    assert (idx2 == 1).sum() > 10


def test_refractory_period_for_undriven_neuron(synth: Connectome):
    """(5) 1 is hammered by 0 (w=1000 @ 2000 Hz) but never spikes twice within 2.2 ms."""
    engine = FlyBrainEngine(synth, seed=5, backend="numpy")
    engine.set_rates([0], 2000.0)
    times, idx = engine.run(500.0)
    t_post = times[idx == 1]
    assert t_post.size > 50
    isi = np.diff(t_post)
    assert isi.min() >= 2.2 - 1e-9, isi.min()
    # driven neurons have no refractory period (refrac_steps = 0)
    t_pre = times[idx == 0]
    assert np.diff(t_pre).min() < 2.2


def test_reset_restores_time_zero_and_is_reproducible(synth: Connectome):
    """(6) reset() -> t=0, empty history; a seeded run repeats exactly."""
    engine = FlyBrainEngine(synth, seed=42, backend="numpy")
    engine.set_rates([0, 2], 150.0)
    t1, i1 = engine.run(300.0)
    assert engine.t_ms == pytest.approx(300.0)
    engine.reset()
    assert engine.t_ms == 0.0 and engine.step_count == 0
    assert engine.history.total == 0 and engine.total_spikes == 0
    assert engine.recent_spikes(10)[0].size == 0
    assert engine.rates == {0: 150.0, 2: 150.0}  # stimuli kept by default
    assert np.all(engine.voltages() == np.float32(-52.0))
    t2, i2 = engine.run(300.0)
    assert np.array_equal(t1, t2) and np.array_equal(i1, i2)
    engine.reset(keep_stimuli=False)
    assert engine.rates == {} and engine.silenced == []
    _, i3 = engine.run(100.0)
    assert i3.size == 0  # silent brain without drive


def test_spike_history_ring_and_window_rates(synth: Connectome):
    engine = FlyBrainEngine(synth, seed=9, backend="numpy", spike_history_cap=50)
    engine.set_rates([20, 21], 500.0)
    engine.run(1000.0)
    assert engine.history.total <= 50
    assert engine.history.dropped > 0
    t, i = engine.recent_spikes(10)
    assert t.size == 10 and i.size == 10
    assert np.all(np.diff(t) >= 0)
    snap = engine.snapshot(window_ms=20.0)
    assert snap["n_neurons"] == N_SYNTH
    assert snap["backend"] == "numpy"
    assert snap["spike_count_window"] >= 0
    assert snap["n_active"] <= 2
    assert engine.mean_rates([], 20.0) == 0.0
    assert engine.mean_rates(None, 1000.0) >= 0.0
    with pytest.raises(IndexError):
        engine.set_rates([N_SYNTH + 5], 10.0)
    with pytest.raises(ValueError):
        engine.set_rates([1], -1.0)


def test_subgraph_mapping_round_trips(synth: Connectome):
    """(7) Subgraph extraction + local/global maps."""
    local_csc, l2g = synth.subgraph([5], hops=2, min_weight=5.0, max_neurons=100)
    assert l2g.tolist() == [5, 6, 7]
    assert local_csc.shape == (3, 3) and local_csc.nnz == 2
    # weak synapse 8->9 (w=2) is below min_weight: 8 is isolated at min_weight=5
    _, l2g_weak = synth.subgraph([8], hops=1, min_weight=5.0, max_neurons=100)
    assert l2g_weak.tolist() == [8]
    _, l2g_weak2 = synth.subgraph([8], hops=1, min_weight=0.0, max_neurons=100)
    assert l2g_weak2.tolist() == [8, 9]
    # backward reach: 3's presynaptic partners 2 and 4
    _, l2g_back = synth.subgraph([3], hops=1, min_weight=1.0, max_neurons=100)
    assert l2g_back.tolist() == [2, 3, 4]
    # cap keeps seeds and the heaviest neighbours
    _, l2g_cap = synth.subgraph([3], hops=1, min_weight=1.0, max_neurons=2)
    assert l2g_cap.size == 2 and 3 in l2g_cap.tolist()

    engine = FlyBrainEngine(synth, seed=1, backend="numpy", subgraph=(local_csc, l2g))
    assert engine.is_subgraph and engine.n_neurons == 3 and engine.n_synapses == 2
    assert engine.to_global([0, 1, 2]).tolist() == [5, 6, 7]
    assert engine.to_local([5, 6, 7]).tolist() == [0, 1, 2]
    assert engine.to_local(engine.to_global([2, 0])).tolist() == [2, 0]
    assert engine.missing_from_subgraph([5, 30]).tolist() == [30]
    assert engine.to_local([30]).size == 0
    assert engine.flywire_ids([0]) == [SYNTH_IDS[5]]
    # the chain still works inside the subgraph
    engine.set_rates(engine.to_local([5]), 200.0)
    _, idx = engine.run(500.0)
    assert (idx == 2).sum() > 5  # local index 2 == global 7, two hops away
    assert engine.snapshot()["subgraph"]["n_neurons"] == 3

    # SubgraphSpec needs seeds
    with pytest.raises(ValueError):
        FlyBrainEngine(synth, subgraph=SubgraphSpec(seed_groups=["nope"]))
    spec_engine = FlyBrainEngine(
        synth, subgraph=SubgraphSpec(seed_groups=[], hops=1, min_weight=1.0), seed_indices=[0]
    )
    assert spec_engine.to_global([0, 1]).tolist() == [0, 1]
    assert spec_engine.subgraph_info["n_neurons"] == 2

    # full-brain mode: identity maps
    full = FlyBrainEngine(synth, backend="numpy")
    assert not full.is_subgraph
    assert full.to_global([4]).tolist() == [4] and full.to_local([4]).tolist() == [4]


# ---------------------------------------------------------------------------
# Atlas
# ---------------------------------------------------------------------------


def test_atlas_resolves_derives_and_lists_missing(synth: Connectome, tmp_path: Path):
    """(8) Real YAML against the synthetic connectome: every FlyWire id is missing
    (listed, not dropped); a custom YAML with synthetic ids derives groups."""
    atlas = Atlas.load(connectome=synth)
    assert atlas.connectome_loaded
    sugar = atlas.group("sugar_grn")
    assert sugar.role == "sensory"
    assert len(sugar.flywire_ids) == 21
    assert sugar.indices == []
    assert sorted(sugar.missing_ids) == sorted(sugar.flywire_ids)
    assert atlas.group("sugar_downstream").derived is True
    assert atlas.group("sugar_downstream").indices == []
    assert atlas.indices(["p9_left", "p9_right"]) == []
    assert atlas.input_groups("attract") == ["sugar_grn"]
    assert atlas.readout_groups("turn_left") == ["p9_left_downstream"]
    summary = atlas.summary()
    assert isinstance(summary, AtlasSummary)
    assert summary.connectome_loaded is True
    assert summary.source["total_missing_ids"] > 0
    assert summary.sensorimotor["inputs"]["attract"]["size"] == 0
    assert summary.sensorimotor["unresolved_group_refs"] == []
    with pytest.raises(KeyError):
        atlas.group("does_not_exist")

    # without a connectome: configuration only, honest flags
    bare = Atlas.load()
    assert not bare.connectome_loaded
    assert bare.group("sugar_grn").indices == [] and bare.group("sugar_grn").missing_ids == []
    assert bare.summary().connectome_loaded is False

    # custom atlas with synthetic ids: derived groups come from the csc
    yaml_text = f"""
schema_version: flybrain.atlas/v1
groups:
  src:
    role: sensory
    flywire_ids: [{SYNTH_IDS[5]}, 999]
  src_b:
    role: sensory
    flywire_ids: [{SYNTH_IDS[2]}, {SYNTH_IDS[4]}]
  weak:
    flywire_ids: [{SYNTH_IDS[8]}]
derived:
  one_hop:
    downstream_of: [src]
    hops: 1
    min_weight: 5
  two_hop:
    downstream_of: [src]
    hops: 2
    min_weight: 5
    exclude: [one_hop]
  shared:
    downstream_of: [src_b]
    hops: 1
    intersection: true
  both:
    downstream_of: [src, src_b]
    hops: 1
    intersection: true
  weak_down:
    downstream_of: [weak]
    hops: 1
    min_weight: 5
sensorimotor:
  inputs: {{forward: [src], left: [], right: [], attract: []}}
  readouts: {{forward: [one_hop], turn_left: [two_hop], turn_right: [], feeding: [missing_group]}}
"""
    path = tmp_path / "atlas.yaml"
    path.write_text(yaml_text, encoding="utf-8")
    custom = Atlas.load(path, connectome=synth)
    assert custom.group("src").indices == [5]
    assert custom.group("src").missing_ids == [999]
    assert custom.group("src").role == "sensory"
    assert custom.group("weak").role == "custom"
    assert custom.group("one_hop").indices == [6]
    assert custom.group("one_hop").flywire_ids == [SYNTH_IDS[6]]
    assert custom.group("two_hop").indices == [7]  # 6 excluded via one_hop
    assert custom.group("shared").indices == [3]  # union within one seed group
    assert custom.group("both").indices == []  # intersection of {6} and {3}
    assert custom.group("weak_down").indices == []  # w=2 < min_weight
    assert custom.readout_indices("forward") == [6]
    assert custom.input_indices("forward") == [5]
    assert custom.summary().sensorimotor["unresolved_group_refs"] == [
        "readouts.feeding:missing_group"
    ]
    assert custom.group_of_index(6) == ["one_hop"]


# ---------------------------------------------------------------------------
# Real data (skipped without FLYBRAIN_DATA_DIR)
# ---------------------------------------------------------------------------


@requires_real_data
def test_real_connectome_sugar_experiment():
    """(9) Load FlyWire v783, drive the 21 sugar GRNs at 200 Hz for 200 ms."""
    import time

    data_dir = _data_dir()
    t0 = time.perf_counter()
    connectome = Connectome.load(data_dir)
    load_s = time.perf_counter() - t0
    assert connectome.n_neurons == 138_639
    assert connectome.n_synapses > 10_000_000
    manifest = connectome.manifest()
    assert manifest.loaded and manifest.n_neurons == 138_639
    assert manifest.sha256_ok is not None

    atlas = Atlas.load(connectome=connectome)
    sugar = atlas.indices("sugar_grn")
    assert len(sugar) == 21
    assert atlas.group("sugar_grn").missing_ids == []
    assert len(atlas.group("sugar_downstream").indices) > 0

    engine = FlyBrainEngine(connectome, seed=0, backend="numpy")
    engine.set_rates(sugar, 200.0)
    times, idx = engine.run(200.0)
    assert idx.size > 0
    active = int(np.unique(idx).size)
    assert active > len(sugar)
    assert engine.mean_rates(sugar, 200.0) > 100.0
    assert engine.mean_rates(atlas.indices("sugar_downstream"), 200.0) > 0.0
    sps = engine.steps_per_second or 0.0
    print(
        f"\nFLYBRAIN real data: load {load_s:.2f}s, spikes={idx.size}, active={active}, "
        f"steps/s={sps:.0f}, realtime_ratio={engine.realtime_ratio:.3f}"
    )
    assert sps >= 500.0, sps
