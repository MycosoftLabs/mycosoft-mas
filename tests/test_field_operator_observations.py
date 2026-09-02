"""Contract tests for Mushroom 1 / Hyphae 1 field-operator observations.

Fixtures are exact captured operator JSON, not invented readings.
"""

from __future__ import annotations

import pytest

from mycosoft_mas.devices.field_operator_observations import (
    FIELD_OPERATOR_DEPLOYMENTS,
    collect_field_operator_observations,
    list_field_operator_catalog,
    normalize_operator_observation,
    resolve_field_operator,
    to_device_telemetry_payload,
)

# Captured 2026-09-02T05:38:25Z from GET http://192.168.0.228:8787/api/sensor
HYPHAE_SENSOR_CAPTURE = {
    "ok": True,
    "detected": True,
    "scan": {"addresses": [], "count": 0, "ts": None},
    "reading": {
        "type": "telemetry",
        "device_id": "mycobrain-sidea-10b41d",
        "node_id": "mycobrain-sidea-10b41d",
        "role": "side_a",
        "sensor_slot": "env",
        "address": "0x76",
        "present": True,
        "valid": True,
        "fw_version": "recovery-operator-bsec2-v0.7",
        "ts_ms": 363437,
        "temperature_c_comp": 25.09,
        "humidity_pct_comp": 48.38,
        "iaq": 50,
        "eco2_ppm": 500,
        "bvoc_ppm": 0.5,
        "pressure_hpa": 647.21,
        "gas_resistance_ohm": 466834,
        "ts": "2026-09-02T05:38:25.167Z",
    },
    "slots": {
        "amb": {
            "type": "telemetry",
            "device_id": "mycobrain-sidea-10b41d",
            "sensor_slot": "amb",
            "address": "0x77",
            "valid": True,
            "temperature_c_comp": 24.33,
            "humidity_pct_comp": 55.06,
            "pressure_hpa": 710.17,
            "gas_resistance_ohm": 490656,
            "iaq": 50,
            "eco2_ppm": 500,
            "bvoc_ppm": 0.5,
            "ts": "2026-09-02T05:38:25.162Z",
        },
        "env": {
            "type": "telemetry",
            "device_id": "mycobrain-sidea-10b41d",
            "sensor_slot": "env",
            "address": "0x76",
            "valid": True,
            "temperature_c_comp": 25.09,
            "humidity_pct_comp": 48.38,
            "pressure_hpa": 647.21,
            "gas_resistance_ohm": 466834,
            "iaq": 50,
            "eco2_ppm": 500,
            "bvoc_ppm": 0.5,
            "ts": "2026-09-02T05:38:25.167Z",
        },
    },
}

# Captured 2026-09-02T05:34:00Z from GET http://192.168.0.228:8787/api/status
HYPHAE_STATUS_CAPTURE = {
    "ok": True,
    "serialPort": "/dev/ttyACM0",
    "serialConnected": True,
    "lastHeartbeat": "2026-09-02T05:34:01.843Z",
    "lastError": None,
    "lastSensorReading": HYPHAE_SENSOR_CAPTURE["reading"],
}

HYPHAE = next(row for row in FIELD_OPERATOR_DEPLOYMENTS if row["catalog_id"] == "hyphae-1")
MUSHROOM = next(row for row in FIELD_OPERATOR_DEPLOYMENTS if row["catalog_id"] == "mushroom-1")
RECEIVED_AT = "2026-09-02T05:38:26.000Z"


def test_shared_mdp_is_ambiguous_and_not_a_deployment_key():
    assert HYPHAE["mdp_device_id"] == MUSHROOM["mdp_device_id"] == "mycobrain-sidea-10b41d"
    resolved = resolve_field_operator("mycobrain-sidea-10b41d")
    assert resolved["kind"] == "ambiguous_mdp"
    assert resolved["registry_ids"] == [
        "mycobrain-mushroom1-jetson-123",
        "mycobrain-hyphae1-jetson-228",
    ]


def test_catalog_preserves_unique_registry_identities():
    catalog = list_field_operator_catalog()
    ids = {row["registry_id"] for row in catalog["deployments"]}
    assert ids == {"mycobrain-mushroom1-jetson-123", "mycobrain-hyphae1-jetson-228"}
    assert all(row["mdp_is_unique"] is False for row in catalog["deployments"])


def test_captured_hyphae_reading_preserves_identity_time_units_and_provenance():
    observation = normalize_operator_observation(
        HYPHAE,
        status=HYPHAE_STATUS_CAPTURE,
        sensor=HYPHAE_SENSOR_CAPTURE,
        received_at=RECEIVED_AT,
        status_ok=True,
        sensor_ok=True,
    )
    assert observation["state"] == "available"
    assert observation["device_id"] == "mycobrain-hyphae1-jetson-228"
    assert observation["registry_id"] == "mycobrain-hyphae1-jetson-228"
    assert observation["identity_verified"] is False
    env = next(row for row in observation["readings"] if row["sensor_slot"] == "env")
    amb = next(row for row in observation["readings"] if row["sensor_slot"] == "amb")
    assert env["device_id"] == "mycobrain-hyphae1-jetson-228"
    assert env["reported_device_id"] == "mycobrain-sidea-10b41d"
    assert env["address"] == "0x76"
    assert env["observed_at"] == "2026-09-02T05:38:25.167Z"
    assert env["received_at"] == RECEIVED_AT
    temps = {row["name"]: row for row in env["measurements"]}
    assert temps["temperature_c"]["value"] == 25.09
    assert temps["temperature_c"]["unit"] == "°C"
    assert temps["humidity_pct"]["value"] == 48.38
    assert temps["humidity_pct"]["unit"] == "%RH"
    assert temps["pressure_hpa"]["value"] == 647.21
    assert temps["gas_resistance_ohm"]["value"] == 466834
    assert amb["address"] == "0x77"
    assert amb["observed_at"] == "2026-09-02T05:38:25.162Z"
    assert observation["provenance"]["source"] == "operator-http"
    assert observation["provenance"]["sensor_url"] == "http://192.168.0.228:8787/api/sensor"
    assert observation["provenance"]["status_url"] == "http://192.168.0.228:8787/api/status"


def test_telemetry_wrapper_omits_shared_mdp_as_source_device_id():
    observation = normalize_operator_observation(
        HYPHAE,
        status=HYPHAE_STATUS_CAPTURE,
        sensor=HYPHAE_SENSOR_CAPTURE,
        received_at=RECEIVED_AT,
        status_ok=True,
        sensor_ok=True,
    )
    payload = to_device_telemetry_payload(observation)
    assert payload["device_id"] == "mycobrain-hyphae1-jetson-228"
    assert "source_device_id" not in payload
    for row in payload["telemetry"]:
        assert row["device_id"] == "mycobrain-hyphae1-jetson-228"
        assert "source_device_id" not in row
        assert row["reported_device_id"] == "mycobrain-sidea-10b41d"


def test_fail_closed_when_operator_unreachable():
    observation = normalize_operator_observation(
        MUSHROOM,
        status=None,
        sensor=None,
        received_at=RECEIVED_AT,
        status_ok=False,
        sensor_ok=False,
        error="GET /api/status and /api/sensor failed or timed out",
    )
    assert observation["state"] == "unreachable"
    assert observation["readings"] == []
    assert observation["device_id"] == "mycobrain-mushroom1-jetson-123"


def test_fail_closed_when_timestamp_or_sensor_identity_missing():
    observation = normalize_operator_observation(
        HYPHAE,
        status={"serialConnected": True},
        sensor={"reading": {"temperature_c_comp": 25.0, "humidity_pct_comp": 40.0}},
        received_at=RECEIVED_AT,
        status_ok=True,
        sensor_ok=True,
    )
    assert observation["state"] == "unbound"
    assert observation["readings"] == []
    assert observation["rejected_count"] >= 1


def test_does_not_fabricate_missing_canonical_values():
    observation = normalize_operator_observation(
        HYPHAE,
        status=None,
        sensor={
            "reading": {
                "type": "telemetry",
                "device_id": "mycobrain-sidea-10b41d",
                "sensor_slot": "env",
                "address": "0x76",
                "temperature_c_comp": 25.09,
                "ts": "2026-09-02T05:38:25.167Z",
            }
        },
        received_at=RECEIVED_AT,
        status_ok=False,
        sensor_ok=True,
    )
    names = {row["name"] for row in observation["readings"][0]["measurements"]}
    assert names == {"temperature_c"}
    assert "humidity_pct" not in names


@pytest.mark.asyncio
async def test_collect_fail_closed_for_unknown_and_shared_mdp():
    unknown = await collect_field_operator_observations(device_id="not-a-device")
    assert unknown["state"] == "unbound"
    assert unknown["observations"] == []

    shared = await collect_field_operator_observations(device_id="mycobrain-sidea-10b41d")
    assert shared["state"] == "unbound"
    assert shared["observations"] == []
    assert "Shared board MDP" in shared["message"]


@pytest.mark.asyncio
async def test_collect_uses_injected_fetch_and_does_not_invent_mushroom_values():
    async def fetch_json(url: str, timeout_s: float):
        if url.startswith("http://192.168.0.228:8787"):
            if url.endswith("/api/status"):
                return HYPHAE_STATUS_CAPTURE
            if url.endswith("/api/sensor"):
                return HYPHAE_SENSOR_CAPTURE
        return None

    bundle = await collect_field_operator_observations(
        fetch_json=fetch_json,
        received_at=RECEIVED_AT,
    )
    by_id = {row["registry_id"]: row for row in bundle["observations"]}
    assert by_id["mycobrain-hyphae1-jetson-228"]["state"] == "available"
    assert by_id["mycobrain-mushroom1-jetson-123"]["state"] == "unreachable"
    assert by_id["mycobrain-mushroom1-jetson-123"]["readings"] == []
    assert by_id["mycobrain-hyphae1-jetson-228"]["readings"][0]["observed_at"] == "2026-09-02T05:38:25.167Z"
