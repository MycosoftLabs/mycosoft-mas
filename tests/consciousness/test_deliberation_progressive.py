"""
Tests for progressive deliberation - Full-Duplex Voice Phase 4.

Created: February 12, 2026
"""

from types import SimpleNamespace

import pytest

from mycosoft_mas.consciousness.deliberation import DeliberateReasoning


class _FakeWorkingContext:
    def to_prompt_context(self):
        return "working-context"


class _FakeConsciousness:
    _orchestrator_service = None
    _memory_coordinator = None

    async def delegate_to_agent(self, **kwargs):
        return {}


class TestDeliberationProgressive:
    @pytest.mark.asyncio
    async def test_think_progressive_emits_additive_refinement_once(self):
        reasoning = DeliberateReasoning(_FakeConsciousness())
        focus = SimpleNamespace(category="conversation", content="Tell me about weather")

        async def fake_generate_response(*args, **kwargs):
            yield "Fast answer."

        async def fake_check_tools(*args, **kwargs):
            return {"weather_tool": {"summary": "Rain expected later today"}}

        async def fake_check_agents(*args, **kwargs):
            return {}

        reasoning._generate_response = fake_generate_response
        reasoning._check_tool_use = fake_check_tools
        reasoning._check_agent_delegation = fake_check_agents

        tokens = []
        async for token in reasoning.think_progressive(
            input_content="weather update",
            focus=focus,
            working_context=_FakeWorkingContext(),
            world_context={"summary": "clear morning"},
            memories=[],
            soul_context={},
        ):
            tokens.append(token)

        output = "".join(tokens)
        assert "Fast answer." in output
        assert output.count("One more thing:") <= 1

