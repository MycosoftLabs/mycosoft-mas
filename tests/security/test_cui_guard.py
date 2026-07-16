from __future__ import annotations

import pytest

from mycosoft_mas.security.cui_guard import (
    CUIBoundaryViolation,
    POLICY_SHA256,
    assert_non_cui,
    guard_agent_instance,
    inspect_payload,
)


def test_allows_compliance_metadata_discussion() -> None:
    decision = inspect_payload(
        {
            "content_kind": "compliance_metadata",
            "text": "CUI handling is governed by NIST SP 800-171 and CMMC Level 2.",
            "control_id": "AC.L2-3.1.1",
        }
    )
    assert decision.allowed
    assert decision.policy_sha256 == POLICY_SHA256


@pytest.mark.parametrize(
    "payload,rule",
    [
        ({"text": "CUI//CTI"}, "CUI_MARKING"),
        ({"classification": "CUI"}, "EXPLICIT_CUI_CLASSIFICATION"),
        ({"contains_cui": True}, "EXPLICIT_CUI_FLAG"),
        ({"text": "-----BEGIN PRIVATE KEY-----"}, "PRIVATE_KEY"),
        ({"text": "api_key=AIzaSyA123456789012345678901234567890"}, "GOOGLE_API_KEY"),
    ],
)
def test_blocks_cui_and_secrets(payload: object, rule: str) -> None:
    decision = inspect_payload(payload)
    assert not decision.allowed
    assert rule in decision.reason_codes


def test_exception_never_contains_original_payload() -> None:
    secret = "CUI//CTI highly-sensitive-body"
    with pytest.raises(CUIBoundaryViolation) as exc:
        assert_non_cui(secret, source="test")
    message = str(exc.value)
    assert secret not in message
    assert "fingerprint=" in message


class _DummyAgent:
    def __init__(self) -> None:
        self.agent_id = "dummy"

    async def process_task(self, task: dict) -> dict:
        return {"echo": task}


@pytest.mark.asyncio
async def test_agent_instance_guard_blocks_input_and_output() -> None:
    agent = _DummyAgent()
    guard_agent_instance(agent)

    ok = await agent.process_task({"text": "public compliance metadata"})
    assert ok["echo"]["text"] == "public compliance metadata"

    with pytest.raises(CUIBoundaryViolation):
        await agent.process_task({"classification": "CUI"})


def test_allows_policy_terminology_without_marking() -> None:
    decision = inspect_payload(
        {
            "content_kind": "compliance_metadata",
            "text": "Controlled technical information and covered defense information are defined by DFARS.",
        }
    )
    assert decision.allowed
