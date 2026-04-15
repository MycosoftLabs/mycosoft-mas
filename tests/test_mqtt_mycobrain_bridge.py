"""Unit tests for MQTT → MAS/MINDEX bridge helpers."""

from mycosoft_mas.integrations.mqtt_mycobrain_bridge import (
    normalize_heartbeat_payload,
    parse_mqtt_topic,
    synthesize_envelope_from_telemetry,
)


def test_parse_topic_ok():
    p = parse_mqtt_topic("mycobrain/jetson-1/heartbeat")
    assert p is not None
    assert p.device_id == "jetson-1"
    assert p.action == "heartbeat"


def test_parse_topic_reject():
    assert parse_mqtt_topic("other/a/b") is None
    assert parse_mqtt_topic("mycobrain/x") is None


def test_synthesize_envelope():
    env = synthesize_envelope_from_telemetry(
        "dev-a",
        {"pack": [{"id": "t", "v": 1.0, "u": "C"}], "seq": 42},
    )
    assert env["hdr"]["deviceId"] == "dev-a"
    assert env["seq"] == 42
    assert len(env["pack"]) == 1


def test_normalize_heartbeat_defaults():
    hb = normalize_heartbeat_payload("id-9", {})
    assert hb["device_id"] == "id-9"
    assert hb["ingestion_source"] == "mqtt"
    assert isinstance(hb["extra"], dict)
