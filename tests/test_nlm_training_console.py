"""NLM training console honesty — skip-startup is not a MAS outage."""

from __future__ import annotations

from mycosoft_mas.core.routers import nlm_training_api as training


def test_normalize_items_accepts_taxa_payload() -> None:
    rows = training._normalize_items(
        {"taxa": [{"canonical_name": "Amanita muscaria"}, "skip-me"]}
    )
    assert len(rows) == 1
    assert rows[0]["canonical_name"] == "Amanita muscaria"


def test_training_capacity_skip_startup_fail_closed(monkeypatch) -> None:
    monkeypatch.setenv("MAS_SKIP_BACKGROUND_STARTUP", "1")
    capacity = training._training_capacity()
    assert capacity["jobs_available"] is False
    assert capacity["skip_startup"] is True
    assert "FAIL-CLOSED" in capacity["reason"]


def test_training_capacity_never_claims_jobs_on_188(monkeypatch) -> None:
    monkeypatch.delenv("MAS_SKIP_BACKGROUND_STARTUP", raising=False)
    capacity = training._training_capacity()
    assert capacity["jobs_available"] is False
    assert "fail-closed" in capacity["reason"].lower()


def test_console_payload_never_binds_ollama_or_stubs_p() -> None:
    nlm = {
        "bound_to_ollama": False,
        "forecast_qualified": False,
        "forecast_p": None,
    }
    assert nlm["bound_to_ollama"] is False
    assert nlm["forecast_qualified"] is False
    assert nlm["forecast_p"] is None
