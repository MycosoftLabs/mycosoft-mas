from __future__ import annotations

from datetime import datetime, timezone

from mycosoft_mas.avani.worldview import (
    build_worldstate_snapshot,
    classify_device_telemetry_trust,
    review_device_action,
    review_worldview_payload,
)


def test_worldstate_snapshot_is_stable_and_degraded_aware():
    payload = {
        "timestamp": "2026-05-14T00:00:00+00:00",
        "degraded": False,
        "world": {
            "crep": {"freshness": "live", "flights": 2, "vessels": 3, "satellites": 4},
            "devices": {"freshness": "stale", "active_count": 5},
            "presence": {"online_users": 6, "active_sessions": 7},
        },
    }

    first = build_worldstate_snapshot(payload)
    second = build_worldstate_snapshot(payload)

    assert first.worldstate_snapshot_id == second.worldstate_snapshot_id
    assert first.source_counts["crep_flights"] == 2
    assert first.source_freshness["devices"] == "stale"
    assert first.confidence < 1.0


def test_worldview_review_denies_internal_domains():
    frame = review_worldview_payload(
        worldview_request_id="req-1",
        data={"results": []},
        source_domains=["telemetry"],
        caller={"plan": "enterprise", "user_type": "agent"},
    )

    assert frame.avani_verdict == "deny"
    assert frame.sensitivity == "internal"


def test_worldview_review_marks_ecological_domains_for_audit():
    frame = review_worldview_payload(
        worldview_request_id="req-2",
        data=[{"id": 1}],
        source_domains=["species", "observations"],
        caller={"plan": "pro", "user_type": "human"},
    )

    assert frame.avani_verdict == "allow"
    assert frame.ecological_risk > 0
    assert frame.provenance["result_count"] == 1


def test_device_telemetry_trust_classifier_marks_trusted_live_data():
    trust = classify_device_telemetry_trust(
        {
            "status": "online",
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "confidence": 0.95,
            "drift_score": 0.02,
        }
    )

    assert trust == "trusted"


def test_device_action_requires_rollback_for_high_impact_command():
    review = review_device_action(
        device_id="sensor-1",
        action="deploy",
        operator_id="operator-1",
        telemetry={"status": "online", "observed_at": datetime.now(timezone.utc).isoformat()},
        ecological_impact=0.4,
        reversibility=0.7,
    )

    assert review.approved is False
    assert review.verdict == "require_approval"
    assert review.rollback_required is True


def test_device_action_denies_compromised_telemetry():
    review = review_device_action(
        device_id="sensor-1",
        action="deploy",
        operator_id="operator-1",
        telemetry={"status": "online", "compromised": True},
        rollback_plan="Recall sensor and disable command channel.",
    )

    assert review.approved is False
    assert review.verdict == "deny"
    assert review.telemetry_trust == "compromised"
