"""Unit smoke tests for MYCA Harness (external services mocked)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from mycosoft_mas.harness.config import HarnessConfig
from mycosoft_mas.harness.engine import HarnessEngine, set_engine
from mycosoft_mas.harness.intention_brain import IntentionBrain
from mycosoft_mas.harness.models import HarnessPacket, RouteType
from mycosoft_mas.harness.planner import HarnessPlanner
from mycosoft_mas.harness.router import HarnessRouter
from mycosoft_mas.harness.static_search import StaticSearch
from mycosoft_mas.harness.static_system import StaticSystem
from mycosoft_mas.harness.turbo_quant import TurboQuantCompressor


@pytest.fixture
def cfg(tmp_path):
    yaml_path = tmp_path / "s.yaml"
    yaml_path.write_text(
        "hello:\n  answer: world\n",
        encoding="utf-8",
    )
    return HarnessConfig(
        nemotron_base_url="http://test",
        nemotron_model="test",
        nemotron_api_key=None,
        personaplex_bridge_url="http://test-pp",
        mindex_api_url="http://test-mx",
        mindex_api_key=None,
        mindex_http_timeout=30.0,
        supabase_url=None,
        supabase_service_key=None,
        static_answers_path=str(yaml_path),
        intention_db_path=str(tmp_path / "ib.sqlite"),
        enable_turbo_quant=True,
        turbo_quant_nda_mode=True,
        ground_queries_with_mindex=True,
        default_unified_search_types="biological",
        nlm_enabled=False,
    )


def test_static_lookup(cfg):
    ss = StaticSystem(cfg.static_answers_path)
    assert ss.lookup("hello") == "world"
    assert ss.lookup("missing") is None


def test_router_nlm_sensor():
    r = HarnessRouter()
    p = HarnessPacket(query="", raw_sensor={"temp": 1})
    assert r.classify(p) == RouteType.NLM


def test_turbo_quant_roundtrip():
    tq = TurboQuantCompressor(nda_mode=True)
    s = "payload"
    assert tq.decompress(tq.compress(s)) == s


@pytest.mark.asyncio
async def test_engine_static_short_circuit(cfg):
    set_engine(None)
    eng = HarnessEngine(cfg)
    out = await eng.run(HarnessPacket(query="hello"))
    assert out.route == RouteType.STATIC
    assert out.text == "world"


@pytest.mark.asyncio
async def test_engine_nemotron_mocked(cfg):
    set_engine(None)
    eng = HarnessEngine(cfg)

    async def fake_gen(*_a, **_k):
        yield "ok"

    with patch.object(eng.nemotron, "generate", fake_gen):
        with patch.object(eng.mindex, "record_execution", new_callable=AsyncMock):
            with patch.object(
                eng.static_search,
                "build_llm_context",
                new_callable=AsyncMock,
                return_value="",
            ):
                out = await eng.run(HarnessPacket(query="x" * 100))
                assert "ok" in (out.text or "")
                assert out.route == RouteType.MINDEX_GROUNDED


def test_router_mindex_grounded_default():
    r = HarnessRouter()
    p = HarnessPacket(query="what is Agaricus bisporus")
    assert r.classify(p) == RouteType.MINDEX_GROUNDED


def test_router_nemotron_no_grounding():
    r = HarnessRouter()
    p = HarnessPacket(query="hello", metadata={"no_grounding": True})
    assert r.classify(p) == RouteType.NEMOTRON


def test_planner_includes_intention_when_goal_exists(cfg):
    ib = IntentionBrain(cfg.intention_db_path)
    gid = ib.add_goal("test harness goal", status="active")
    planner = HarnessPlanner(ib)
    plan = planner.plan(
        HarnessPacket(query="q"),
        RouteType.MINDEX_GROUNDED,
    )
    assert plan.get("intention") is not None
    assert plan["intention"]["goal_id"] == gid
    assert "consider_goal:" in "".join(plan["steps"])


@pytest.mark.asyncio
async def test_static_search_context_from_unified_payload(cfg):
    ss = StaticSearch(cfg)
    fake = {
        "results": {"biological": [{"scientific_name": "Agaricus bisporus"}]},
        "total_count": 1,
        "domains_searched": ["biological"],
    }
    with patch.object(ss, "fetch_unified", new_callable=AsyncMock, return_value=fake):
        ctx = await ss.build_llm_context("mushroom")
        assert "Agaricus" in ctx
