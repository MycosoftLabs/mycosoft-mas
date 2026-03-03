"""
Tests for STATIC Domain Constraint Builders

Tests the domain-specific constraint index builders that pull data from
all MAS subsystems (MINDEX, CREP, NLM, taxonomy, agents, devices,
signals, users, MycoBrain) and build STATIC indexes for each.

Created: March 3, 2026
"""

import asyncio

import numpy as np
import pytest

from mycosoft_mas.llm.constrained.static_index import STATICIndex
from mycosoft_mas.llm.constrained.domain_builders import (
    DOMAIN_BUILDERS,
    DomainIndexReport,
    MINDEXConstraintConfig,
    _build_string_index,
    _byte_tokenize,
    build_agent_index,
    build_all_domain_indexes,
    build_crep_index,
    build_device_index,
    build_nlm_index,
    build_signal_index,
    build_taxonomy_index,
    build_user_index,
)


# --- Utility Tests ---


class TestByteTokenizer:
    def test_ascii_string(self):
        tokens = _byte_tokenize("hello")
        assert tokens == [104, 101, 108, 108, 111]

    def test_empty_string(self):
        tokens = _byte_tokenize("")
        assert tokens == []

    def test_unicode_string(self):
        tokens = _byte_tokenize("Agáricus")
        assert len(tokens) > 0
        assert all(0 <= t <= 255 for t in tokens)


class TestBuildStringIndex:
    def test_basic_build(self):
        index = _build_string_index("test", ["cat", "car", "dog"])
        assert isinstance(index, STATICIndex)
        assert index.num_sequences == 3
        assert index.num_states > 0

    def test_deduplication(self):
        index = _build_string_index("test", ["cat", "cat", "dog", "dog", "cat"])
        assert index.num_sequences == 2

    def test_filters_empty_strings(self):
        index = _build_string_index("test", ["cat", "", "dog", ""])
        assert index.num_sequences == 2

    def test_raises_on_empty(self):
        with pytest.raises(ValueError, match="No strings"):
            _build_string_index("test", [])


# --- Domain Builder Tests ---


class TestAgentIndex:
    @pytest.mark.asyncio
    async def test_agent_index_builds(self):
        indexes = await build_agent_index()

        assert "agent_ids" in indexes
        assert "agent_categories" in indexes
        assert "agent_capabilities" in indexes

        # Verify known agents are indexed
        agent_idx = indexes["agent_ids"]
        assert agent_idx.num_sequences > 50  # We have 60+ known agents

        # Categories should match CLAUDE.md
        cat_idx = indexes["agent_categories"]
        assert cat_idx.num_sequences == 14

    @pytest.mark.asyncio
    async def test_agent_ids_contain_known_agents(self):
        indexes = await build_agent_index()
        # Verify that "orchestrator" is a valid constrained sequence
        tokens = _byte_tokenize("orchestrator")
        # We can check start_mask for 'o' = 111
        assert indexes["agent_ids"].start_mask[ord("o")]


class TestDeviceIndex:
    @pytest.mark.asyncio
    async def test_device_index_builds(self):
        indexes = await build_device_index()

        assert "device_types" in indexes
        assert "sensor_types" in indexes
        assert "mycobrain_modes" in indexes
        assert "stimulation_types" in indexes
        assert "electrode_ids" in indexes

        # 64 electrodes
        assert indexes["electrode_ids"].num_sequences == 64

        # 14 device types
        assert indexes["device_types"].num_sequences == 14

        # 20 sensor types
        assert indexes["sensor_types"].num_sequences == 20


class TestSignalIndex:
    @pytest.mark.asyncio
    async def test_signal_index_builds(self):
        indexes = await build_signal_index()

        assert "signal_types" in indexes
        assert "sdr_encoding_types" in indexes
        assert "fci_channels" in indexes
        assert "signal_features" in indexes

        # 4 quadrants * 16 channels = 64 FCI channels
        assert indexes["fci_channels"].num_sequences == 64

    @pytest.mark.asyncio
    async def test_signal_types_valid(self):
        indexes = await build_signal_index()
        idx = indexes["signal_types"]
        # 'm' for mycelium_electrical should be valid start
        assert idx.start_mask[ord("m")]


class TestNLMIndex:
    @pytest.mark.asyncio
    async def test_nlm_index_builds(self):
        indexes = await build_nlm_index()

        assert "nlm_prediction_types" in indexes
        assert "nlm_entity_types" in indexes
        assert "nlm_capabilities" in indexes

        assert indexes["nlm_prediction_types"].num_sequences == 15
        assert indexes["nlm_entity_types"].num_sequences == 15
        assert indexes["nlm_capabilities"].num_sequences == 10


class TestCREPIndex:
    @pytest.mark.asyncio
    async def test_crep_domains_always_available(self):
        """CREP domain names should always build even without live API."""
        indexes = await build_crep_index()

        assert "crep_domains" in indexes
        assert indexes["crep_domains"].num_sequences == 7


class TestTaxonomyIndex:
    @pytest.mark.asyncio
    async def test_taxonomy_builds_kingdoms(self):
        """Taxonomy should at minimum include default kingdoms."""
        indexes = await build_taxonomy_index()

        assert "taxonomy_kingdoms" in indexes
        # At least the 5 default kingdoms
        assert indexes["taxonomy_kingdoms"].num_sequences >= 5


class TestUserIndex:
    @pytest.mark.asyncio
    async def test_user_index_builds(self):
        indexes = await build_user_index()

        assert "user_roles" in indexes
        assert "user_permissions" in indexes
        assert "access_levels" in indexes

        assert indexes["user_roles"].num_sequences == 15
        assert indexes["user_permissions"].num_sequences == 17
        assert indexes["access_levels"].num_sequences == 6


# --- Master Builder Tests ---


class TestBuildAllDomains:
    @pytest.mark.asyncio
    async def test_build_all_domains(self):
        """Build all domain indexes concurrently."""
        report = await build_all_domain_indexes()

        assert isinstance(report, DomainIndexReport)
        assert len(report.indexes) > 0
        assert report.total_states > 0
        assert report.total_memory_mb > 0
        assert report.build_time_ms > 0

        # All 8 domains should succeed (live API failures are non-fatal)
        assert len(report.domains_built) == 8
        assert len(report.domains_failed) == 0

    @pytest.mark.asyncio
    async def test_build_subset_of_domains(self):
        """Build only selected domains."""
        report = await build_all_domain_indexes(domains=["agents", "nlm"])

        assert len(report.domains_built) == 2
        assert "agents" in report.domains_built
        assert "nlm" in report.domains_built

        # Should have agent and NLM indexes but not CREP
        assert any(k.startswith("agent_") for k in report.indexes)
        assert any(k.startswith("nlm_") for k in report.indexes)
        assert not any(k.startswith("crep_") for k in report.indexes)

    @pytest.mark.asyncio
    async def test_report_to_dict(self):
        report = await build_all_domain_indexes(domains=["signals"])

        d = report.to_dict()
        assert "total_indexes" in d
        assert "domains_built" in d
        assert "total_states" in d
        assert "total_memory_mb" in d
        assert "build_time_ms" in d
        assert "indexes" in d


class TestDomainBuildersRegistry:
    def test_all_domains_registered(self):
        """Verify all expected domains are in the DOMAIN_BUILDERS map."""
        expected = {
            "mindex", "taxonomy", "crep", "nlm",
            "agents", "devices", "signals", "users",
        }
        assert set(DOMAIN_BUILDERS.keys()) == expected

    def test_all_builders_are_coroutines(self):
        """Each builder should be an async function."""
        import asyncio

        for name, builder in DOMAIN_BUILDERS.items():
            assert asyncio.iscoroutinefunction(builder), (
                f"Builder for '{name}' is not async"
            )


# --- Constraint Validation Integration Tests ---


class TestConstraintValidation:
    @pytest.mark.asyncio
    async def test_validate_known_agent(self):
        """Validate that known agent IDs pass constraint check."""
        from mycosoft_mas.llm.constrained.constraint_engine import ConstraintEngine

        indexes = await build_agent_index()
        engine = ConstraintEngine()
        engine.register_index("agent_ids", indexes["agent_ids"])

        # orchestrator should be valid
        tokens = _byte_tokenize("orchestrator")
        assert engine._validate_sequence(indexes["agent_ids"], tokens)

        # random-garbage-agent should NOT be valid
        tokens = _byte_tokenize("random-garbage-agent")
        assert not engine._validate_sequence(indexes["agent_ids"], tokens)

    @pytest.mark.asyncio
    async def test_validate_known_device_type(self):
        """Validate device types against constraint index."""
        from mycosoft_mas.llm.constrained.constraint_engine import ConstraintEngine

        indexes = await build_device_index()
        engine = ConstraintEngine()
        engine.register_index("device_types", indexes["device_types"])

        tokens = _byte_tokenize("mycobrain")
        assert engine._validate_sequence(indexes["device_types"], tokens)

        tokens = _byte_tokenize("nonexistent_device")
        assert not engine._validate_sequence(indexes["device_types"], tokens)

    @pytest.mark.asyncio
    async def test_validate_nlm_prediction_type(self):
        """Validate NLM prediction types against constraint index."""
        from mycosoft_mas.llm.constrained.constraint_engine import ConstraintEngine

        indexes = await build_nlm_index()
        engine = ConstraintEngine()
        engine.register_index("nlm_prediction_types", indexes["nlm_prediction_types"])

        tokens = _byte_tokenize("species_identification")
        assert engine._validate_sequence(indexes["nlm_prediction_types"], tokens)

        tokens = _byte_tokenize("hallucinated_prediction")
        assert not engine._validate_sequence(indexes["nlm_prediction_types"], tokens)

    @pytest.mark.asyncio
    async def test_validate_electrode_id(self):
        """Validate FCI electrode IDs are properly constrained."""
        from mycosoft_mas.llm.constrained.constraint_engine import ConstraintEngine

        indexes = await build_device_index()
        engine = ConstraintEngine()
        engine.register_index("electrode_ids", indexes["electrode_ids"])

        tokens = _byte_tokenize("E000")
        assert engine._validate_sequence(indexes["electrode_ids"], tokens)

        tokens = _byte_tokenize("E063")
        assert engine._validate_sequence(indexes["electrode_ids"], tokens)

        tokens = _byte_tokenize("E999")
        assert not engine._validate_sequence(indexes["electrode_ids"], tokens)

    @pytest.mark.asyncio
    async def test_validate_fci_channel(self):
        """Validate FCI recording channels."""
        from mycosoft_mas.llm.constrained.constraint_engine import ConstraintEngine

        indexes = await build_signal_index()
        engine = ConstraintEngine()
        engine.register_index("fci_channels", indexes["fci_channels"])

        tokens = _byte_tokenize("NE-CH00")
        assert engine._validate_sequence(indexes["fci_channels"], tokens)

        tokens = _byte_tokenize("XX-CH99")
        assert not engine._validate_sequence(indexes["fci_channels"], tokens)
