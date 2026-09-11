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


def test_console_payload_never_binds_ollama_or_stubs_p(monkeypatch) -> None:
    import asyncio

    async def fake_mindex(_path: str, timeout: float = 8.0):
        return {"total_taxa": 3, "total_compounds": 9}

    async def fake_nlm():
        return {
            "bound_to_ollama": False,
            "forecast_qualified": False,
            "forecast_p": None,
            "model_loaded": False,
            "weights_sha256": None,
        }

    monkeypatch.setattr(training, "_mindex_get", fake_mindex)
    monkeypatch.setattr(training, "_nlm_live_status", fake_nlm)
    monkeypatch.setattr(training, "_disk_checkpoints", lambda: [])
    monkeypatch.setattr(
        "mycosoft_mas.nlm.formspace.scientific_loader.inventory_nlm_weights",
        lambda **_kwargs: {
            "weights": [],
            "count": 0,
            "bound_to_ollama": False,
            "forecast_qualified": False,
            "forecast_p": None,
        },
    )
    payload = asyncio.run(training.training_console())
    assert payload["bound_to_ollama"] is False
    assert payload["forecast_qualified"] is False
    assert payload["forecast_p"] is None
    assert payload["nlm"]["bound_to_ollama"] is False
    assert payload["nlm"]["forecast_p"] is None
    assert payload["mindex"]["compound_count"] == 9


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

    inventory = loader.inventory_nlm_weights(refresh=True)
    names = {row["name"] for row in inventory["weights"]}
    assert "weights.pt" in names
    assert "model.json" in names
    assert inventory["home"] == "nlm-home"
    assert all("/" not in str(row["path"])[:1] or not str(row["path"]).startswith("/") for row in inventory["weights"])
    assert all(":" not in str(row["path"])[:3] for row in inventory["weights"])
    assert inventory["bound_to_ollama"] is False
    assert inventory["forecast_qualified"] is False
    assert inventory["forecast_p"] is None
    assert all(row["forecast_qualified"] is False for row in inventory["weights"])
    assert all(not str(row["path"]).startswith(str(home)) for row in inventory["weights"])


def test_disk_checkpoint_ids_are_unique_and_loadable(tmp_path, monkeypatch) -> None:
    model = tmp_path / "nlm" / "models"
    nested = model / "checkpoints"
    nested.mkdir(parents=True)
    (model / "weights.pt").write_bytes(b"nlm-a" * 200)
    (nested / "weights.pt").write_bytes(b"nlm-b" * 200)
    monkeypatch.setenv("NLM_HOME", str(tmp_path / "nlm"))
    monkeypatch.setenv("NLM_MODEL_DIR", str(model))
    monkeypatch.setenv("NLM_CHECKPOINT_DIR", str(nested))
    training._DISK_CHECKPOINT_CACHE["at"] = 0.0
    training._DISK_CHECKPOINT_CACHE["value"] = None
    rows = training._disk_checkpoints()
    ids = [row["id"] for row in rows]
    assert len(ids) == len(set(ids))
    assert len(rows) == 2
    assert all(not str(row["path"]).startswith(str(tmp_path)) for row in rows)
    match = next(row for row in rows if row["id"] == ids[0])
    assert match["checkpoint_id"] == ids[0]


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
