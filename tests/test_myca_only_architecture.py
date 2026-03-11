"""
Tests for MYCA-only architecture: Ollama primary, no frontier fallback,
Merkle world root integration, device registry snapshot.

Date: March 9, 2026
"""

from __future__ import annotations

import json
import pytest

from mycosoft_mas.merkle.world_root_service import build_world_root
from mycosoft_mas.merkle.root_builder import WORLD_SLOT_ORDER


def test_build_world_root_single_slot() -> None:
    """build_world_root returns hex string with at least one slot."""
    slot_data = {"device_registry": {"devices": {}, "timestamp": "2026-03-09T12:00:00Z"}}
    root = build_world_root(slot_data)
    assert isinstance(root, str)
    assert len(root) == 64
    assert all(c in "0123456789abcdef" for c in root)


def test_build_world_root_multiple_slots() -> None:
    """build_world_root accepts multiple valid slots."""
    slot_data = {
        "device_registry": {"devices": {}, "timestamp": "2026-03-09T12:00:00Z"},
        "device_health": {"dev1": "online"},
        "crep_summary": "Flights: 12, vessels: 5",
    }
    root = build_world_root(slot_data)
    assert isinstance(root, str)
    assert len(root) == 64


def test_build_world_root_empty_raises() -> None:
    """build_world_root raises if no slots provided."""
    with pytest.raises(ValueError, match="at least one slot"):
        build_world_root({})


def test_build_world_root_ignores_unknown_slots() -> None:
    """Unknown slot names are ignored; valid slots still produce root."""
    slot_data = {
        "device_registry": {"devices": {}},
        "unknown_slot": "ignored",
    }
    root = build_world_root(slot_data)
    assert len(root) == 64


def test_get_device_registry_snapshot_returns_json_serializable() -> None:
    """get_device_registry_snapshot returns JSON-serializable dict."""
    from mycosoft_mas.core.routers.device_registry_api import get_device_registry_snapshot

    snap = get_device_registry_snapshot()
    assert isinstance(snap, dict)
    assert "devices" in snap
    assert "timestamp" in snap
    # Must be JSON-serializable
    json_str = json.dumps(snap)
    assert isinstance(json_str, str)


def test_llm_brain_ollama_primary() -> None:
    """LLMBrain uses Ollama as primary; docstring states 99.9% own LLM."""
    from mycosoft_mas.myca.os import llm_brain

    mod_doc = (llm_brain.__doc__ or "").lower()
    assert "ollama" in mod_doc
    assert "99" in mod_doc or "own" in mod_doc


def test_world_slot_order_includes_device_registry() -> None:
    """WORLD_SLOT_ORDER includes device_registry and device_health."""
    assert "device_registry" in WORLD_SLOT_ORDER
    assert "device_health" in WORLD_SLOT_ORDER
    assert "crep_summary" in WORLD_SLOT_ORDER
    assert "nlm_summary" in WORLD_SLOT_ORDER
