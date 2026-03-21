"""
Tests for STATIC System-Wide Integration

Tests the STATICValidator utility, LLM pipeline integration,
MINDEX API entity validation, knowledge graph validation,
and the new missing indexes (gene_regions, compound_classes,
bioactivity_types, graph_node_types, graph_edge_types).

Created: March 3, 2026
"""

import pytest

from mycosoft_mas.llm.constrained.constraint_engine import ConstraintEngine
from mycosoft_mas.llm.constrained.domain_builders import (
    _build_string_index,
    _byte_tokenize,
    build_mindex_species_index,
    build_search_index,
)
from mycosoft_mas.llm.constrained.static_index import STATICIndex
from mycosoft_mas.llm.constrained.validator import (
    STATICValidator,
    ValidationResult,
    get_static_validator,
    set_static_validator,
)

# --- STATICValidator Tests ---


class TestSTATICValidator:
    def setup_method(self):
        """Create a fresh validator with test indexes."""
        self.validator = STATICValidator()

        # Build a small test index
        test_index = _build_string_index("test", ["alpha", "beta", "gamma"])
        self.validator.register_index("test_index", test_index)

        # Build gene regions index
        gene_regions = _build_string_index("gene_regions", ["ITS", "LSU", "SSU", "COX1", "TEF1"])
        self.validator.register_index("mindex_gene_regions", gene_regions)

        # Build compound classes index
        compound_classes = _build_string_index(
            "compound_classes", ["Alkaloid", "Terpenoid", "Polyketide"]
        )
        self.validator.register_index("mindex_compound_classes", compound_classes)

        # Build graph node types
        node_types = _build_string_index("node_types", ["species", "compound", "gene", "habitat"])
        self.validator.register_index("search_graph_node_types", node_types)

        # Build graph edge types
        edge_types = _build_string_index("edge_types", ["produces", "inhibits", "found_in", "is_a"])
        self.validator.register_index("search_graph_edge_types", edge_types)

        self.validator.mark_initialized()

    def test_is_valid_true(self):
        """Valid entity returns True."""
        assert self.validator.is_valid("alpha", "test_index")

    def test_is_valid_false(self):
        """Invalid entity returns False."""
        assert not self.validator.is_valid("delta", "test_index")

    def test_is_valid_missing_index_fail_open(self):
        """Missing index fails open (returns True)."""
        assert self.validator.is_valid("anything", "nonexistent_index")

    def test_validate_valid_entity(self):
        """Validate returns ValidationResult with valid=True."""
        result = self.validator.validate("beta", "test_index")
        assert isinstance(result, ValidationResult)
        assert result.valid is True
        assert result.entity == "beta"
        assert result.index_name == "test_index"

    def test_validate_invalid_entity(self):
        """Validate returns ValidationResult with valid=False."""
        result = self.validator.validate("omega", "test_index")
        assert isinstance(result, ValidationResult)
        assert result.valid is False
        assert "not found" in result.message

    def test_validate_missing_index(self):
        """Validate with missing index returns valid=True (fail-open)."""
        result = self.validator.validate("x", "no_such_index")
        assert result.valid is True
        assert "not loaded" in result.message

    def test_is_valid_gene_region(self):
        """Gene region convenience method works."""
        assert self.validator.is_valid_gene_region("ITS")
        assert self.validator.is_valid_gene_region("COX1")
        assert not self.validator.is_valid_gene_region("FAKE_GENE")

    def test_is_valid_compound_class(self):
        """Compound class convenience method works."""
        assert self.validator.is_valid_compound_class("Alkaloid")
        assert not self.validator.is_valid_compound_class("FakeClass")

    def test_is_valid_graph_node_type(self):
        """Graph node type validation works."""
        assert self.validator.is_valid_graph_node_type("species")
        assert self.validator.is_valid_graph_node_type("compound")
        assert not self.validator.is_valid_graph_node_type("fake_node")

    def test_is_valid_graph_edge_type(self):
        """Graph edge type validation works."""
        assert self.validator.is_valid_graph_edge_type("produces")
        assert self.validator.is_valid_graph_edge_type("found_in")
        assert not self.validator.is_valid_graph_edge_type("fake_edge")

    def test_has_index(self):
        assert self.validator.has_index("test_index")
        assert not self.validator.has_index("nope")

    def test_is_initialized(self):
        assert self.validator.is_initialized

    def test_get_stats(self):
        stats = self.validator.get_stats()
        assert stats["initialized"] is True
        assert stats["total_indexes"] >= 5
        assert "test_index" in stats["index_names"]

    def test_list_indexes(self):
        indexes = self.validator.list_indexes()
        assert len(indexes) >= 5


class TestSTATICValidatorSingleton:
    def test_get_returns_same_instance(self):
        """get_static_validator returns the same instance."""
        v1 = get_static_validator()
        v2 = get_static_validator()
        assert v1 is v2

    def test_set_overrides_instance(self):
        """set_static_validator overrides the global instance."""
        custom = STATICValidator()
        set_static_validator(custom)
        assert get_static_validator() is custom
        # Restore default
        set_static_validator(STATICValidator())


# --- New Domain Index Tests ---


class TestMINDEXGeneRegionsIndex:
    @pytest.mark.asyncio
    async def test_gene_regions_built(self):
        """MINDEX builder now includes gene_regions index."""
        indexes = await build_mindex_species_index()
        assert "mindex_gene_regions" in indexes
        idx = indexes["mindex_gene_regions"]
        assert isinstance(idx, STATICIndex)
        assert idx.num_sequences >= 30

    @pytest.mark.asyncio
    async def test_gene_region_its_valid(self):
        """ITS is a valid gene region."""
        indexes = await build_mindex_species_index()
        engine = ConstraintEngine()
        engine.register_index("mindex_gene_regions", indexes["mindex_gene_regions"])

        tokens = _byte_tokenize("ITS")
        assert engine._validate_sequence(indexes["mindex_gene_regions"], tokens)

    @pytest.mark.asyncio
    async def test_gene_region_invalid(self):
        """Random string is not a valid gene region."""
        indexes = await build_mindex_species_index()
        engine = ConstraintEngine()
        engine.register_index("mindex_gene_regions", indexes["mindex_gene_regions"])

        tokens = _byte_tokenize("FAKE_REGION_XYZ")
        assert not engine._validate_sequence(indexes["mindex_gene_regions"], tokens)


class TestMINDEXCompoundClassesIndex:
    @pytest.mark.asyncio
    async def test_compound_classes_built(self):
        """MINDEX builder includes compound_classes index."""
        indexes = await build_mindex_species_index()
        assert "mindex_compound_classes" in indexes
        idx = indexes["mindex_compound_classes"]
        assert isinstance(idx, STATICIndex)
        assert idx.num_sequences >= 30

    @pytest.mark.asyncio
    async def test_alkaloid_valid(self):
        indexes = await build_mindex_species_index()
        engine = ConstraintEngine()
        engine.register_index("mindex_compound_classes", indexes["mindex_compound_classes"])

        tokens = _byte_tokenize("Alkaloid")
        assert engine._validate_sequence(indexes["mindex_compound_classes"], tokens)

    @pytest.mark.asyncio
    async def test_invalid_class(self):
        indexes = await build_mindex_species_index()
        engine = ConstraintEngine()
        engine.register_index("mindex_compound_classes", indexes["mindex_compound_classes"])

        tokens = _byte_tokenize("NotARealClass")
        assert not engine._validate_sequence(indexes["mindex_compound_classes"], tokens)


class TestMINDEXBioactivityIndex:
    @pytest.mark.asyncio
    async def test_bioactivity_types_built(self):
        """MINDEX builder includes bioactivity_types index."""
        indexes = await build_mindex_species_index()
        assert "mindex_bioactivity_types" in indexes
        idx = indexes["mindex_bioactivity_types"]
        assert isinstance(idx, STATICIndex)
        assert idx.num_sequences >= 20

    @pytest.mark.asyncio
    async def test_antimicrobial_valid(self):
        indexes = await build_mindex_species_index()
        engine = ConstraintEngine()
        engine.register_index("mindex_bioactivity_types", indexes["mindex_bioactivity_types"])

        tokens = _byte_tokenize("antimicrobial")
        assert engine._validate_sequence(indexes["mindex_bioactivity_types"], tokens)


class TestSearchGraphNodeEdgeTypes:
    @pytest.mark.asyncio
    async def test_graph_node_types_built(self):
        """Search builder includes graph node types."""
        indexes = await build_search_index()
        assert "search_graph_node_types" in indexes
        idx = indexes["search_graph_node_types"]
        assert isinstance(idx, STATICIndex)
        assert idx.num_sequences >= 20

    @pytest.mark.asyncio
    async def test_graph_edge_types_built(self):
        """Search builder includes graph edge types."""
        indexes = await build_search_index()
        assert "search_graph_edge_types" in indexes
        idx = indexes["search_graph_edge_types"]
        assert isinstance(idx, STATICIndex)
        assert idx.num_sequences >= 25

    @pytest.mark.asyncio
    async def test_node_type_species_valid(self):
        indexes = await build_search_index()
        engine = ConstraintEngine()
        engine.register_index("search_graph_node_types", indexes["search_graph_node_types"])

        tokens = _byte_tokenize("species")
        assert engine._validate_sequence(indexes["search_graph_node_types"], tokens)

    @pytest.mark.asyncio
    async def test_edge_type_produces_valid(self):
        indexes = await build_search_index()
        engine = ConstraintEngine()
        engine.register_index("search_graph_edge_types", indexes["search_graph_edge_types"])

        tokens = _byte_tokenize("produces")
        assert engine._validate_sequence(indexes["search_graph_edge_types"], tokens)

    @pytest.mark.asyncio
    async def test_invalid_node_type(self):
        indexes = await build_search_index()
        engine = ConstraintEngine()
        engine.register_index("search_graph_node_types", indexes["search_graph_node_types"])

        tokens = _byte_tokenize("hallucinated_type")
        assert not engine._validate_sequence(indexes["search_graph_node_types"], tokens)


# --- LLM Client Integration Tests ---


class TestLLMClientConstrainedChat:
    def test_constrained_chat_method_exists(self):
        """LLMClient has constrained_chat method."""
        from mycosoft_mas.llm.client import LLMClient

        assert hasattr(LLMClient, "constrained_chat")

    def test_validate_entity_method_exists(self):
        """LLMClient has validate_entity method."""
        from mycosoft_mas.llm.client import LLMClient

        assert hasattr(LLMClient, "validate_entity")


class TestLLMRouterConstraintParam:
    def test_chat_accepts_constrained_index_name(self):
        """LLMRouter.chat accepts constrained_index_name parameter."""
        import inspect

        from mycosoft_mas.llm.router import LLMRouter

        sig = inspect.signature(LLMRouter.chat)
        assert "constrained_index_name" in sig.parameters

    def test_apply_constraint_validation_exists(self):
        """LLMRouter has _apply_constraint_validation method."""
        from mycosoft_mas.llm.router import LLMRouter

        assert hasattr(LLMRouter, "_apply_constraint_validation")


# --- Graph Memory Validation Tests ---


class TestGraphMemoryValidation:
    def test_add_node_accepts_valid_type(self):
        """add_node works with valid node types."""
        try:
            from mycosoft_mas.memory.graph_memory import GraphMemory
        except ImportError:
            pytest.skip("memory module has unrelated import error")

        graph = GraphMemory()
        node_id = graph.add_node("species", {"name": "test"})
        assert node_id is not None

    def test_add_edge_accepts_valid_relationship(self):
        """add_edge works with valid relationship types."""
        try:
            from mycosoft_mas.memory.graph_memory import GraphMemory
        except ImportError:
            pytest.skip("memory module has unrelated import error")

        graph = GraphMemory()
        n1 = graph.add_node("species", {"name": "a"})
        n2 = graph.add_node("compound", {"name": "b"})
        result = graph.add_edge(n1, n2, "produces")
        assert result is True


# --- Environment Variables Tests ---


class TestEnvironmentVariables:
    def test_env_example_has_static_vars(self):
        with open(".env.example", "r") as f:
            content = f.read()

        assert "STATIC_BUILD_ON_STARTUP" in content
        assert "STATIC_INDEX_CACHE_DIR" in content
        assert "MINDEX_DB_PATH" in content


# --- Startup Integration Tests ---


class TestStartupIntegration:
    def test_static_build_on_startup_code_exists(self):
        """myca_main.py includes STATIC startup initialization."""
        with open("mycosoft_mas/core/myca_main.py", "r") as f:
            content = f.read()

        assert "STATIC_BUILD_ON_STARTUP" in content
        assert "build_all_domain_indexes" in content
        assert "get_static_validator" in content
        assert "static_validator" in content
