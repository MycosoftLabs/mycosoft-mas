"""
Tests for STATIC Domain Constraint Builders

Tests the domain-specific constraint index builders that pull data from
all MAS subsystems (MINDEX, CREP, NLM, taxonomy, agents, devices,
signals, users, MycoBrain) and universal domain builders (biosphere,
environment, infrastructure, geospatial, observation, search).

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
    build_biosphere_index,
    build_crep_index,
    build_device_index,
    build_environment_index,
    build_geospatial_index,
    build_infrastructure_index,
    build_nlm_index,
    build_observation_index,
    build_search_index,
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


# --- Universal Domain Builder Tests (v2) ---


class TestBiosphereIndex:
    @pytest.mark.asyncio
    async def test_biosphere_index_builds(self):
        indexes = await build_biosphere_index()

        assert "bio_kingdoms" in indexes
        assert "bio_phyla" in indexes
        assert "bio_animalia_classes" in indexes
        assert "bio_organism_forms" in indexes
        assert "bio_conservation_status" in indexes
        assert "bio_ecological_roles" in indexes
        assert "bio_trophic_levels" in indexes

        # 12 kingdoms/domains of life
        assert indexes["bio_kingdoms"].num_sequences == 12
        # 7 trophic levels
        assert indexes["bio_trophic_levels"].num_sequences == 7

    @pytest.mark.asyncio
    async def test_biosphere_contains_all_life(self):
        indexes = await build_biosphere_index()
        # Verify major organism forms are constrained
        forms_idx = indexes["bio_organism_forms"]
        for form in ["mammal", "insect", "bird", "fish", "mushroom",
                      "bacterium", "virus", "tree"]:
            assert forms_idx.start_mask[ord(form[0])], (
                f"Organism form '{form}' start char not in index"
            )


class TestEnvironmentIndex:
    @pytest.mark.asyncio
    async def test_environment_index_builds(self):
        indexes = await build_environment_index()

        assert "env_atmospheric" in indexes
        assert "env_oceanic" in indexes
        assert "env_terrestrial" in indexes
        assert "env_space" in indexes
        assert "env_biological" in indexes
        assert "env_units" in indexes
        assert "env_data_quality" in indexes
        assert "env_temporal" in indexes

        # Should have substantial entry counts
        assert indexes["env_atmospheric"].num_sequences >= 30
        assert indexes["env_units"].num_sequences >= 50

    @pytest.mark.asyncio
    async def test_environment_units_valid(self):
        indexes = await build_environment_index()
        idx = indexes["env_units"]
        # 'c' for celsius should be valid start
        assert idx.start_mask[ord("c")]


class TestInfrastructureIndex:
    @pytest.mark.asyncio
    async def test_infrastructure_index_builds(self):
        indexes = await build_infrastructure_index()

        assert "infra_ai_model_types" in indexes
        assert "infra_frontier_models" in indexes
        assert "infra_robot_types" in indexes
        assert "infra_vehicle_types" in indexes
        assert "infra_app_types" in indexes
        assert "infra_org_types" in indexes
        assert "infra_protocols" in indexes

        # Should have many AI model types
        assert indexes["infra_ai_model_types"].num_sequences >= 30
        # Should have major frontier models
        assert indexes["infra_frontier_models"].num_sequences >= 20

    @pytest.mark.asyncio
    async def test_frontier_models_valid(self):
        indexes = await build_infrastructure_index()
        idx = indexes["infra_frontier_models"]
        # 'c' for claude_* should be valid start
        assert idx.start_mask[ord("c")]
        # 'm' for myca should be valid start
        assert idx.start_mask[ord("m")]


class TestGeospatialIndex:
    @pytest.mark.asyncio
    async def test_geospatial_index_builds(self):
        indexes = await build_geospatial_index()

        assert "geo_biomes" in indexes
        assert "geo_climate_zones" in indexes
        assert "geo_ocean_zones" in indexes
        assert "geo_habitats" in indexes

        # Many biomes
        assert indexes["geo_biomes"].num_sequences >= 30
        # Koppen-Geiger + descriptive
        assert indexes["geo_climate_zones"].num_sequences >= 30


class TestObservationIndex:
    @pytest.mark.asyncio
    async def test_observation_index_builds(self):
        indexes = await build_observation_index()

        assert "obs_methods" in indexes
        assert "obs_data_formats" in indexes
        assert "obs_compression" in indexes
        assert "obs_storage_tiers" in indexes
        assert "obs_pipeline_stages" in indexes

        # Many data formats
        assert indexes["obs_data_formats"].num_sequences >= 40
        # Many compression algorithms
        assert indexes["obs_compression"].num_sequences >= 20


class TestSearchIndex:
    @pytest.mark.asyncio
    async def test_search_index_builds(self):
        indexes = await build_search_index()

        assert "search_query_types" in indexes
        assert "search_result_types" in indexes
        assert "search_ranking_signals" in indexes
        assert "search_entity_types" in indexes

        # Many entity types (the master MINDEX taxonomy)
        assert indexes["search_entity_types"].num_sequences >= 40
        # Many query types
        assert indexes["search_query_types"].num_sequences >= 20

    @pytest.mark.asyncio
    async def test_search_entity_types_comprehensive(self):
        indexes = await build_search_index()
        idx = indexes["search_entity_types"]
        # 's' for species, signal_stream, sensor, etc.
        assert idx.start_mask[ord("s")]
        # 'a' for ai_model, agent, application, etc.
        assert idx.start_mask[ord("a")]


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

        # All 14 domains should succeed (live API failures are non-fatal)
        assert len(report.domains_built) == 14
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
            "biosphere", "environment", "infrastructure",
            "geospatial", "observation", "search",
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

    @pytest.mark.asyncio
    async def test_validate_biosphere_kingdom(self):
        """Validate biosphere kingdoms against constraint index."""
        from mycosoft_mas.llm.constrained.constraint_engine import ConstraintEngine

        indexes = await build_biosphere_index()
        engine = ConstraintEngine()
        engine.register_index("bio_kingdoms", indexes["bio_kingdoms"])

        tokens = _byte_tokenize("Animalia")
        assert engine._validate_sequence(indexes["bio_kingdoms"], tokens)

        tokens = _byte_tokenize("Fungi")
        assert engine._validate_sequence(indexes["bio_kingdoms"], tokens)

        tokens = _byte_tokenize("FakeKingdom")
        assert not engine._validate_sequence(indexes["bio_kingdoms"], tokens)

    @pytest.mark.asyncio
    async def test_validate_climate_zone(self):
        """Validate Koppen-Geiger climate zones."""
        from mycosoft_mas.llm.constrained.constraint_engine import ConstraintEngine

        indexes = await build_geospatial_index()
        engine = ConstraintEngine()
        engine.register_index("geo_climate_zones", indexes["geo_climate_zones"])

        tokens = _byte_tokenize("Cfa")
        assert engine._validate_sequence(indexes["geo_climate_zones"], tokens)

        tokens = _byte_tokenize("XYZ")
        assert not engine._validate_sequence(indexes["geo_climate_zones"], tokens)

    @pytest.mark.asyncio
    async def test_validate_frontier_model(self):
        """Validate frontier model names against constraint index."""
        from mycosoft_mas.llm.constrained.constraint_engine import ConstraintEngine

        indexes = await build_infrastructure_index()
        engine = ConstraintEngine()
        engine.register_index("infra_frontier_models", indexes["infra_frontier_models"])

        tokens = _byte_tokenize("claude_opus")
        assert engine._validate_sequence(indexes["infra_frontier_models"], tokens)

        tokens = _byte_tokenize("myca")
        assert engine._validate_sequence(indexes["infra_frontier_models"], tokens)

        tokens = _byte_tokenize("hallucinated_model_xyz")
        assert not engine._validate_sequence(indexes["infra_frontier_models"], tokens)

    @pytest.mark.asyncio
    async def test_validate_data_format(self):
        """Validate data format identifiers."""
        from mycosoft_mas.llm.constrained.constraint_engine import ConstraintEngine

        indexes = await build_observation_index()
        engine = ConstraintEngine()
        engine.register_index("obs_data_formats", indexes["obs_data_formats"])

        tokens = _byte_tokenize("parquet")
        assert engine._validate_sequence(indexes["obs_data_formats"], tokens)

        tokens = _byte_tokenize("fasta")
        assert engine._validate_sequence(indexes["obs_data_formats"], tokens)

        tokens = _byte_tokenize("nonexistent_format")
        assert not engine._validate_sequence(indexes["obs_data_formats"], tokens)
