import pytest
from fastapi import HTTPException

from mycosoft_mas.core.routers.ethics_training_api import (
    ChatRequest,
    RunScenarioRequest,
    chat_sandbox,
    run_scenario,
)
from mycosoft_mas.ethics.sandbox_manager import SandboxChatError, get_sandbox_manager
from mycosoft_mas.ethics.training_engine import ScenarioRunResult
@pytest.fixture(autouse=True)
def _reset_sandbox_manager():
    manager = get_sandbox_manager()
    manager._sessions.clear()  # noqa: SLF001 - test fixture reset
    yield
    manager._sessions.clear()  # noqa: SLF001 - test fixture reset


@pytest.mark.asyncio
async def test_chat_endpoint_maps_blank_message_to_structured_400(monkeypatch):
    class _FakeManager:
        async def chat(self, session_id, message, audio_base64=None):
            raise SandboxChatError(
                "Message cannot be blank",
                code="blank_message",
                status_code=400,
            )

    monkeypatch.setattr(
        "mycosoft_mas.core.routers.ethics_training_api.get_sandbox_manager",
        lambda: _FakeManager(),
    )

    with pytest.raises(HTTPException) as exc:
        await chat_sandbox("session-id", ChatRequest(message=" "))
    assert exc.value.status_code == 400
    detail = exc.value.detail
    assert detail["error"] == "blank_message"


@pytest.mark.asyncio
async def test_run_endpoint_returns_404_for_missing_session(monkeypatch):
    class _FakeEngine:
        async def run_scenario(self, session_id, scenario_id):
            return ScenarioRunResult(
                session_id=session_id,
                scenario_id=scenario_id,
                prompts_sent=[],
                responses=[],
                completed=False,
                error="Session not found",
                error_code="session_not_found",
            )

    monkeypatch.setattr(
        "mycosoft_mas.core.routers.ethics_training_api.get_training_engine",
        lambda: _FakeEngine(),
    )

    with pytest.raises(HTTPException) as exc:
        await run_scenario(RunScenarioRequest(session_id="missing", scenario_id="adult_corporate_ethics"))

    assert exc.value.status_code == 404
    detail = exc.value.detail
    assert detail["error"] == "session_not_found"

