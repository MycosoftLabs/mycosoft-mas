from __future__ import annotations

from datetime import datetime, timezone

import pytest

from mycosoft_mas.avani.audit.season_state import AvaniSeasonStateStore
from mycosoft_mas.avani.season_engine.seasons import Season, SeasonMetrics, SeasonState


class FailingMindexClient:
    async def _get_db_pool(self):
        raise RuntimeError("database unavailable in test")


@pytest.mark.asyncio
async def test_season_state_json_fallback_round_trip(tmp_path):
    store = AvaniSeasonStateStore(mindex_client=FailingMindexClient(), fallback_dir=tmp_path)
    state = SeasonState(
        current=Season.AUTUMN,
        entered_at=datetime.now(timezone.utc),
        trigger_reason="eco_stability_0.70_below_threshold",
        metrics=SeasonMetrics(eco_stability=0.7, all_systems_green=False),
        history=[{"from": "spring", "to": "autumn", "reason": "test"}],
    )

    storage = await store.save(state)
    restored = await store.load()

    assert storage == "json_fallback"
    assert restored is not None
    assert restored.current == Season.AUTUMN
    assert restored.metrics.eco_stability == 0.7
    assert restored.history[0]["to"] == "autumn"
