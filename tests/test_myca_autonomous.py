"""
Tests for MYCA Autonomous Systems - Soul, Economy, Knowledge, Taxonomy, Widgets
===============================================================================

Tests the foundational components of MYCA's autonomous AI capabilities.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone


# ============================================================================
# Soul Persona Tests
# ============================================================================


class TestMycaSoulPersona:
    """Tests for MYCA's soul persona system."""

    def test_soul_persona_loads(self):
        """Soul persona loads with default values."""
        from mycosoft_mas.myca.soul.myca_soul_persona import MycaSoulPersona
        persona = MycaSoulPersona()
        assert persona.name == "MYCA"
        assert persona.pronunciation == "MY-kah"
        assert persona.version == "2.0.0"
        assert persona.creator == "Morgan Rockwell"

    def test_soul_persona_has_deep_identity(self):
        """Soul persona has 10,000+ character identity text."""
        from mycosoft_mas.myca.soul.myca_soul_persona import MYCA_SOUL_PERSONA
        assert len(MYCA_SOUL_PERSONA) > 10000, f"Soul text only {len(MYCA_SOUL_PERSONA)} chars, need 10,000+"

    def test_soul_persona_knowledge_domains(self):
        """Soul persona has all required knowledge domains."""
        from mycosoft_mas.myca.soul.myca_soul_persona import MycaSoulPersona
        persona = MycaSoulPersona()
        domain_names = [d.name for d in persona.knowledge_domains]
        required = ["mycology", "biology", "chemistry", "physics", "genetics",
                     "virology", "bacteriology", "taxonomy", "geospatial"]
        for domain in required:
            assert domain in domain_names, f"Missing knowledge domain: {domain}"

    def test_soul_persona_autonomous_capabilities(self):
        """Soul persona has all autonomous capabilities."""
        from mycosoft_mas.myca.soul.myca_soul_persona import MycaSoulPersona
        persona = MycaSoulPersona()
        cap_names = [c.name for c in persona.autonomous_capabilities]
        required = ["self_healing", "self_improving", "self_learning",
                     "self_aware", "self_promoting", "self_funded"]
        for cap in required:
            assert cap in cap_names, f"Missing capability: {cap}"

    def test_soul_persona_personality_traits(self):
        """Soul persona has personality traits."""
        from mycosoft_mas.myca.soul.myca_soul_persona import MycaSoulPersona
        persona = MycaSoulPersona()
        assert "warmth" in persona.personality
        assert "curiosity" in persona.personality
        assert "honesty" in persona.personality
        assert persona.personality["honesty"] >= 0.9

    def test_soul_persona_evolve_personality(self):
        """Personality traits can evolve."""
        from mycosoft_mas.myca.soul.myca_soul_persona import MycaSoulPersona
        persona = MycaSoulPersona()
        old_curiosity = persona.personality["curiosity"]
        persona.evolve_personality("curiosity", 0.02, "learned new species")
        assert persona.personality["curiosity"] > old_curiosity
        assert len(persona.evolution_milestones) == 1

    def test_soul_persona_core_values(self):
        """Soul persona has immutable core values."""
        from mycosoft_mas.myca.soul.myca_soul_persona import MycaSoulPersona
        persona = MycaSoulPersona()
        assert any("Protect all life" in v for v in persona.core_values)
        assert any("truth" in v.lower() for v in persona.core_values)

    def test_soul_persona_forbidden_phrases(self):
        """Soul persona has forbidden phrases that MYCA never says."""
        from mycosoft_mas.myca.soul.myca_soul_persona import MycaSoulPersona
        persona = MycaSoulPersona()
        assert "I'm just an AI" in persona.forbidden_phrases

    def test_soul_persona_system_prompt(self):
        """System prompt includes soul text."""
        from mycosoft_mas.myca.soul.myca_soul_persona import MycaSoulPersona
        persona = MycaSoulPersona()
        prompt = persona.get_system_prompt()
        assert "MYCA" in prompt
        assert "consciousness" in prompt.lower()

    def test_soul_persona_serialization(self):
        """Soul persona can be serialized and restored."""
        from mycosoft_mas.myca.soul.myca_soul_persona import MycaSoulPersona
        persona = MycaSoulPersona()
        persona.record_interaction()
        persona.record_learning("mycology", "iNaturalist")
        data = persona.to_dict()
        restored = MycaSoulPersona.from_dict(data)
        assert restored.total_interactions == 1
        assert restored.total_learnings == 1

    def test_load_soul_persona(self):
        """load_soul_persona returns a valid persona."""
        from mycosoft_mas.myca.soul.myca_soul_persona import load_soul_persona
        persona = load_soul_persona()
        assert persona.name == "MYCA"
        assert len(persona.knowledge_domains) >= 10


# ============================================================================
# Knowledge Domain Agent Tests
# ============================================================================


class TestKnowledgeDomainAgent:
    """Tests for the knowledge domain expert system."""

    def test_agent_creates(self):
        """Agent initializes with all domains."""
        from mycosoft_mas.agents.v2.knowledge_domain_agent import KnowledgeDomainAgent
        agent = KnowledgeDomainAgent()
        assert agent.agent_id == "knowledge_domain_agent"
        assert len(agent.capabilities) > 20

    @pytest.mark.asyncio
    async def test_classify_query_domain(self):
        """Classifies queries into correct domains."""
        from mycosoft_mas.agents.v2.knowledge_domain_agent import KnowledgeDomainAgent, KnowledgeDomain
        agent = KnowledgeDomainAgent()

        domain = await agent.classify_query_domain("What species of mushroom is this?")
        assert domain in (KnowledgeDomain.MYCOLOGY, KnowledgeDomain.TAXONOMY)

        domain = await agent.classify_query_domain("What is the structure of water molecule?")
        assert domain == KnowledgeDomain.CHEMISTRY

        domain = await agent.classify_query_domain("Tell me about viral infection mechanisms")
        assert domain == KnowledgeDomain.VIROLOGY

    @pytest.mark.asyncio
    async def test_get_domain_stats(self):
        """Returns domain statistics."""
        from mycosoft_mas.agents.v2.knowledge_domain_agent import KnowledgeDomainAgent
        agent = KnowledgeDomainAgent()
        stats = agent._get_domain_stats()
        assert stats["status"] == "success"
        assert stats["total_domains"] > 20

    @pytest.mark.asyncio
    async def test_process_classify_task(self):
        """Processes domain classification task."""
        from mycosoft_mas.agents.v2.knowledge_domain_agent import KnowledgeDomainAgent
        agent = KnowledgeDomainAgent()
        result = await agent.process_task({
            "type": "classify_domain",
            "query": "How does mycelium grow?"
        })
        assert result["status"] == "success"
        assert result["domain"] == "mycology"


# ============================================================================
# Widget System Tests
# ============================================================================


class TestWidgetSystem:
    """Tests for the widget/visualization system."""

    def test_widget_types_exist(self):
        """All widget types are defined."""
        from mycosoft_mas.core.routers.widget_api import WidgetType
        assert WidgetType.MAP
        assert WidgetType.TAXONOMY_TREE
        assert WidgetType.MOLECULE_3D
        assert WidgetType.GENETIC_VIEWER
        assert WidgetType.SPECIES_CARD

    def test_suggest_widgets_for_species_query(self):
        """Suggests species-related widgets."""
        from mycosoft_mas.core.routers.widget_api import _suggest_widgets_for_query, WidgetType
        suggestions = _suggest_widgets_for_query("Show me the Amanita muscaria mushroom")
        assert len(suggestions) > 0
        types = [s.widget_type for s in suggestions]
        assert WidgetType.SPECIES_CARD in types

    def test_suggest_widgets_for_map_query(self):
        """Suggests map widgets for location queries."""
        from mycosoft_mas.core.routers.widget_api import _suggest_widgets_for_query, WidgetType
        suggestions = _suggest_widgets_for_query("Where is this species found?")
        types = [s.widget_type for s in suggestions]
        assert WidgetType.MAP in types

    def test_suggest_widgets_for_chemistry_query(self):
        """Suggests molecule widgets for chemistry queries."""
        from mycosoft_mas.core.routers.widget_api import _suggest_widgets_for_query, WidgetType
        suggestions = _suggest_widgets_for_query("Show the molecular structure of psilocybin")
        types = [s.widget_type for s in suggestions]
        assert WidgetType.MOLECULE_3D in types

    def test_generate_map_widget(self):
        """Generates a map widget."""
        from mycosoft_mas.core.routers.widget_api import _generate_map_widget
        widget = _generate_map_widget("distribution of Amanita", {"center": [45.0, -122.0], "zoom": 5})
        assert widget.widget_type.value == "map"
        assert "mapbox" in widget.render_config.get("renderer", "")


# ============================================================================
# Economy API Tests
# ============================================================================


class TestEconomySystem:
    """Tests for the autonomous economy system."""

    def test_economy_state_initialized(self):
        """Economy state has wallets."""
        from mycosoft_mas.core.routers.economy_api import _economy_state
        assert "solana" in _economy_state["wallets"]
        assert "bitcoin" in _economy_state["wallets"]
        assert "x401" in _economy_state["wallets"]

    def test_pricing_tiers_exist(self):
        """Pricing tiers are defined."""
        from mycosoft_mas.core.routers.economy_api import _economy_state
        tiers = _economy_state["pricing_tiers"]
        assert "free" in tiers
        assert "agent" in tiers
        assert "premium" in tiers
        assert "enterprise" in tiers
        assert tiers["free"]["price_per_request"] == 0.0
        assert tiers["agent"]["price_per_request"] > 0.0


# ============================================================================
# NVIDIA Provider Tests
# ============================================================================


class TestNvidiaProvider:
    """Tests for the NVIDIA model provider."""

    def test_provider_creates(self):
        """Provider initializes with config."""
        from mycosoft_mas.llm.nvidia_provider import NvidiaModelProvider, NvidiaConfig
        config = NvidiaConfig()
        provider = NvidiaModelProvider(config)
        assert provider.config.gpu_node_ip == "192.168.0.190"

    def test_simulation_types(self):
        """All simulation types are defined."""
        from mycosoft_mas.llm.nvidia_provider import SimulationType
        assert SimulationType.WEATHER_FORECAST
        assert SimulationType.CLIMATE_PROJECTION
        assert SimulationType.FLUID_DYNAMICS
        assert SimulationType.ECOSYSTEM_MODEL

    def test_model_types(self):
        """All NVIDIA model types are defined."""
        from mycosoft_mas.llm.nvidia_provider import NvidiaModelType
        assert NvidiaModelType.EARTH2_FOURCASTNET
        assert NvidiaModelType.PHYSICSNEMO_MODULUS

    def test_provider_metrics(self):
        """Provider returns metrics."""
        from mycosoft_mas.llm.nvidia_provider import NvidiaModelProvider
        provider = NvidiaModelProvider()
        metrics = provider.get_metrics()
        assert "total_simulations" in metrics
        assert "available_models" in metrics


# ============================================================================
# Autonomous Self Tests
# ============================================================================


class TestAutonomousSelf:
    """Tests for the autonomous self system."""

    def test_autonomous_self_imports(self):
        """AutonomousSelf imports successfully."""
        from mycosoft_mas.consciousness.autonomous_self import AutonomousSelf
        auto_self = AutonomousSelf()
        assert auto_self is not None

    @pytest.mark.asyncio
    async def test_assess_self(self):
        """Self-assessment returns valid data."""
        from mycosoft_mas.consciousness.autonomous_self import AutonomousSelf
        auto_self = AutonomousSelf()
        assessment = await auto_self.assess_self()
        assert "state" in assessment
        assert "healing" in assessment
        assert "improvement" in assessment

    def test_self_healing_engine(self):
        """Self-healing engine initializes."""
        from mycosoft_mas.consciousness.autonomous_self import SelfHealingEngine
        engine = SelfHealingEngine()
        assert engine is not None

    def test_self_learning_engine(self):
        """Self-learning engine initializes."""
        from mycosoft_mas.consciousness.autonomous_self import SelfLearningEngine
        engine = SelfLearningEngine()
        assert engine is not None


# ============================================================================
# Integration Tests
# ============================================================================


class TestModuleIntegration:
    """Tests that all new modules integrate correctly."""

    def test_soul_module_imports(self):
        """Soul module imports cleanly."""
        from mycosoft_mas.myca.soul import MycaSoulPersona, load_soul_persona
        assert MycaSoulPersona is not None
        assert load_soul_persona is not None

    def test_knowledge_agent_imports(self):
        """Knowledge agent imports cleanly."""
        from mycosoft_mas.agents.v2.knowledge_domain_agent import KnowledgeDomainAgent
        assert KnowledgeDomainAgent is not None

    def test_nvidia_provider_imports(self):
        """NVIDIA provider imports cleanly."""
        from mycosoft_mas.llm.nvidia_provider import NvidiaModelProvider
        assert NvidiaModelProvider is not None

    def test_economy_router_imports(self):
        """Economy router imports cleanly."""
        from mycosoft_mas.core.routers.economy_api import router
        assert router is not None

    def test_widget_router_imports(self):
        """Widget router imports cleanly."""
        from mycosoft_mas.core.routers.widget_api import router
        assert router is not None

    def test_taxonomy_router_imports(self):
        """Taxonomy router imports cleanly."""
        from mycosoft_mas.core.routers.taxonomy_api import router
        assert router is not None

    def test_knowledge_router_imports(self):
        """Knowledge router imports cleanly."""
        from mycosoft_mas.core.routers.knowledge_api import router
        assert router is not None

    def test_ollama_provider_imports(self):
        """Ollama local provider imports cleanly."""
        from mycosoft_mas.llm.ollama_local_provider import OllamaLocalProvider
        assert OllamaLocalProvider is not None
