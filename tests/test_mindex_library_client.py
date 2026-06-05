"""Unit tests for MindexLibraryClient (no live MINDEX required)."""

from __future__ import annotations

import pytest

from mycosoft_mas.integrations.mindex_library_client import (
    MindexLibraryClient,
    _mindex_api_base,
)
from mycosoft_mas.nlm.library_frames import waveform_ref_from_blob


def test_mindex_api_base_default(monkeypatch):
    monkeypatch.delenv("MINDEX_API_URL", raising=False)
    assert _mindex_api_base() == "http://192.168.0.189:8000/api/mindex"


def test_mindex_api_base_with_suffix(monkeypatch):
    monkeypatch.setenv("MINDEX_API_URL", "http://192.168.0.189:8000/api/mindex")
    assert _mindex_api_base() == "http://192.168.0.189:8000/api/mindex"


def test_stream_url():
    client = MindexLibraryClient(base_url="http://192.168.0.189:8000/api/mindex")
    url = client.stream_url("a742bbd6-383d-4a7f-8945-e3c7d55c1982")
    assert url.endswith("/library/blobs/a742bbd6-383d-4a7f-8945-e3c7d55c1982/stream")


def test_waveform_ref_from_blob():
    ref = waveform_ref_from_blob(
        {
            "id": "blob-1",
            "sample_rate_hz": 44100,
            "duration_sec": 12.5,
            "channels": 2,
            "filename": "test.wav",
            "label_primary": "bird",
        }
    )
    assert ref["mindex_id"] == "blob-1"
    assert ref["sample_rate_hz"] == 44100
    assert ref["duration_seconds"] == 12.5
    assert ref["channel_count"] == 2


@pytest.mark.asyncio
async def test_health_unreachable(monkeypatch):
    class BrokenClient(MindexLibraryClient):
        async def list_catalog(self, limit=100, path=None):
            raise ConnectionError("LAN down")

    client = BrokenClient(base_url="http://127.0.0.1:1/api/mindex", timeout_s=0.1)
    health = await client.health_check()
    assert health["reachable"] is False
