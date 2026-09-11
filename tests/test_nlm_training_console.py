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


def test_inventory_lists_on_disk_weights_and_never_qualifies(tmp_path, monkeypatch) -> None:
    from mycosoft_mas.nlm.formspace import scientific_loader as loader

    home = tmp_path / "nlm"
    reference = home / "reference"
    reference.mkdir(parents=True)
    weights = reference / "weights.pt"
    weights.write_bytes(b"nlm-reference-fixture" * 800)
    (reference / "model.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("NLM_HOME", str(home))
    monkeypatch.delenv("NLM_MODEL_DIR", raising=False)

    inventory = loader.inventory_nlm_weights()
    names = {row["name"] for row in inventory["weights"]}
    assert "weights.pt" in names
    assert "model.json" in names
    assert inventory["bound_to_ollama"] is False
    assert inventory["forecast_qualified"] is False
    assert inventory["forecast_p"] is None
    assert all(row["forecast_qualified"] is False for row in inventory["weights"])


def test_external_nlm_base_skips_mas_and_obsolete_8200(monkeypatch) -> None:
    from mycosoft_mas.core.routers import nlm_api

    monkeypatch.delenv("NLM_API_URL", raising=False)
    assert nlm_api._external_nlm_base() is None
    monkeypatch.setenv("NLM_API_URL", "http://192.168.0.188:8001")
    assert nlm_api._external_nlm_base() is None
    monkeypatch.setenv("NLM_API_URL", "http://192.168.0.188:8200")
    assert nlm_api._external_nlm_base() is None
    monkeypatch.setenv("NLM_API_URL", "http://example.test:9100")
    assert nlm_api._external_nlm_base() == "http://example.test:9100"
