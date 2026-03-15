"""
Tests for MAS search orchestrator — Doable Search Rollout validation.
Covers: run_unified_search return shape, fallback behavior (no consciousness).
Created: March 14, 2026
"""

import pytest

from mycosoft_mas.consciousness.search_orchestrator import run_unified_search


@pytest.mark.asyncio
async def test_run_unified_search_returns_canonical_shape():
    """run_unified_search returns dict with query, results.keyword, results.semantic, timestamp."""
    out = await run_unified_search(
        "Amanita muscaria",
        search_context=None,
    )
    assert isinstance(out, dict)
    assert out.get("query") == "Amanita muscaria"
    assert "results" in out
    assert "keyword" in out["results"]
    assert "semantic" in out["results"]
    assert "specialist" in out["results"]
    assert isinstance(out["results"]["keyword"], list)
    assert isinstance(out["results"]["semantic"], list)
    assert "timestamp" in out
    assert "focus" in out
    assert "memories" in out


@pytest.mark.asyncio
async def test_run_unified_search_with_empty_query():
    """Empty query still returns canonical shape (focus may be empty)."""
    out = await run_unified_search("", search_context=None)
    assert isinstance(out, dict)
    assert out.get("query") == ""
    assert "results" in out and "timestamp" in out
