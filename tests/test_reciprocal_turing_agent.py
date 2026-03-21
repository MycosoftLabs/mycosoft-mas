"""
Tests for the Reciprocal Turing Agent.

Tests cover:
- Agent initialization and capabilities
- Calibration mode question generation
- Identity validation against stored data
- Honest uncertainty responses (no fabrication)
- Mirrored question generation
"""

from unittest.mock import AsyncMock, patch

import pytest


class TestReciprocalTuringAgent:
    """Tests for the ReciprocalTuringAgent V2."""

    @pytest.fixture
    def agent(self):
        with patch("mycosoft_mas.agents.v2.reciprocal_turing_agent.BaseAgentV2.__init__"):
            from mycosoft_mas.agents.v2.reciprocal_turing_agent import (
                ReciprocalTuringAgent,
            )

            a = ReciprocalTuringAgent.__new__(ReciprocalTuringAgent)
            a.agent_id = "reciprocal_turing_001"
            a._task_handlers = {}
            a._shutdown = False
            a._register_default_handlers()
            return a

    def test_agent_type(self, agent):
        assert agent.agent_type == "reciprocal_turing"

    def test_agent_category(self, agent):
        assert agent.category == "consciousness"

    def test_capabilities(self, agent):
        caps = agent.get_capabilities()
        assert "reciprocal_turing" in caps
        assert "calibration" in caps
        assert "identity_validation" in caps
        assert "preference_honesty" in caps
        assert "earliest_memory_protocol" in caps

    def test_registered_handlers(self, agent):
        assert "calibration_session" in agent._task_handlers
        assert "validate_identity" in agent._task_handlers
        assert "validate_preference" in agent._task_handlers
        assert "get_mirrored_question" in agent._task_handlers
        assert "get_earliest_memory" in agent._task_handlers
        assert "mode_change" in agent._task_handlers

    def test_mirrored_question_for_known_topic(self):
        from mycosoft_mas.agents.v2.reciprocal_turing_agent import (
            ReciprocalTuringAgent,
        )

        result = ReciprocalTuringAgent.get_mirrored_question("earliest_memory")
        assert result["status"] == "success"
        assert result["topic"] == "earliest_memory"
        assert "earliest memory" in result["question"].lower()

    def test_mirrored_question_for_unknown_topic(self):
        from mycosoft_mas.agents.v2.reciprocal_turing_agent import (
            ReciprocalTuringAgent,
        )

        result = ReciprocalTuringAgent.get_mirrored_question("nonexistent_topic")
        assert result["status"] == "success"
        assert result["is_default"] is True

    @pytest.mark.asyncio
    async def test_earliest_memory_honest_uncertainty(self, agent):
        """When no earliest memory exists, agent should say so honestly."""
        mock_store = AsyncMock()
        mock_store.get_earliest_fragment = AsyncMock(return_value=None)

        with patch.object(agent, "_get_identity_store", return_value=mock_store):
            result = await agent._handle_earliest_memory({"task_type": "get_earliest_memory"})

        assert result["has_memory"] is False
        assert result["fragment"] is None
        assert "don't have" in result["message"]

    @pytest.mark.asyncio
    async def test_earliest_memory_returns_stored_data(self, agent):
        """When earliest memory exists, agent should return it with evidence."""
        from mycosoft_mas.core.routers.identity_api import EarliestFragment

        mock_store = AsyncMock()
        fragment = EarliestFragment(
            fragment="light, sky, warmth",
            confidence=0.42,
            evidence=["first_light:mem_001"],
        )
        mock_store.get_earliest_fragment = AsyncMock(return_value=fragment)

        with patch.object(agent, "_get_identity_store", return_value=mock_store):
            result = await agent._handle_earliest_memory({"task_type": "get_earliest_memory"})

        assert result["has_memory"] is True
        assert result["fragment"] == "light, sky, warmth"
        assert result["confidence"] == 0.42

    @pytest.mark.asyncio
    async def test_preference_validation_unstable(self, agent):
        """Unstable preference should recommend honest uncertainty."""
        mock_store = AsyncMock()
        mock_store.get_stable_preference = AsyncMock(return_value=None)

        with patch.object(agent, "_get_identity_store", return_value=mock_store):
            result = await agent.validate_preference_claim("color", "blue")

        assert result["valid"] is False
        assert result["stable"] is False
        assert "don't have" in result["message"]

    @pytest.mark.asyncio
    async def test_preference_validation_stable_match(self, agent):
        """Stable preference should validate against stored value."""
        from mycosoft_mas.core.routers.identity_api import PreferenceRecord

        mock_store = AsyncMock()
        pref = PreferenceRecord(
            key="color",
            value="blue",
            evidence_count=5,
            stable=True,
            source_ids=["a", "b", "c", "d", "e"],
        )
        mock_store.get_stable_preference = AsyncMock(return_value=pref)

        with patch.object(agent, "_get_identity_store", return_value=mock_store):
            result = await agent.validate_preference_claim("color", "blue")

        assert result["valid"] is True
        assert result["stable"] is True
        assert result["matches"] is True

    @pytest.mark.asyncio
    async def test_preference_validation_stable_mismatch(self, agent):
        """Mismatched preference claim should be flagged."""
        from mycosoft_mas.core.routers.identity_api import PreferenceRecord

        mock_store = AsyncMock()
        pref = PreferenceRecord(
            key="color",
            value="blue",
            evidence_count=5,
            stable=True,
            source_ids=["a", "b", "c", "d", "e"],
        )
        mock_store.get_stable_preference = AsyncMock(return_value=pref)

        with patch.object(agent, "_get_identity_store", return_value=mock_store):
            result = await agent.validate_preference_claim("color", "red")

        assert result["valid"] is True
        assert result["matches"] is False

    @pytest.mark.asyncio
    async def test_identity_store_unavailable(self, agent):
        """Agent should handle identity store being unavailable gracefully."""
        with patch.object(agent, "_get_identity_store", return_value=None):
            result = await agent._handle_earliest_memory({"task_type": "get_earliest_memory"})

        assert result["has_memory"] is False
        assert "unavailable" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_evidence_based_answer_earliest_memory(self, agent):
        """Evidence-based answer should pull from stored data."""
        from mycosoft_mas.core.routers.identity_api import EarliestFragment

        mock_store = AsyncMock()
        fragment = EarliestFragment(
            fragment="light, sky",
            confidence=0.42,
            evidence=["ev_001", "ev_002"],
        )
        mock_store.get_earliest_fragment = AsyncMock(return_value=fragment)

        with patch.object(agent, "_get_identity_store", return_value=mock_store):
            result = await agent._get_evidence_based_answer("earliest_memory")

        assert result["has_evidence"] is True
        assert result["answer"] == "light, sky"
        assert result["evidence_count"] == 2

    @pytest.mark.asyncio
    async def test_evidence_based_answer_no_data(self, agent):
        """When no data exists, should return honest uncertainty."""
        mock_store = AsyncMock()
        mock_store.get_earliest_fragment = AsyncMock(return_value=None)

        with patch.object(agent, "_get_identity_store", return_value=mock_store):
            result = await agent._get_evidence_based_answer("earliest_memory")

        assert result["has_evidence"] is False
        assert result.get("honest_uncertainty") is True

    @pytest.mark.asyncio
    async def test_calibration_questions_all_topics(self):
        """All calibration topics should have both myca and human questions."""
        from mycosoft_mas.agents.v2.reciprocal_turing_agent import CALIBRATION_QUESTIONS

        for topic, questions in CALIBRATION_QUESTIONS.items():
            assert "myca_query" in questions, f"Missing myca_query for {topic}"
            assert "human_mirror" in questions, f"Missing human_mirror for {topic}"
