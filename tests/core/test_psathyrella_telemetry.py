"""Validate Psathyrella BuoyTelemetry envelope against GCS contract shape."""

from __future__ import annotations

import pytest

from mycosoft_mas.devices.psathyrella.constants import PSATHYRELLA_DEVICE_ID
from mycosoft_mas.devices.psathyrella.telemetry_builder import build_buoy_telemetry

REQUIRED_TOP_LEVEL = {
    "deviceId",
    "link",
    "lastUpdateMsAgo",
    "source",
    "simulated",
    "pose",
    "bme",
    "propulsion",
    "autonomy",
    "power",
    "comms",
    "camera",
    "lidar",
    "radar",
    "bluesight",
}


@pytest.mark.asyncio
async def test_buoy_telemetry_envelope_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_fetch(*_args, **_kwargs):
        return None, None, None, False

    monkeypatch.setattr(
        "mycosoft_mas.devices.psathyrella.telemetry_builder._fetch_bme_from_mycobrain",
        _fake_fetch,
    )

    envelope = await build_buoy_telemetry(PSATHYRELLA_DEVICE_ID)

    assert REQUIRED_TOP_LEVEL.issubset(envelope.keys())
    assert envelope["deviceId"] == PSATHYRELLA_DEVICE_ID
    assert envelope["simulated"] is False
    assert envelope["link"] in {"online", "stale", "offline", "unknown"}
    assert "a" in envelope["bme"] and "b" in envelope["bme"]
    assert len(envelope["propulsion"]["thrusters"]) == 4
    assert envelope["autonomy"]["mode"] == "MANUAL"
    assert envelope["lidar"]["active"] is False
    assert envelope["radar"]["maxRangeM"] == 4000
    assert envelope["bluesight"]["wifi"] == []


@pytest.mark.asyncio
async def test_buoy_telemetry_maps_bme_when_present(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_fetch(*_args, **_kwargs):
        bme_a = {
            "temperature": 22.5,
            "humidity": 41.0,
            "pressure": 1013.2,
            "gasResistance": 125000.0,
            "iaq": 42.0,
            "iaqAccuracy": 3.0,
            "co2Equivalent": 450.0,
            "vocEquivalent": 0.5,
            "present": True,
            "address": "0x77",
            "label": "BME688 A - I2C-1 AMB",
        }
        return bme_a, None, "2026-06-25T12:00:00+00:00", True

    monkeypatch.setattr(
        "mycosoft_mas.devices.psathyrella.telemetry_builder._fetch_bme_from_mycobrain",
        _fake_fetch,
    )

    envelope = await build_buoy_telemetry(PSATHYRELLA_DEVICE_ID)
    assert envelope["link"] == "online"
    assert envelope["bme"]["a"]["temperature"] == 22.5
    assert envelope["bme"]["a"]["gasResistance"] == 125000.0
    assert envelope["bme"]["b"] is None


def test_psathyrella_api_telemetry_route(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from mycosoft_mas.core.routers import psathyrella_api

    async def _fake_build(_device_id: str):
        return {
            "deviceId": PSATHYRELLA_DEVICE_ID,
            "link": "unknown",
            "lastUpdateMsAgo": None,
            "source": None,
            "simulated": False,
            "pose": {
                "lat": None,
                "lon": None,
                "headingDeg": None,
                "speedKn": None,
                "depthM": None,
                "gpsLock": "unavailable",
            },
            "bme": {"a": None, "b": None},
            "propulsion": {"thrusters": [], "commandedVector": None},
            "autonomy": {
                "mode": "MANUAL",
                "armed": False,
                "waypoints": [],
                "activeWaypointId": None,
                "cameraHoldBearingDeg": None,
                "fightCurrent": False,
            },
            "power": {
                "solarInputW": None,
                "panelTempC": None,
                "batterySocPct": None,
                "batteryVoltage": None,
                "loadW": None,
                "estRuntimeH": None,
                "sunRepositionSuggested": False,
            },
            "comms": {
                "radios": [],
                "acoustic": {
                    "connected": False,
                    "carrierKhz": None,
                    "snrDb": None,
                    "rangeM": None,
                    "lastPingMsAgo": None,
                },
                "hydrophone": {"levelDb": None, "peakBearingDeg": None, "bandHz": None},
                "bridgeActive": False,
                "lastUplink": None,
            },
            "camera": {
                "active": False,
                "streamUrl": None,
                "zoom": None,
                "bearingDeg": None,
                "tiltDeg": None,
            },
            "lidar": {"sweepDeg": None, "maxRangeM": 500, "contacts": [], "active": False},
            "radar": {"sweepDeg": None, "maxRangeM": 4000, "contacts": [], "active": False},
            "bluesight": {"wifi": [], "active": False},
        }

    monkeypatch.setattr(psathyrella_api, "build_buoy_telemetry", _fake_build)

    app = FastAPI()
    app.include_router(psathyrella_api.router)
    client = TestClient(app)
    response = client.get("/api/psathyrella/telemetry")
    assert response.status_code == 200
    body = response.json()
    assert body.get("status") == "ok"
    assert body.get("deviceId") == PSATHYRELLA_DEVICE_ID
