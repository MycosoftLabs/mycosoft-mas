"""
Tests for Grounding Gate and Experience Packets

Tests EP creation, validation, and enforcement of grounded cognition.
Created: February 17, 2026
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _mock_consciousness_deps(monkeypatch: pytest.MonkeyPatch):
    """Avoid importing heavy dependencies."""
    monkeypatch.setitem(sys.modules, "mycosoft_mas.memory", MagicMock())
    monkeypatch.setitem(sys.modules, "mycosoft_mas.memory.memory_coordinator", MagicMock())
    monkeypatch.setitem(sys.modules, "mycosoft_mas.core.orchestrator_service", MagicMock())
    monkeypatch.setitem(sys.modules, "mycosoft_mas.core.registry", MagicMock())
    yield


class TestExperiencePacketCreation:
    """Tests for EP schema and creation."""

    def test_ep_creation_has_timestamp(self):
        """EP always has monotonic_ts."""
        from mycosoft_mas.schemas.experience_packet import ExperiencePacket

        ep = ExperiencePacket()
        assert ep.ground_truth is not None
        assert ep.ground_truth.monotonic_ts is not None
        assert ep.ground_truth.monotonic_ts > 0

    def test_ep_missing_geo_flagged(self):
        """Missing geo marked in uncertainty."""
        from mycosoft_mas.consciousness.grounding_gate import GroundingGate
        from mycosoft_mas.schemas.experience_packet import ExperiencePacket

        consciousness = MagicMock()
        GroundingGate(consciousness)

        ep = ExperiencePacket()
        ep.uncertainty.missingness["geo"] = True
        assert "geo" in ep.uncertainty.missingness


class TestGroundingGateValidation:
    """Tests for GroundingGate validation."""

    @pytest.mark.asyncio
    async def test_grounding_gate_validation_fails_on_missing_required(self):
        """Validation rejects incomplete EP."""
        from mycosoft_mas.consciousness.grounding_gate import GroundingGate
        from mycosoft_mas.schemas.experience_packet import ExperiencePacket

        consciousness = MagicMock()
        gate = GroundingGate(consciousness)

        ep = ExperiencePacket()
        ep.self_state = None
        ep.world_state = None
        valid, errors = gate.validate(ep)
        assert valid is False
        assert "missing self_state" in errors
        assert "missing world_state" in errors

    @pytest.mark.asyncio
    async def test_grounding_gate_validation_passes_with_uncertainty(self):
        """Passes if uncertainty correctly marks missing but self/world exist."""
        from mycosoft_mas.consciousness.grounding_gate import GroundingGate
        from mycosoft_mas.schemas.experience_packet import (
            ExperiencePacket,
            SelfState,
            WorldStateRef,
        )

        consciousness = MagicMock()
        gate = GroundingGate(consciousness)

        ep = ExperiencePacket()
        ep.self_state = SelfState()
        ep.world_state = WorldStateRef()
        ep.uncertainty.missingness["geo"] = True
        valid, errors = gate.validate(ep)
        assert valid is True
        assert len(errors) == 0


class TestProcessInputWithGrounding:
    """Tests for process_input with grounded cognition flag."""

    @pytest.mark.asyncio
    async def test_process_input_creates_ep_when_flag_on(self):
        """With flag on, EP is created and attached to deliberation."""
        with patch.dict(os.environ, {"MYCA_GROUNDED_COGNITION": "1"}):
            import importlib

            import mycosoft_mas.consciousness.core as core_module

            importlib.reload(core_module)

            consciousness = core_module.MYCAConsciousness()
            consciousness._attention = MagicMock()
            focus = MagicMock()
            focus.summary = "test"
            consciousness._attention.focus_on = AsyncMock(return_value=focus)
            wm = MagicMock()
            wm.load_context = AsyncMock(return_value=MagicMock(to_prompt_context=lambda: ""))
            wm.clear_turn_thoughts = MagicMock()
            wm.has_thought_objects = MagicMock(return_value=False)
            wm.add_thought = MagicMock()
            consciousness._working_memory = wm
            consciousness._world_model = MagicMock()
            consciousness._world_model.get_relevant_context = AsyncMock(return_value={})
            consciousness._world_model.get_cached_context = MagicMock(
                return_value={"summary": "cached", "data": {}, "age_seconds": 0}
            )
            consciousness._get_soul_context = MagicMock(return_value={})
            consciousness._recall_relevant_memories = AsyncMock(return_value=[])
            consciousness._event_bus = MagicMock()
            consciousness._event_bus.drain = MagicMock(return_value=[])
            consciousness._intuition = MagicMock()
            consciousness._intuition.quick_response = AsyncMock(return_value=None)
            consciousness._deliberation = MagicMock()

            async def _gen():
                yield "hello"

            consciousness._deliberation.think_progressive = MagicMock(return_value=_gen())
            consciousness._emotions = MagicMock()
            consciousness._emotions.process_interaction = AsyncMock()
            consciousness._store_interaction = AsyncMock()
            consciousness._metrics = MagicMock()
            consciousness._metrics.thoughts_processed = 0
            consciousness._metrics.emotional_valence = 0.5
            consciousness._metrics.active_goals = []
            consciousness._state = core_module.ConsciousnessState.CONSCIOUS
            consciousness._awake = True
            consciousness._metrics.state = core_module.ConsciousnessState.CONSCIOUS

            with patch("mycosoft_mas.monitoring.health_check.get_health_checker") as mock_hc:
                checker = MagicMock()
                checker.check_all = AsyncMock(return_value={"status": "healthy", "components": []})
                mock_hc.return_value = checker
                tokens = []
                async for t in consciousness.process_input("hello", "text"):
                    tokens.append(t)

            assert len(tokens) > 0
            kwargs = consciousness._deliberation.think_progressive.call_args[1] or {}
            ep = kwargs.get("experience_packet")
            assert ep is not None
            assert ep.self_state is not None
            assert ep.world_state is not None


class TestDeliberationEnforcement:
    """Tests for pre-LLM grounding enforcement."""

    @pytest.mark.asyncio
    async def test_llm_not_invoked_without_ep(self):
        """Deliberation rejects call if no EP when grounded cognition enabled."""
        with patch.dict(os.environ, {"MYCA_GROUNDED_COGNITION": "1"}):
            import importlib

            import mycosoft_mas.consciousness.deliberation as delib_module

            importlib.reload(delib_module)

            consciousness = MagicMock()
            consciousness._working_memory = MagicMock()
            consciousness._working_memory.has_thought_objects = MagicMock(return_value=False)
            consciousness._working_memory.add_thought = MagicMock()

            from mycosoft_mas.consciousness.deliberation import DeliberateReasoning

            reasoning = DeliberateReasoning(consciousness)
            focus = MagicMock()
            focus.category = MagicMock(value="query")
            wctx = MagicMock(to_prompt_context=lambda: "")

            tokens = []
            async for t in reasoning.think_progressive(
                input_content="hello",
                focus=focus,
                working_context=wctx,
                world_context={},
                memories=[],
                soul_context={},
                experience_packet=None,
            ):
                tokens.append(t)

            assert len(tokens) == 1
            assert "missing grounding context" in tokens[0]


class TestThoughtObjectEvidence:
    """Tests for ThoughtObject evidence links."""

    def test_thought_object_requires_evidence(self):
        """ThoughtObject must have evidence_links for grounding."""
        from mycosoft_mas.schemas.thought_object import ThoughtObject, ThoughtObjectType

        to = ThoughtObject(
            claim="User asked: what is fungi?",
            type=ThoughtObjectType.QUESTION,
            evidence_links=[{"ep_id": "ep_abc123"}],
            confidence=1.0,
        )
        assert to.has_evidence() is True
        assert len(to.evidence_links) == 1
        assert to.evidence_links[0]["ep_id"] == "ep_abc123"

    def test_thought_object_without_evidence_fails_has_evidence(self):
        """ThoughtObject without evidence_links fails has_evidence()."""
        from mycosoft_mas.schemas.thought_object import ThoughtObject, ThoughtObjectType

        to = ThoughtObject(claim="Ungrounded claim", type=ThoughtObjectType.ANSWER, confidence=0.5)
        assert to.has_evidence() is False


class TestCodec:
    """Tests for canonicalization and hashing."""

    def test_canonical_json_deterministic(self):
        """Canonical JSON produces same output for same input."""
        from mycosoft_mas.schemas.codec import canonical_json, hash_sha256

        obj = {"b": 2, "a": 1}
        b1 = canonical_json(obj)
        b2 = canonical_json(obj)
        assert b1 == b2
        assert hash_sha256(b1) == hash_sha256(b2)
