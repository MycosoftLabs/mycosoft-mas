"""Tests for SINE ingest metadata and MINDEX client wiring."""

from __future__ import annotations

import pytest

from mycosoft_mas.devices.psathyrella.sine_ingest import (
    build_sine_ingest_metadata,
    ingest_acoustic_blob,
)


def test_build_sine_ingest_metadata_hydrophone() -> None:
    meta = build_sine_ingest_metadata(device_id="psathyrella-buoy-com4", sensor_type="hydrophone")
    assert "psathyrella" in meta["source_id"]
    assert meta["acoustic_domain"] == "water"
    assert "hydrophone" in meta["tags"]


@pytest.mark.asyncio
async def test_ingest_acoustic_blob_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FailClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, *args, **kwargs):
            raise ConnectionError("mindex down")

    monkeypatch.setattr("mycosoft_mas.devices.psathyrella.sine_ingest.httpx.AsyncClient", _FailClient)
    result = await ingest_acoustic_blob(
        device_id="psathyrella-buoy-com4",
        sensor_type="hydrophone",
        blob_uri="/nas/psathyrella/sample.wav",
        duration_s=12.0,
    )
    assert result["status"] == "pending"
    assert result["reason"] == "mindex_unreachable"
