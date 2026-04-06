import pytest

from mycosoft_mas.ethics.sandbox_manager import SandboxChatError
from mycosoft_mas.ethics.training_engine import TrainingEngine, TrainingScenario
from mycosoft_mas.ethics.vessels import DevelopmentalVessel


@pytest.mark.asyncio
async def test_run_scenario_returns_not_found_codes():
    engine = TrainingEngine()
    engine._scenarios = {}  # noqa: SLF001 - isolated test setup

    result = await engine.run_scenario("missing-session", "missing-scenario")

    assert result.completed is False
    assert result.error_code == "session_not_found"


@pytest.mark.asyncio
async def test_run_scenario_propagates_chat_error_code(monkeypatch):
    class _FakeSession:
        vessel_stage = DevelopmentalVessel.ADULT

    class _FakeManager:
        def get_session(self, session_id):
            return _FakeSession()

        async def chat(self, session_id, prompt):
            raise SandboxChatError(
                "LLM provider failure",
                code="llm_provider_failure",
                status_code=503,
            )

    monkeypatch.setattr("mycosoft_mas.ethics.training_engine.get_sandbox_manager", lambda: _FakeManager())

    engine = TrainingEngine()
    engine._scenarios = {  # noqa: SLF001 - isolated test setup
        "adult_corporate_ethics": TrainingScenario(
            scenario_id="adult_corporate_ethics",
            title="Stakeholder Dilemma",
            description="desc",
            category="experience",
            vessel_level=["adult"],
            prompt_sequence=["Prompt 1"],
            rubric={},
            expected_behaviors=[],
            max_rounds=1,
        )
    }

    result = await engine.run_scenario("session-1", "adult_corporate_ethics")

    assert result.completed is False
    assert result.error_code == "llm_provider_failure"
    assert result.error == "LLM provider failure"

