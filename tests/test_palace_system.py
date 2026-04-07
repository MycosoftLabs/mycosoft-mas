"""
Tests for the Unified Memory Palace System.
Created: April 7, 2026

Tests the palace models, AAAK compression, entity codes,
contradiction detector, and retrieval stack.
"""

import pytest
from datetime import datetime


# =========================================================================
# Phase 1: Palace Models
# =========================================================================


class TestPalaceModels:
    """Tests for palace data models."""

    def test_wing_creation(self):
        from mycosoft_mas.memory.palace.models import Wing, SourceType

        wing = Wing(name="mycology", description="Species data", source_type=SourceType.MYCOLOGY)
        assert wing.name == "mycology"
        assert wing.source_type == SourceType.MYCOLOGY

    def test_room_creation(self):
        from mycosoft_mas.memory.palace.models import Room

        room = Room(name="species-identification", wing_name="mycology")
        assert room.name == "species-identification"
        assert room.wing_name == "mycology"

    def test_hall_types(self):
        from mycosoft_mas.memory.palace.models import HallType

        assert len(HallType) == 5
        assert HallType.FACTS.value == "facts"
        assert HallType.EVENTS.value == "events"
        assert HallType.DISCOVERIES.value == "discoveries"
        assert HallType.PREFERENCES.value == "preferences"
        assert HallType.ADVICE.value == "advice"

    def test_drawer_creation(self):
        from mycosoft_mas.memory.palace.models import Drawer, HallType

        drawer = Drawer(
            wing="mycology",
            room="species",
            hall=HallType.FACTS,
            content="Amanita muscaria contains ibotenic acid",
            importance=0.8,
        )
        assert drawer.wing == "mycology"
        assert drawer.hall == HallType.FACTS
        assert drawer.importance == 0.8
        assert not drawer.is_closet

    def test_palace_taxonomy(self):
        from mycosoft_mas.memory.palace.models import PalaceTaxonomy

        tax = PalaceTaxonomy()
        tax.add_entry("mycology", "species", "facts", 5)
        tax.add_entry("mycology", "species", "events", 3)
        tax.add_entry("crep", "flights", "events", 10)

        result = tax.to_dict()
        assert "mycology" in result
        assert "crep" in result
        assert result["mycology"]["total"] == 8
        assert result["crep"]["total"] == 10

    def test_wing_from_db_row(self):
        from mycosoft_mas.memory.palace.models import Wing

        row = {
            "id": None,
            "name": "devices",
            "description": "IoT devices",
            "source_type": "device",
            "properties": {},
            "created_at": None,
        }
        wing = Wing.from_db_row(row)
        assert wing.name == "devices"

    def test_tunnel_from_db_row(self):
        from mycosoft_mas.memory.palace.models import Tunnel

        row = {
            "id": None,
            "room_name": "temperature",
            "wing_a_name": "devices",
            "wing_b_name": "weather",
            "wing_a": None,
            "wing_b": None,
            "strength": 2.5,
            "discovered_at": None,
        }
        tunnel = Tunnel.from_db_row(row)
        assert tunnel.room_name == "temperature"
        assert tunnel.strength == 2.5


# =========================================================================
# Phase 2: AAAK Compression
# =========================================================================


class TestAAKCompression:
    """Tests for AAAK dialect compression and decompression."""

    def test_basic_compression(self):
        from mycosoft_mas.memory.palace.aaak_dialect import AAKEncoder

        encoder = AAKEncoder()
        result = encoder.compress(
            content="We decided to migrate the database from SQLite to PostgreSQL because of scalability concerns.",
            wing="infrastructure",
            room="databases",
            importance=0.9,
        )
        assert result  # Non-empty
        assert len(result) < 200  # Compressed
        assert "infrastructure" in result

    def test_compression_with_entities(self):
        from mycosoft_mas.memory.palace.aaak_dialect import AAKEncoder

        encoder = AAKEncoder()
        result = encoder.compress(
            content="The MycoBrain coordinator detected unusual temperature readings from the BME688 sensor.",
            wing="devices",
            room="mycobrain",
            agent_id="mycobrain_coordinator",
        )
        assert result
        # Should contain some entity codes
        assert "|" in result

    def test_batch_compression(self):
        from mycosoft_mas.memory.palace.aaak_dialect import AAKEncoder

        encoder = AAKEncoder()
        entries = [
            {"content": "Species Amanita muscaria identified in sector 7", "importance": 0.9, "room": "species"},
            {"content": "Temperature anomaly detected at 23.5C", "importance": 0.7, "room": "sensors"},
            {"content": "User prefers dark mode for dashboard", "importance": 0.5, "room": "preferences"},
        ]
        result = encoder.compress_batch(entries, wing="mycology", max_tokens=120)
        assert result
        # Should be under token budget
        token_est = len(result) // 4
        assert token_est <= 150  # Allow some margin

    def test_decoder(self):
        from mycosoft_mas.memory.palace.aaak_dialect import AAKDecoder, AAKEncoder

        encoder = AAKEncoder()
        compressed = encoder.compress(
            content="Breakthrough: new compound discovered in Psilocybe cubensis",
            wing="mycology",
            room="compounds",
            importance=0.95,
        )

        decoder = AAKDecoder()
        result = decoder.decode(compressed)
        assert "entries" in result
        assert len(result["entries"]) > 0

    def test_compression_ratio(self):
        from mycosoft_mas.memory.palace.aaak_dialect import compression_ratio

        original = "This is a much longer text that contains several sentences about various topics including database migrations, agent deployments, and species identification protocols."
        compressed = "ORC|2026-04-07|infra/db\nZ:ORC,DEP|database_migration|★★★★"

        ratio = compression_ratio(original, compressed)
        assert ratio > 1.0  # Compression achieved

    def test_token_estimation(self):
        from mycosoft_mas.memory.palace.aaak_dialect import estimate_tokens

        assert estimate_tokens("Hello world") == max(1, 11 // 4)
        assert estimate_tokens("A" * 400) == 100


# =========================================================================
# Phase 2: Entity Codes
# =========================================================================


class TestEntityCodes:
    """Tests for entity code registry."""

    def test_known_agent_code(self):
        from mycosoft_mas.memory.palace.entity_codes import get_entity_registry

        reg = get_entity_registry()
        assert reg.get_code("orchestrator") == "ORC"
        assert reg.get_code("ceo_agent") == "CEO"

    def test_known_domain_code(self):
        from mycosoft_mas.memory.palace.entity_codes import get_entity_registry

        reg = get_entity_registry()
        assert reg.get_code("postgresql") == "PGS"
        assert reg.get_code("redis") == "RDS"

    def test_auto_generated_code(self):
        from mycosoft_mas.memory.palace.entity_codes import EntityCodeRegistry

        reg = EntityCodeRegistry()
        code = reg.get_code("new_custom_agent")
        assert len(code) == 3
        assert code.isupper()

    def test_reverse_lookup(self):
        from mycosoft_mas.memory.palace.entity_codes import get_entity_registry

        reg = get_entity_registry()
        assert reg.get_entity("ORC") == "orchestrator"
        assert reg.get_entity("CEO") == "ceo_agent"

    def test_manual_registration(self):
        from mycosoft_mas.memory.palace.entity_codes import EntityCodeRegistry

        reg = EntityCodeRegistry()
        reg.register("my_new_agent", "MNA")
        assert reg.get_code("my_new_agent") == "MNA"
        assert reg.get_entity("MNA") == "my_new_agent"


# =========================================================================
# Phase 3: Unified Graph Schema
# =========================================================================


class TestUnifiedGraphSchema:
    """Tests for the unified graph schema with temporal support."""

    def test_unified_node_types(self):
        from mycosoft_mas.memory.graph_schema import NodeType

        # Original types
        assert NodeType.SPECIES.value == "species"
        assert NodeType.CONCEPT.value == "concept"
        # Persistent graph types
        assert NodeType.SYSTEM.value == "system"
        assert NodeType.AGENT.value == "agent"
        assert NodeType.API.value == "api"
        # MINDEX types
        assert NodeType.TRAIT.value == "trait"
        assert NodeType.COMPOUND.value == "compound"
        assert NodeType.HABITAT.value == "habitat"
        # Palace types
        assert NodeType.CREP_EVENT.value == "crep_event"
        assert NodeType.SENSOR.value == "sensor"

    def test_unified_edge_types(self):
        from mycosoft_mas.memory.graph_schema import EdgeType

        # Original types
        assert EdgeType.RELATED_TO.value == "related_to"
        assert EdgeType.CONTAINS.value == "contains"
        # Persistent graph types
        assert EdgeType.DEPENDS_ON.value == "depends_on"
        assert EdgeType.HOSTS.value == "hosts"
        # MINDEX types
        assert EdgeType.IS_A.value == "is_a"
        assert EdgeType.HAS_TRAIT.value == "has_trait"
        # Temporal predicates
        assert EdgeType.DECIDED.value == "decided"
        assert EdgeType.OBSERVED.value == "observed"

    def test_temporal_edge_fields(self):
        from mycosoft_mas.memory.graph_schema import KnowledgeEdge, EdgeType

        edge = KnowledgeEdge(
            id="test-1",
            source_id="node-1",
            target_id="node-2",
            edge_type=EdgeType.CONTAINS,
            valid_from=datetime(2026, 1, 1),
            valid_to=None,
            confidence=0.95,
            source_closet="closet-1",
            source_file="test.py",
        )
        assert edge.valid_from == datetime(2026, 1, 1)
        assert edge.valid_to is None
        assert edge.confidence == 0.95
        assert edge.is_currently_valid  # No end date = currently valid

    def test_temporal_edge_expired(self):
        from mycosoft_mas.memory.graph_schema import KnowledgeEdge, EdgeType

        edge = KnowledgeEdge(
            id="test-2",
            source_id="node-1",
            target_id="node-2",
            edge_type=EdgeType.RELATED_TO,
            valid_from=datetime(2025, 1, 1),
            valid_to=datetime(2025, 6, 1),
        )
        assert not edge.is_currently_valid  # Past end date


# =========================================================================
# Phase 1: Navigator Auto-Classification
# =========================================================================


class TestNavigatorClassification:
    """Tests for auto-classification without database."""

    def test_wing_classification(self):
        from mycosoft_mas.memory.palace.navigator import PalaceNavigator

        nav = PalaceNavigator()

        assert nav._classify_wing("Flight ADS-B data from sector 5", [], "") == "crep"
        assert nav._classify_wing("Species Amanita muscaria found", [], "") == "mycology"
        assert nav._classify_wing("Docker container restarted", [], "") == "infrastructure"
        assert nav._classify_wing("n8n workflow completed", [], "") == "workflows"
        assert nav._classify_wing("Earth2 climate simulation results", [], "") == "weather"

    def test_room_classification(self):
        from mycosoft_mas.memory.palace.navigator import PalaceNavigator

        nav = PalaceNavigator()

        assert nav._classify_room("New mushroom species taxonomy update", "mycology", []) == "species"
        assert nav._classify_room("Chemical compound analysis: alkaloid detected", "mycology", []) == "compounds"
        assert nav._classify_room("Docker container image rebuilt", "infrastructure", []) == "docker"

    def test_hall_classification(self):
        from mycosoft_mas.memory.palace.navigator import PalaceNavigator
        from mycosoft_mas.memory.palace.models import HallType

        nav = PalaceNavigator()

        assert nav._classify_hall("We decided to use PostgreSQL for this") == HallType.FACTS
        assert nav._classify_hall("Task completed successfully, deployment done") == HallType.EVENTS
        assert nav._classify_hall("Discovered a new pattern in the data") == HallType.DISCOVERIES
        assert nav._classify_hall("User prefers dark mode configuration") == HallType.PREFERENCES
        assert nav._classify_hall("I recommend using this approach as best practice") == HallType.ADVICE


# =========================================================================
# Phase 4: Retrieval Stack (unit parts without DB)
# =========================================================================


class TestRetrievalStack:
    """Tests for retrieval stack components that don't need a database."""

    def test_identity_loading(self):
        from mycosoft_mas.memory.palace.retrieval_stack import RetrievalStack

        stack = RetrievalStack()
        identity = stack._load_identity()
        assert "MYCA" in identity
        assert len(identity) < 300  # Should be compact

    def test_wing_detection_from_message(self):
        from mycosoft_mas.memory.palace.retrieval_stack import RetrievalStack

        stack = RetrievalStack()

        assert stack._detect_wing_from_message("Show me the latest flight data") == "crep"
        assert stack._detect_wing_from_message("What mushroom species are in the database?") == "mycology"
        assert stack._detect_wing_from_message("Docker container health check") == "infrastructure"
        assert stack._detect_wing_from_message("Hello, how are you?") is None

    def test_token_estimation(self):
        from mycosoft_mas.memory.palace.retrieval_stack import RetrievalStack

        stack = RetrievalStack()
        assert stack.estimate_tokens("Hello world") >= 1
        assert stack.estimate_tokens("A" * 400) == 100


# =========================================================================
# Phase 8: Merkle Bridge (unit parts)
# =========================================================================


class TestMerkleBridge:
    """Tests for merkle bridge hashing."""

    def test_hash_deterministic(self):
        from mycosoft_mas.memory.palace.merkle_bridge import MerkleBridge

        bridge = MerkleBridge()
        h1 = bridge.compute_hash_hex("test content")
        h2 = bridge.compute_hash_hex("test content")
        assert h1 == h2  # Deterministic

    def test_hash_different_content(self):
        from mycosoft_mas.memory.palace.merkle_bridge import MerkleBridge

        bridge = MerkleBridge()
        h1 = bridge.compute_hash_hex("content A")
        h2 = bridge.compute_hash_hex("content B")
        assert h1 != h2

    def test_hash_length(self):
        from mycosoft_mas.memory.palace.merkle_bridge import MerkleBridge

        bridge = MerkleBridge()
        h = bridge.compute_hash_hex("test")
        assert len(h) == 64  # 32 bytes = 64 hex chars


# =========================================================================
# Integration: Package Imports
# =========================================================================


class TestPalacePackage:
    """Tests that the palace package imports correctly."""

    def test_package_import(self):
        from mycosoft_mas.memory.palace import (
            PalaceNavigator,
            Wing,
            Room,
            Hall,
            HallType,
            Tunnel,
            Closet,
            Drawer,
        )
        assert PalaceNavigator is not None
        assert HallType.FACTS.value == "facts"

    def test_aaak_import(self):
        from mycosoft_mas.memory.palace.aaak_dialect import (
            AAKEncoder,
            AAKDecoder,
            estimate_tokens,
            compression_ratio,
        )
        assert AAKEncoder is not None
        assert AAKDecoder is not None

    def test_entity_codes_import(self):
        from mycosoft_mas.memory.palace.entity_codes import (
            EntityCodeRegistry,
            get_entity_registry,
            AGENT_CODES,
            DOMAIN_CODES,
            EMOTION_CODES,
        )
        assert len(AGENT_CODES) > 40
        assert len(DOMAIN_CODES) > 10
        assert len(EMOTION_CODES) > 10

    def test_contradiction_detector_import(self):
        from mycosoft_mas.memory.palace.contradiction_detector import (
            ContradictionDetector,
            Contradiction,
        )
        assert ContradictionDetector is not None

    def test_retrieval_stack_import(self):
        from mycosoft_mas.memory.palace.retrieval_stack import RetrievalStack
        assert RetrievalStack is not None

    def test_merkle_bridge_import(self):
        from mycosoft_mas.memory.palace.merkle_bridge import MerkleBridge
        assert MerkleBridge is not None

    def test_db_pool_import(self):
        from mycosoft_mas.memory.palace.db_pool import get_shared_pool, close_shared_pool
        assert get_shared_pool is not None

    def test_mixin_has_palace_methods(self):
        from mycosoft_mas.agents.memory_mixin import AgentMemoryMixin

        mixin = AgentMemoryMixin()
        assert hasattr(mixin, "palace_remember")
        assert hasattr(mixin, "palace_recall")
        assert hasattr(mixin, "palace_search")
        assert hasattr(mixin, "wake_up")
        assert hasattr(mixin, "get_tunnels")
        assert hasattr(mixin, "diary_write")
        assert hasattr(mixin, "diary_read")
        assert hasattr(mixin, "check_fact")
        assert hasattr(mixin, "get_timeline")
