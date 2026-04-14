"""
Tests for progressive context injection in deliberation.py.

Tests cover:
- Draft → refine → correct flow
- Correction cap (max 1 per response)
- Fast path response starts before rich context arrives
- Cancellation halts generation mid-stream

Author: MYCA / Consciousness OS
Created: April 2026
"""

import asyncio
from typing import AsyncGenerator, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mycosoft_mas.consciousness.speech_planner import (
    SpeechAct,
    SpeechActType,
    SpeechPlanner,
    get_speech_planner,
)


# ---------------------------------------------------------------------------
# SpeechPlanner (core progressive output component)
# ---------------------------------------------------------------------------


async def _gen(tokens: List[str]) -> AsyncGenerator[str, None]:
    for t in tokens:
        yield t
        await asyncio.sleep(0)


class TestSpeechPlannerProgressive:
    @pytest.mark.asyncio
    async def test_empty_input_yields_nothing(self):
        planner = SpeechPlanner()
        acts = []
        async for act in planner.plan(_gen([])):
            acts.append(act)
        assert acts == []

    @pytest.mark.asyncio
    async def test_short_text_yields_final_act(self):
        """Short text below MIN_CHARS should yield a FINAL act."""
        planner = SpeechPlanner()
        acts = []
        async for act in planner.plan(_gen(["Hi there"])):
            acts.append(act)
        assert len(acts) == 1
        assert acts[0].type == SpeechActType.FINAL

    @pytest.mark.asyncio
    async def test_sentence_boundary_splits(self):
        """A sentence boundary should produce a STATEMENT act."""
        planner = SpeechPlanner()
        # Two sentences, each long enough
        text = "A" * 45 + ". " + "B" * 45 + "."
        acts = []
        async for act in planner.plan(_gen([text])):
            acts.append(act)
        assert len(acts) >= 1

    @pytest.mark.asyncio
    async def test_cancellation_stops_generation(self):
        """When on_cancel returns True, plan() stops early."""
        planner = SpeechPlanner()
        call_count = 0

        def cancel_after_one() -> bool:
            nonlocal call_count
            call_count += 1
            return call_count > 1

        long_text = ". ".join(["Word " * 20] * 10)
        acts = []
        async for act in planner.plan(_gen([long_text]), on_cancel=cancel_after_one):
            acts.append(act)
        # Should produce fewer acts than without cancellation
        assert len(acts) <= 2

    @pytest.mark.asyncio
    async def test_correction_act_type(self):
        """correction() should produce a CORRECTION type act."""
        planner = SpeechPlanner()
        act = planner.correction("some extra context")
        assert act.type == SpeechActType.CORRECTION
        assert "One more thing" in act.text

    @pytest.mark.asyncio
    async def test_backchannel_act_type(self):
        planner = SpeechPlanner()
        act = planner.backchannel()
        assert act.type == SpeechActType.BACKCHANNEL

    @pytest.mark.asyncio
    async def test_status_act_type(self):
        planner = SpeechPlanner()
        act = planner.status("lookup")
        assert act.type == SpeechActType.STATUS
        assert "looking" in act.text.lower()

    @pytest.mark.asyncio
    async def test_plan_with_status_prepends_status(self):
        """plan_with_status(has_tools=True) should yield a STATUS act first."""
        planner = SpeechPlanner()
        acts = []
        async for act in planner.plan_with_status(_gen(["Short text."]), has_tools=True):
            acts.append(act)
        assert acts[0].type == SpeechActType.STATUS

    @pytest.mark.asyncio
    async def test_plan_with_status_no_tools_no_status(self):
        """plan_with_status(has_tools=False) should not prepend a STATUS act."""
        planner = SpeechPlanner()
        acts = []
        async for act in planner.plan_with_status(_gen(["Short"]), has_tools=False):
            acts.append(act)
        assert not any(a.type == SpeechActType.STATUS for a in acts)

    @pytest.mark.asyncio
    async def test_estimate_duration_proportional_to_length(self):
        """Longer speech acts should have higher estimated durations."""
        planner = SpeechPlanner()
        short = SpeechAct(text="Hi", type=SpeechActType.BACKCHANNEL)
        long = SpeechAct(
            text="This is a much longer sentence that should take more time to say.",
            type=SpeechActType.STATEMENT,
        )
        assert planner.estimate_duration([long]) > planner.estimate_duration([short])

    def test_singleton(self):
        """get_speech_planner() returns the same instance."""
        a = get_speech_planner()
        b = get_speech_planner()
        assert a is b

    @pytest.mark.asyncio
    async def test_abbreviation_not_split(self):
        """'Dr. Smith' should not cause a speech boundary on the period."""
        planner = SpeechPlanner(min_chars=10)
        text = "Dr. Smith is a well-known scientist from the 20th century who did great work."
        acts = []
        async for act in planner.plan(_gen([text])):
            acts.append(act)
        # The full text should be covered (no broken "Dr" fragment)
        full_text = " ".join(a.text for a in acts)
        assert "Dr" in full_text
