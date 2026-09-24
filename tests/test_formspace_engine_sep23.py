"""FormSpace engine API — atlas, graph, experiment (Sep 23, 2026)."""

from __future__ import annotations

from mycosoft_mas.nlm.formspace.atlas import FormSpaceAtlas
from mycosoft_mas.nlm.formspace.dynamics import compute_trajectory, run_recovery_experiment
from mycosoft_mas.nlm.formspace.engine import FormSpaceEngine
from mycosoft_mas.nlm.formspace.graphing import build_graph_payload


def test_demo_catalog_has_charts(tmp_path) -> None:
    atlas = FormSpaceAtlas(root=tmp_path)
    charts = atlas.list_demo_charts()
    assert len(charts) >= 10
    assert all(c.get("live") is False for c in charts)
    assert any(c["chart_id"] == "fs-fci-demo-v1" for c in charts)


def test_trajectory_from_fixture_series() -> None:
    result = compute_trajectory(
        [0.1, 0.2, 0.3, 0.4],
        chart_id="fs-fci-demo-v1",
        origin="CATALOG_FIXTURE",
    )
    assert result["ok"] is True
    assert result["p"] is None
    assert len(result["trajectory"]) == 4
    assert result["final_state"] is not None


def test_trajectory_empty_abstains() -> None:
    result = compute_trajectory([], chart_id="fs-fci-demo-v1")
    assert result["ok"] is False
    assert result["status"] == "no_data"
    assert result["trajectory"] == []


def test_recovery_experiment_deterministic() -> None:
    baseline = [0.1, 0.15, 0.2, 0.25, 0.3, 0.28, 0.26, 0.24]
    result = run_recovery_experiment(
        chart_id="fs-fci-demo-v1",
        baseline=baseline,
        perturbation_index=2,
        perturbation_delta=0.5,
    )
    assert result["ok"] is True
    assert result["p"] is None
    assert len(result["baseline_trajectory"]) == len(baseline)
    assert "recovered" in result


def test_graph_demo_fixture(tmp_path) -> None:
    # Ensure atlas fixtures resolve via default DEMO_CHARTS
    payload = build_graph_payload(
        chart_id="fs-spectral-demo-v1",
        use_demo_fixture=True,
    )
    assert payload["ok"] is True
    assert len(payload["points"]) > 0
    assert payload["p"] is None
    assert payload["origin"] == "CATALOG_FIXTURE"


def test_graph_no_data_without_fixture() -> None:
    payload = build_graph_payload(
        chart_id="fs-spectral-demo-v1",
        use_demo_fixture=False,
    )
    assert payload["ok"] is False
    assert payload["status"] == "no_data"
    assert payload["points"] == []


def test_engine_auth_memory(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FORMSPACE_MEMORY_DIR", str(tmp_path / "mem"))
    monkeypatch.setenv("FORMSPACE_ATLAS_DIR", str(tmp_path / "atlas"))
    engine = FormSpaceEngine()
    denied = engine.memory_list(None)
    assert denied.get("auth_required") is True
    saved = engine.atlas_upsert(
        {"name": "My chart", "axes": ["x", "y"]},
        user_id="user-1",
    )
    assert saved["ok"] is True
    mem = engine.memory_list("user-1")
    assert mem["ok"] is True
    assert any(c["chart_id"] == saved["chart"]["chart_id"] for c in mem["saved_charts"])


def test_engine_health_not_ollama(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FORMSPACE_ATLAS_DIR", str(tmp_path / "atlas"))
    engine = FormSpaceEngine()
    health = engine.health()
    assert health["bound_to_ollama"] is False
    assert health["engine"] == "formspace"
