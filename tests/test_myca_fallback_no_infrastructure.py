"""MYCA chat fallbacks must never leak internal infrastructure to users."""

from mycosoft_mas.core.myca_main import (
    extract_user_message_for_fallback,
    generate_myca_fallback_response,
)

INFRA_MARKERS = (
    "redis",
    "postgresql",
    "qdrant",
    "192.168.",
    "mas vm",
    "proxmox",
    "docker container",
    "rtx 5090",
    "moshi 7b",
    "multiple tiers",
)


def test_extract_user_message_strips_search_isolation_directive():
    enriched = (
        "[Search Isolation]\n"
        "Do not use prior MYCA chat turns or conversation memory to answer.\n\n"
        "[User Message]\n"
        "test"
    )
    assert extract_user_message_for_fallback(enriched) == "test"


def test_test_message_does_not_return_infrastructure_leak():
    enriched = (
        "[Search Isolation]\n"
        "Do not use prior MYCA chat turns or conversation memory to answer.\n\n"
        "[User Message]\n"
        "test"
    )
    response = generate_myca_fallback_response(enriched)
    lower = response.lower()
    assert "i'm here" in lower or "what" in lower
    for marker in INFRA_MARKERS:
        assert marker not in lower, f"infrastructure leak: {marker!r} in {response!r}"


def test_memory_question_is_user_facing_not_ops_detail():
    response = generate_myca_fallback_response("do you remember me?")
    lower = response.lower()
    for marker in INFRA_MARKERS:
        assert marker not in lower
