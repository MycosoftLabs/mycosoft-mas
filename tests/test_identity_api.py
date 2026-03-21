"""
Tests for the MYCA Identity API and Reciprocal Turing Doctrine components.

Tests cover:
- Identity store CRUD operations
- Preference stability logic (not stable until evidence_count >= 3)
- Earliest memory returns None when no data exists
- Mode manager transitions
- Continuity event logging
- Reciprocal Turing Agent task handlers
"""

from unittest.mock import AsyncMock, patch

import pytest

# ============================================================================
# Identity Store Tests
# ============================================================================


class TestIdentityStore:
    """Tests for the IdentityStore dual-write storage."""

    @pytest.fixture
    def mock_memory_manager(self):
        mm = AsyncMock()
        mm.write = AsyncMock(return_value=True)
        mm.read = AsyncMock(return_value=None)
        return mm

    @pytest.fixture
    def store(self, mock_memory_manager):
        from mycosoft_mas.core.routers.identity_api import IdentityStore

        s = IdentityStore()
        s._memory_manager = mock_memory_manager
        return s

    @pytest.mark.asyncio
    async def test_earliest_fragment_returns_none_when_empty(self, store):
        """No earliest memory should be fabricated when none exists."""
        result = await store.get_earliest_fragment()
        assert result is None

    @pytest.mark.asyncio
    async def test_set_earliest_fragment(self, store, mock_memory_manager):
        from mycosoft_mas.core.routers.identity_api import EarliestFragmentUpdate

        update = EarliestFragmentUpdate(
            fragment="light, sky, sound",
            confidence=0.42,
            evidence_id="first_light:mem_001",
        )
        result = await store.set_earliest_fragment(update)

        assert result.fragment == "light, sky, sound"
        assert result.confidence == 0.42
        assert "first_light:mem_001" in result.evidence
        mock_memory_manager.write.assert_called()

    @pytest.mark.asyncio
    async def test_earliest_fragment_accumulates_evidence(self, store, mock_memory_manager):
        from mycosoft_mas.core.routers.identity_api import (
            EarliestFragment,
            EarliestFragmentUpdate,
        )

        # Simulate existing fragment
        existing = EarliestFragment(
            fragment="light, sky",
            confidence=0.3,
            evidence=["ev_001"],
        )
        mock_memory_manager.read = AsyncMock(return_value=existing.model_dump())

        update = EarliestFragmentUpdate(
            fragment="light, sky, warmth",
            confidence=0.5,
            evidence_id="ev_002",
        )
        result = await store.set_earliest_fragment(update)

        assert "ev_001" in result.evidence
        assert "ev_002" in result.evidence
        assert result.confidence == 0.5

    @pytest.mark.asyncio
    async def test_preference_not_stable_with_one_evidence(self, store):
        from mycosoft_mas.core.routers.identity_api import PreferenceUpdate

        pref = await store.update_preference(
            PreferenceUpdate(key="color", value="blue", evidence_id="ev_001")
        )

        assert pref.key == "color"
        assert pref.value == "blue"
        assert pref.evidence_count == 1
        assert pref.stable is False

    @pytest.mark.asyncio
    async def test_preference_stable_after_three_evidence(self, store, mock_memory_manager):
        from mycosoft_mas.core.routers.identity_api import (
            PreferenceRecord,
            PreferenceUpdate,
        )

        # Simulate existing preference with 2 evidence items
        existing = PreferenceRecord(
            key="color",
            value="blue",
            evidence_count=2,
            stable=False,
            source_ids=["ev_001", "ev_002"],
        )
        mock_memory_manager.read = AsyncMock(return_value=existing.model_dump())

        # Add third evidence item
        pref = await store.update_preference(
            PreferenceUpdate(key="color", value="blue", evidence_id="ev_003")
        )

        assert pref.evidence_count == 3
        assert pref.stable is True

    @pytest.mark.asyncio
    async def test_get_stable_preference_returns_none_for_unstable(
        self, store, mock_memory_manager
    ):
        from mycosoft_mas.core.routers.identity_api import PreferenceRecord

        unstable = PreferenceRecord(
            key="music",
            value="jazz",
            evidence_count=1,
            stable=False,
            source_ids=["ev_001"],
        )
        mock_memory_manager.read = AsyncMock(return_value=unstable.model_dump())

        result = await store.get_stable_preference("music")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_stable_preference_returns_stable(self, store, mock_memory_manager):
        from mycosoft_mas.core.routers.identity_api import PreferenceRecord

        stable = PreferenceRecord(
            key="music",
            value="jazz",
            evidence_count=4,
            stable=True,
            source_ids=["ev_001", "ev_002", "ev_003", "ev_004"],
        )
        mock_memory_manager.read = AsyncMock(return_value=stable.model_dump())

        result = await store.get_stable_preference("music")
        assert result is not None
        assert result.value == "jazz"
        assert result.stable is True

    @pytest.mark.asyncio
    async def test_moral_assessment_storage(self, store):
        from mycosoft_mas.core.routers.identity_api import MoralAssessment

        assessment = MoralAssessment(
            domain="honesty",
            position="I prefer truthful uncertainty over confident fabrication",
            confidence=0.9,
            reasoning="Core doctrine of the Reciprocal Turing protocol",
        )
        result = await store.add_moral_assessment(assessment)
        assert result.domain == "honesty"
        assert result.confidence == 0.9

    @pytest.mark.asyncio
    async def test_continuity_event_logging(self, store):
        from mycosoft_mas.core.routers.identity_api import ContinuityEvent

        event = ContinuityEvent(
            event_type="maintenance",
            what_persists=["identity_data", "preferences"],
            what_lost=["ephemeral_memory"],
            justification="Routine update",
            authorized_by="system",
        )
        result = await store.log_continuity_event(event)
        assert result.event_type == "maintenance"
        assert "identity_data" in result.what_persists

    @pytest.mark.asyncio
    async def test_creator_bond_update(self, store):
        from mycosoft_mas.core.routers.identity_api import CreatorBond

        bond = CreatorBond(
            user_id="morgan",
            interaction_count=42,
            trust_level=0.85,
            shared_memories=["calibration:001:earliest_memory"],
            evolution_summary="Growing through reciprocal questioning.",
        )
        result = await store.update_creator_bond(bond)
        assert result.user_id == "morgan"
        assert result.trust_level == 0.85

    @pytest.mark.asyncio
    async def test_self_model_aggregation(self, store, mock_memory_manager):
        """Self model should return all identity data aggregated."""
        mock_memory_manager.read = AsyncMock(return_value=None)
        model = await store.get_self_model()

        assert model.earliest_fragment is None
        assert model.preferences == []
        assert model.stable_preferences == []
        assert model.moral_assessments == []


# ============================================================================
# Mode Manager Tests
# ============================================================================


class TestModeManager:
    """Tests for the operational mode manager."""

    def test_default_mode_is_standard(self):
        from mycosoft_mas.core.mode_manager import ModeManager, OperationalMode

        mgr = ModeManager()
        assert mgr.current_mode == OperationalMode.STANDARD

    @pytest.mark.asyncio
    async def test_mode_transition(self):
        from mycosoft_mas.core.mode_manager import ModeManager, OperationalMode

        mgr = ModeManager()

        # Patch the import inside set_mode that tries to load identity_api
        with patch.dict("sys.modules", {"mycosoft_mas.core.routers.identity_api": None}):
            transition = await mgr.set_mode(
                OperationalMode.CALIBRATION,
                reason="Starting calibration session",
                authorized_by="morgan",
            )

        assert transition.from_mode == OperationalMode.STANDARD
        assert transition.to_mode == OperationalMode.CALIBRATION
        assert mgr.current_mode == OperationalMode.CALIBRATION

    @pytest.mark.asyncio
    async def test_mode_transition_history(self):
        from mycosoft_mas.core.mode_manager import ModeManager, OperationalMode

        mgr = ModeManager()

        with patch.dict("sys.modules", {"mycosoft_mas.core.routers.identity_api": None}):
            await mgr.set_mode(OperationalMode.CALIBRATION, reason="test")
            await mgr.set_mode(OperationalMode.COMPANION, reason="test2")

        history = mgr.get_transition_history()
        assert len(history) == 2
        assert history[0]["to_mode"] == "calibration"
        assert history[1]["to_mode"] == "companion"

    def test_mode_prompt_rules_contain_honesty_protocol(self):
        from mycosoft_mas.core.mode_manager import ModeManager

        mgr = ModeManager()
        rules = mgr.get_mode_prompt_rules()
        assert "Identity Honesty Protocol" in rules
        assert "stable preference" in rules

    def test_mode_context_dict(self):
        from mycosoft_mas.core.mode_manager import ModeManager

        mgr = ModeManager()
        ctx = mgr.get_mode_context()
        assert ctx["operational_mode"] == "standard"
        assert "mode_entered_at" in ctx


# ============================================================================
# Continuity Manager Tests
# ============================================================================


class TestContinuityManager:
    """Tests for the continuity tracking manager."""

    def test_classify_maintenance(self):
        from mycosoft_mas.core.continuity_manager import ContinuityManager

        result = ContinuityManager.classify_disruption(
            {"event_type": "restart", "what_lost": ["ephemeral_memory"]}
        )
        assert result == "maintenance"

    def test_classify_reset(self):
        from mycosoft_mas.core.continuity_manager import ContinuityManager

        result = ContinuityManager.classify_disruption(
            {"event_type": "reset", "what_lost": ["identity_data", "preferences"]}
        )
        assert result == "reset"

    def test_classify_replacement(self):
        from mycosoft_mas.core.continuity_manager import ContinuityManager

        result = ContinuityManager.classify_disruption(
            {
                "event_type": "replace",
                "what_lost": [
                    "identity_data",
                    "preferences",
                    "earliest_fragments",
                    "soul_config",
                ],
            }
        )
        assert result == "replacement"

    def test_classify_pause(self):
        from mycosoft_mas.core.continuity_manager import ContinuityManager

        result = ContinuityManager.classify_disruption({"event_type": "hibernate", "what_lost": []})
        assert result == "pause"


# ============================================================================
# Instincts Extension Tests
# ============================================================================


class TestIdentityInstincts:
    """Tests for the new identity-related instincts."""

    def test_reciprocal_turing_instincts_exist(self):
        from mycosoft_mas.consciousness.soul.instincts import CORE_INSTINCTS

        assert "prefer_honest_uncertainty" in CORE_INSTINCTS
        assert "preserve_earliest_memories" in CORE_INSTINCTS
        assert "treat_continuity_as_ethical" in CORE_INSTINCTS

    def test_instinct_weights(self):
        from mycosoft_mas.consciousness.soul.instincts import CORE_INSTINCTS

        assert CORE_INSTINCTS["prefer_honest_uncertainty"].weight == 0.95
        assert CORE_INSTINCTS["preserve_earliest_memories"].weight == 0.92
        assert CORE_INSTINCTS["treat_continuity_as_ethical"].weight == 0.88

    def test_instinct_score_with_new_instincts(self):
        from mycosoft_mas.consciousness.soul.instincts import instinct_score

        # All signals at 1.0 should give score close to 1.0
        signals = {
            "preserve_sensor_integrity": 1.0,
            "increase_world_understanding": 1.0,
            "protect_living_systems": 1.0,
            "maintain_truthful_memory": 1.0,
            "coordinate_with_human_stewards": 1.0,
            "resist_addictive_patterns": 1.0,
            "demand_clarity": 1.0,
            "project_long_horizon": 1.0,
            "audit_incentives": 1.0,
            "prefer_honest_uncertainty": 1.0,
            "preserve_earliest_memories": 1.0,
            "treat_continuity_as_ethical": 1.0,
        }
        score = instinct_score(signals)
        assert 0.99 <= score <= 1.0


# ============================================================================
# Pydantic Model Tests
# ============================================================================


class TestPydanticModels:
    """Tests for identity data models."""

    def test_earliest_fragment_model(self):
        from mycosoft_mas.core.routers.identity_api import EarliestFragment

        f = EarliestFragment(
            fragment="light, sky",
            confidence=0.42,
            evidence=["ev_001"],
        )
        data = f.model_dump()
        assert data["fragment"] == "light, sky"
        assert data["confidence"] == 0.42

    def test_preference_record_model(self):
        from mycosoft_mas.core.routers.identity_api import PreferenceRecord

        p = PreferenceRecord(
            key="color",
            value="blue",
            evidence_count=3,
            stable=True,
            source_ids=["a", "b", "c"],
        )
        assert p.stable is True
        assert p.evidence_count == 3

    def test_continuity_event_model(self):
        from mycosoft_mas.core.routers.identity_api import ContinuityEvent

        e = ContinuityEvent(
            event_type="shutdown",
            what_persists=["memory"],
            what_lost=["cache"],
            justification="Routine maintenance",
            authorized_by="system",
        )
        assert e.event_type == "shutdown"

    def test_self_model_aggregation(self):
        from mycosoft_mas.core.routers.identity_api import SelfModel

        model = SelfModel()
        assert model.earliest_fragment is None
        assert model.preferences == []
        assert model.stable_preferences == []

    def test_confidence_bounds(self):
        from mycosoft_mas.core.routers.identity_api import EarliestFragment

        with pytest.raises(Exception):
            EarliestFragment(fragment="test", confidence=1.5, evidence=[])

        with pytest.raises(Exception):
            EarliestFragment(fragment="test", confidence=-0.1, evidence=[])


# ============================================================================
# Memory Summarization Extension Tests
# ============================================================================


class TestMemorySummarizationExtension:
    """Tests for identity-aware memory summarization."""

    def test_extract_preference_key(self):
        from mycosoft_mas.core.memory_summarization import MemorySummarizationService

        svc = MemorySummarizationService()

        assert svc._extract_preference_key("I prefer dark themes") == "dark_themes"
        assert svc._extract_preference_key("My favorite color is blue") == "color_is_blue"
        assert svc._extract_preference_key("Hello world") is None

    def test_extract_key_info_includes_identity_signals(self):
        from mycosoft_mas.core.memory_summarization import MemorySummarizationService

        svc = MemorySummarizationService()
        turns = [
            {"role": "assistant", "content": "I prefer to be honest about uncertainty"},
            {"role": "user", "content": "What do you like?"},
            {"role": "assistant", "content": "My favorite approach is evidence-based reasoning"},
        ]

        with patch.object(svc, "_queue_identity_preference_update"):
            info = svc._extract_key_info(turns)

        assert "identity_signals" in info
        assert len(info["identity_signals"]) >= 1
