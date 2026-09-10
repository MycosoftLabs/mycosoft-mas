"""SEP10 archived FormSpace reference: replay yes, Fusarium p never stub."""

from __future__ import annotations

from pathlib import Path

from mycosoft_mas.nlm.formspace.native_ssm import (
    inverse_variance_fusion,
    native_scan,
)
from mycosoft_mas.nlm.formspace.scientific_loader import (
    LEGACY_MODEL_JSON_SHA256,
    probe_scientific_nlm,
)
from mycosoft_mas.nlm.inference.service import is_usable_nlm_confidence

PACKET_REF = Path(
    r"C:\Users\Owner1\Downloads\NLM_Weights_MAS188_Cursor_Package"
    r"\NLM_Weights_MAS188_Cursor_Package\reference"
)


def test_native_scan_chunk_equivalence() -> None:
    series = [1.0, 2.0, 3.0, 4.0]
    full, _ = native_scan(series, 0.1, -2.0, 0.5)
    first, mid = native_scan(series[:2], 0.1, -2.0, 0.5)
    second, _ = native_scan(series[2:], 0.1, -2.0, 0.5, h=mid)
    assert max(abs(a - b) for a, b in zip(full, first + second)) < 1e-12


def test_inverse_variance_fusion() -> None:
    mean, var = inverse_variance_fusion([25.0, 27.0], [1.0, 4.0])
    assert abs(mean - 25.4) < 1e-9
    assert abs(var - 0.8) < 1e-9


def test_stub_confidence_never_usable() -> None:
    assert is_usable_nlm_confidence(0.85, "ok", {}) is False
    assert is_usable_nlm_confidence(0.0, "Archived FormSpace reference replay completed.", {}) is False


def test_legacy_probe_stays_forecast_unloaded(tmp_path: Path) -> None:
    (tmp_path / "weights.pt").write_bytes(b"0" * 20_000)
    (tmp_path / "model.json").write_text(
        '{"schema":"formspace-environmental-reference/0.1.0","model_sha256":"%s"}'
        % LEGACY_MODEL_JSON_SHA256,
        encoding="utf-8",
    )
    probe = probe_scientific_nlm(str(tmp_path))
    assert probe.model_loaded is False
    assert probe.is_legacy_reference is True


def test_reference_runtime_from_packet() -> None:
    if not (PACKET_REF / "reference_trained_weights.npz").is_file():
        return
    from mycosoft_mas.nlm.formspace.reference_runtime import ReferenceRuntime

    runtime = ReferenceRuntime()
    assert runtime.load(str(PACKET_REF)) is True
    replay = runtime.replay()
    assert replay["ok"] is True
    assert replay["p"] is None
    assert replay["forecast_qualified"] is False
    assert runtime.parameter_count == 25728
    weka = runtime.weka_features()
    assert weka["ok"] is True
    assert weka["p"] is None
    assert "0.85" not in (weka.get("arff") or "")


def test_decision_path_p_null() -> None:
    import asyncio

    from mycosoft_mas.nlm.formspace.decision_path import run_decision_path

    path = asyncio.run(run_decision_path({}))
    assert path["p"] is None
    assert path["live"] is False
    assert path["forecast_qualified"] is False
    assert any(task["status"] == "NOT_SUPPLIED" for task in path["tasks"])
