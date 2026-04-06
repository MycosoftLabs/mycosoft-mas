import pytest

from mycosoft_mas.ethics.sandbox_manager import (
    SandboxChatError,
    get_sandbox_manager,
)
from mycosoft_mas.ethics.vessels import DevelopmentalVessel


class _FakeRouter:
    persona = ""

    async def stream_response(self, message, context, tools=None):
        for token in ["hello", " world"]:
            yield token


class _FallbackRouter:
    persona = ""

    async def stream_response(self, message, context, tools=None):
        from mycosoft_mas.llm.frontier_router import LLM_FALLBACK_MESSAGE

        yield LLM_FALLBACK_MESSAGE


@pytest.fixture(autouse=True)
def _reset_sandbox_manager():
    manager = get_sandbox_manager()
    manager._sessions.clear()  # noqa: SLF001 - test fixture reset
    yield
    manager._sessions.clear()  # noqa: SLF001 - test fixture reset


@pytest.mark.asyncio
async def test_chat_rejects_blank_message():
    manager = get_sandbox_manager()
    session = manager.create_session(
        vessel_stage=DevelopmentalVessel.ADULT,
        capabilities=["text"],
        creator="morgan",
    )

    with pytest.raises(SandboxChatError) as exc:
        await manager.chat(session.session_id, "   ")

    assert exc.value.code == "blank_message"
    assert exc.value.status_code == 400
    assert session.conversation_history == []


@pytest.mark.asyncio
async def test_chat_records_assistant_only_on_real_response(monkeypatch):
    manager = get_sandbox_manager()
    session = manager.create_session(
        vessel_stage=DevelopmentalVessel.ADULT,
        capabilities=["text"],
        creator="morgan",
    )

    monkeypatch.setattr("mycosoft_mas.llm.frontier_router.FrontierLLMRouter", _FakeRouter)

    response = await manager.chat(session.session_id, "Test message")

    assert response == "hello world"
    assert session.conversation_history[-2]["role"] == "user"
    assert session.conversation_history[-1] == {"role": "assistant", "content": "hello world"}


@pytest.mark.asyncio
async def test_chat_raises_when_router_returns_fallback(monkeypatch):
    manager = get_sandbox_manager()
    session = manager.create_session(
        vessel_stage=DevelopmentalVessel.ADULT,
        capabilities=["text"],
        creator="morgan",
    )

    monkeypatch.setattr("mycosoft_mas.llm.frontier_router.FrontierLLMRouter", _FallbackRouter)

    with pytest.raises(SandboxChatError) as exc:
        await manager.chat(session.session_id, "Trigger fallback")

    assert exc.value.code == "llm_provider_failure"
    assert exc.value.status_code == 503
    # user prompt is preserved for audit; assistant fallback is not recorded
    assert len(session.conversation_history) == 1
    assert session.conversation_history[0]["role"] == "user"

