"""ITDX Task 8 + situation-assessment — no mock PASS."""

from mycosoft_mas.agents.itdx_task8_agent import (
    SCHEMA_VERSION,
    SITUATION_SCHEMA_VERSION,
    aggregate_avani_gate,
    avani_to_task8_gate,
    borda_rank,
)
from mycosoft_mas.core.routers.itdx_api import CHANNEL_KEYS, fort_stewart_demo_slice


def test_avani_gate_order_deny_pause_pass_review():
    assert avani_to_task8_gate(approved=False, has_evidence=True, envelope_complete=True) == "DENY"
    assert avani_to_task8_gate(approved=True, has_evidence=False, envelope_complete=True) == "PAUSE"
    assert avani_to_task8_gate(approved=True, has_evidence=True, envelope_complete=True) == "PASS"
    assert avani_to_task8_gate(approved=True, has_evidence=True, envelope_complete=False) == "REVIEW"
    assert avani_to_task8_gate(approved=None, has_evidence=True, envelope_complete=True) == "REVIEW"


def test_aggregate_does_not_invent_pass():
    assert aggregate_avani_gate(["REVIEW"], ["REVIEW", "REVIEW"]) == "REVIEW"
    assert aggregate_avani_gate(["DENY"], ["PASS"]) == "DENY"


def test_borda_only_ranks_pass():
    ranked = borda_rank(
        [
            {"id": "coa-1", "title": "A", "formspace_gate": "REVIEW", "score": 99},
            {"id": "coa-2", "title": "B", "formspace_gate": "PASS", "score": 10},
        ]
    )
    assert ranked == [{"id": "coa-2", "title": "B", "borda_points": 0, "rank": 1}]


def test_fort_stewart_slice_and_schema_names():
    slice_ = fort_stewart_demo_slice()
    assert slice_["ao"]["name"] == "Fort Stewart"
    assert slice_["origin"] == "SYNTHETIC_EXERCISE"
    assert SCHEMA_VERSION == "itdx-task8/v1"
    assert SITUATION_SCHEMA_VERSION == "itdx.situation_assessment/v1"
    assert "decision_authority" in CHANNEL_KEYS
    assert "weather" in CHANNEL_KEYS


def test_website_slice_alias_maps_to_ao():
    from mycosoft_mas.core.routers.itdx_api import _normalize_map_slice

    out = _normalize_map_slice(
        {
            "ao": {},
            "slice": {
                "name": "Fort Stewart",
                "bbox": [-81.70, 31.80, -81.45, 32.05],
                "center": [31.88, -81.61],
            },
            "assets": [],
        }
    )
    assert out["ao"]["name"] == "Fort Stewart"
    assert out["ao"]["bbox"][0] == -81.70


def test_channel_helper_not_supplied_has_no_fake_p():
    from mycosoft_mas.core.routers.itdx_api import _channel

    row = _channel(status="NOT_SUPPLIED", note="missing", agent_id="earth2")
    assert row["p"] is None
    assert row["status"] == "NOT_SUPPLIED"


def test_new_osint_channels_exist_and_google_missing_reason():
    from mycosoft_mas.core.routers.itdx_api import CHANNEL_KEYS, _channel

    assert "traffic" in CHANNEL_KEYS
    assert "pathways" in CHANNEL_KEYS
    assert "navigation" in CHANNEL_KEYS
    row = _channel(
        status="NOT_SUPPLIED",
        reason="google_maps_key_missing",
        note="GOOGLE_MAPS_API_KEY unset",
        capability_class="public_road",
    )
    assert row["p"] is None
    assert row["reason"] == "google_maps_key_missing"
    assert row["capability_class"] == "public_road"


def test_nlm_stub_confidence_never_usable():
    from mycosoft_mas.nlm.inference.service import (
        NLM_STUB_CONFIDENCE,
        is_usable_nlm_confidence,
        nlm_text_is_stub,
    )

    assert NLM_STUB_CONFIDENCE == 0.85
    assert is_usable_nlm_confidence(0.85, "ok", {}) is False
    assert is_usable_nlm_confidence(None, "ok", {}) is False
    assert nlm_text_is_stub("placeholder response") is True


def test_intention_service_module_imports():
    from mycosoft_mas.engines.intention import IntentionService
    from mycosoft_mas.engines.intention.intention_service import IntentionService as Direct

    assert IntentionService is Direct


def test_qualify_seven_roles_not_bound_when_handoff_unbound():
    from mycosoft_mas.agents.itdx_task8_agent import qualify_seven_roles

    roles = [{"bound": True, "error": None} for _ in range(6)]
    roles.append({"bound": False, "error": "secretary_not_invoked"})
    assert qualify_seven_roles(roles) != "BOUND"
    assert qualify_seven_roles(roles) == "DEGRADED"


def test_google_key_never_leaks_in_redacted_url():
    from mycosoft_mas.core.routers.itdx_public_sources import _redact_url

    redacted = _redact_url("https://maps.googleapis.com/maps/api/directions/json?key=SECRETKEY")
    assert "SECRETKEY" not in redacted
    assert "REDACTED" in redacted


def test_google_polyline_decodes_to_lonlat():
    from mycosoft_mas.core.routers.itdx_public_sources import _decode_polyline

    coords = _decode_polyline("_p~iF~ps|U")
    assert len(coords) == 1
    lon, lat = coords[0]
    assert abs(lat - 38.5) < 0.01
    assert abs(lon - (-120.2)) < 0.01


def test_assessment_does_not_http_self():
    from mycosoft_mas.core.routers import itdx_api

    source = open(itdx_api.__file__, encoding="utf-8").read()
    assert "gather_public_osint" in source
    assert "in-process (no HTTP to 127.0.0.1:8001 / self)" in source
    assert "MAS_INTERNAL_URL" not in source
    assert "_get_json(" not in source
