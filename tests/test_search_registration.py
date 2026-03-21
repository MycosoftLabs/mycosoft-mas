"""
Tests for search registration (MINDEX persist, training sink) — Doable Search Rollout.
Unit tests for helpers; persist_search_to_mindex is tested with mocked HTTP.
Created: March 14, 2026
"""

from mycosoft_mas.consciousness.search_registration import (
    _normalize_query,
    _result_hash,
    _snippet_from_payload,
)


def test_normalize_query():
    assert _normalize_query("  Amanita muscaria  ") == "amanita muscaria"
    assert _normalize_query("") == ""
    assert _normalize_query(None) == ""


def test_result_hash_stable():
    payload = {"results": {"keyword": [{"id": "1", "scientific_name": "Amanita"}]}}
    h1 = _result_hash("amanita", payload)
    h2 = _result_hash("amanita", payload)
    assert h1 == h2
    assert len(h1) == 32


def test_snippet_from_payload():
    payload = {
        "focus": "Fungi search",
        "results": {
            "keyword": [
                {"scientific_name": "Amanita muscaria", "description": "Red cap"},
            ],
            "semantic": [],
        },
    }
    snippet = _snippet_from_payload(payload, max_len=500)
    assert "Fungi" in snippet or "Amanita" in snippet
    assert len(snippet) <= 500


def test_snippet_empty_payload():
    assert _snippet_from_payload({}) == "Search completed."
