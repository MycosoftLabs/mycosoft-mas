"""Stage B FormSpace ledger + causal pipeline. No invented ecology p."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from mycosoft_mas.nlm.formspace.contracts import ForecastEnvelope, ObservationEnvelope
from mycosoft_mas.nlm.formspace.forecast_ledger import ForecastLedger
from mycosoft_mas.nlm.formspace.observation_pipeline import CausalObservationPipeline
from mycosoft_mas.nlm.formspace.scientific_loader import (
    LEGACY_MODEL_JSON_SHA256,
    probe_scientific_nlm,
)


def test_probe_unloaded_without_weights(tmp_path: Path) -> None:
    probe = probe_scientific_nlm(str(tmp_path))
    assert probe.model_loaded is False
    assert "Ollama" in probe.reason or "weights" in probe.reason.lower() or "No scientific" in probe.reason


def test_probe_ignores_gguf(tmp_path: Path) -> None:
    (tmp_path / "llama.gguf").write_bytes(b"0" * 20_000)
    probe = probe_scientific_nlm(str(tmp_path))
    assert probe.model_loaded is False


def test_probe_preserves_legacy_sha_unloaded(tmp_path: Path) -> None:
    (tmp_path / "weights.pt").write_bytes(b"0" * 20_000)
    (tmp_path / "model.json").write_text(
        json.dumps(
            {
                "schema": "formspace-environmental-reference/0.1.0",
                "model_sha256": LEGACY_MODEL_JSON_SHA256,
            }
        ),
        encoding="utf-8",
    )
    probe = probe_scientific_nlm(str(tmp_path))
    assert probe.model_loaded is False
    assert probe.is_legacy_reference is True
    assert LEGACY_MODEL_JSON_SHA256[:12] in probe.reason


def test_m07_future_available_at_excluded() -> None:
    pipeline = CausalObservationPipeline()
    envelope = ObservationEnvelope(
        subject_id="site-1",
        source_id="sensor-a",
        root_evidence_id="ev-1",
        event_time="2026-09-09T12:00:00Z",
        received_at="2026-09-09T12:05:00Z",
        available_at="2026-09-09T13:00:00Z",
        chart_id="env-ssm32",
        chart_version="v1",
        values={"x": 1.0},
        origin="MEASURED",
    )
    cutoff = datetime(2026, 9, 9, 12, 30, tzinfo=timezone.utc)
    result = pipeline.process(envelope, cutoff)
    assert result["status"] == "excluded_future_available_at"
    assert result["consumed"] is False
    assert result["scores"] is None if "scores" in result else True


def test_m06_duplicate_root_evidence_once() -> None:
    pipeline = CausalObservationPipeline()
    first = ObservationEnvelope(
        subject_id="site-1",
        source_id="sensor-a",
        root_evidence_id="ev-dup",
        event_time="2026-09-09T12:00:00Z",
        received_at="2026-09-09T12:01:00Z",
        available_at="2026-09-09T12:02:00Z",
        chart_id="env-ssm32",
        chart_version="v1",
        values={"x": 1.0},
        origin="MEASURED",
    )
    cutoff = datetime(2026, 9, 9, 12, 30, tzinfo=timezone.utc)
    accepted = pipeline.process(first, cutoff)
    assert accepted["consumed"] is True
    assert accepted["scores"] is None
    copy = first.model_copy(update={"observation_id": "obs-copy"})
    dup = pipeline.process(copy, cutoff)
    assert dup["status"] == "duplicate_root_evidence"
    assert dup["consumed"] is False


def test_i03_ledger_refuses_overwrite(tmp_path: Path) -> None:
    ledger = ForecastLedger(tmp_path)
    envelope = ForecastEnvelope(
        forecast_id="fcst-lock",
        subject_id="site-1",
        episode_id="ep-1",
        issued_at="2026-09-09T12:00:00Z",
        input_cutoff_at="2026-09-09T11:59:00Z",
        event_definition_id="onset.v1",
        chart_id="env-ssm32",
        chart_version="v1",
        support_status="UNSUPPORTED",
        reasons=["weights absent"],
        hazard_probabilities=[0.85],
        cumulative_probabilities=[0.85],
    )
    first = ledger.persist(envelope)
    assert first["overwritten"] is False
    assert first["forecast"]["hazard_probabilities"] is None
    second = ledger.persist(
        envelope.model_copy(update={"reasons": ["late label"]})
    )
    assert second["status"] == "idempotent"
    assert second["overwritten"] is False
    refused = ledger.refuse_overwrite("fcst-lock", {"late_label": {"onset_at": "later"}})
    assert refused["status"] == "refused"
    assert refused["overwritten"] is False
    stored = ledger.get("fcst-lock")
    assert stored is not None
    assert stored["reasons"] == ["weights absent"]


def test_i05_unsupported_and_failed_export(tmp_path: Path) -> None:
    ledger = ForecastLedger(tmp_path)
    for status, forecast_id in (
        ("UNSUPPORTED", "fcst-unsup"),
        ("FAILED", "fcst-fail"),
        ("CANCELLED", "fcst-cancel"),
        ("STALE", "fcst-stale"),
    ):
        ledger.persist(
            ForecastEnvelope(
                forecast_id=forecast_id,
                subject_id="site-1",
                episode_id="ep-1",
                issued_at="2026-09-09T12:00:00Z",
                input_cutoff_at="2026-09-09T11:59:00Z",
                event_definition_id="onset.v1",
                chart_id="env-ssm32",
                chart_version="v1",
                support_status=status,
                reasons=[status.lower()],
            )
        )
        row = ledger.get(forecast_id)
        assert row is not None
        assert row["support_status"] == status
        assert row["hazard_probabilities"] is None
        assert row["cumulative_probabilities"] is None
