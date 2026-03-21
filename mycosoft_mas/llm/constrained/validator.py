"""
STATIC Entity Validator

Central validation utility for the entire Mycosoft MAS.
Provides system-wide entity validation against STATIC constraint indexes,
so any component can verify entity references before using them.

Usage:
    from mycosoft_mas.llm.constrained.validator import get_static_validator

    validator = get_static_validator()

    # Validate a single entity
    if validator.is_valid("Agaricus bisporus", "mindex_species_scientific"):
        # Safe to use

    # Validate with suggestion
    result = validator.validate("Agaricus bisorus", "mindex_species_scientific")
    if not result.valid:
        print(f"Invalid. Did you mean: {result.suggestions}")

    # Validate a gene region parameter
    if validator.is_valid_gene_region("ITS"):
        # Safe for SQL query

Created: March 3, 2026
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from mycosoft_mas.llm.constrained.constraint_engine import ConstraintEngine
from mycosoft_mas.llm.constrained.static_index import STATICIndex

logger = logging.getLogger(__name__)


# Byte-level tokenizer matching the one in domain_builders.py
def _byte_tokenize(s: str) -> List[int]:
    return list(s.encode("utf-8"))


@dataclass
class ValidationResult:
    """Result of validating an entity against a STATIC index."""

    valid: bool
    entity: str
    index_name: str
    suggestions: List[str] = field(default_factory=list)
    message: str = ""


class STATICValidator:
    """
    System-wide entity validator backed by STATIC constraint indexes.

    Provides convenient methods for validating entities against any
    registered constraint index. Used by API endpoints, agents, memory
    systems, and the LLM pipeline to prevent hallucinated references.
    """

    def __init__(self, engine: Optional[ConstraintEngine] = None):
        self._engine = engine or ConstraintEngine()
        self._initialized = False
        logger.info("STATICValidator created")

    @property
    def engine(self) -> ConstraintEngine:
        return self._engine

    @property
    def is_initialized(self) -> bool:
        """Whether domain indexes have been built and loaded."""
        return self._initialized and len(self._engine.list_indexes()) > 0

    def mark_initialized(self) -> None:
        self._initialized = True

    def register_index(self, name: str, index: STATICIndex) -> None:
        """Register a constraint index for validation."""
        self._engine.register_index(name, index)

    def list_indexes(self) -> Dict[str, Any]:
        """List all registered indexes."""
        return self._engine.list_indexes()

    def has_index(self, name: str) -> bool:
        """Check if a named index exists."""
        return self._engine.get_index(name) is not None

    def is_valid(self, entity: str, index_name: str) -> bool:
        """
        Check if an entity string is valid in the given index.

        This is the fastest validation path — a simple boolean check.

        Args:
            entity: The entity string to validate.
            index_name: Name of the constraint index to check against.

        Returns:
            True if the entity exists in the index, False otherwise.
            Returns True if the index doesn't exist (fail-open for safety).
        """
        index = self._engine.get_index(index_name)
        if index is None:
            # Fail-open: if the index isn't loaded, allow the entity
            logger.debug(f"Index '{index_name}' not loaded, allowing entity '{entity}'")
            return True

        tokens = _byte_tokenize(entity)
        return self._engine._validate_sequence(index, tokens)

    def validate(self, entity: str, index_name: str) -> ValidationResult:
        """
        Validate an entity with detailed result including suggestions.

        Args:
            entity: The entity string to validate.
            index_name: Name of the constraint index.

        Returns:
            ValidationResult with valid flag, entity, and suggestions.
        """
        index = self._engine.get_index(index_name)
        if index is None:
            return ValidationResult(
                valid=True,
                entity=entity,
                index_name=index_name,
                message=f"Index '{index_name}' not loaded, entity allowed by default",
            )

        tokens = _byte_tokenize(entity)
        is_valid = self._engine._validate_sequence(index, tokens)

        if is_valid:
            return ValidationResult(
                valid=True,
                entity=entity,
                index_name=index_name,
                message="Entity is valid",
            )

        return ValidationResult(
            valid=False,
            entity=entity,
            index_name=index_name,
            message=f"Entity '{entity}' not found in index '{index_name}'",
        )

    # --- Convenience methods for common validation patterns ---

    def is_valid_gene_region(self, gene_region: str) -> bool:
        """Validate a gene region identifier (ITS, LSU, COX1, etc.)."""
        return self.is_valid(gene_region, "mindex_gene_regions")

    def is_valid_compound_class(self, compound_class: str) -> bool:
        """Validate a compound class identifier (Alkaloid, Terpenoid, etc.)."""
        return self.is_valid(compound_class, "mindex_compound_classes")

    def is_valid_bioactivity(self, bioactivity: str) -> bool:
        """Validate a bioactivity type (antimicrobial, antitumor, etc.)."""
        return self.is_valid(bioactivity, "mindex_bioactivity_types")

    def is_valid_species(self, name: str, name_type: str = "scientific") -> bool:
        """Validate a species name against MINDEX."""
        if name_type == "scientific":
            return self.is_valid(name, "mindex_species_scientific")
        elif name_type == "common":
            return self.is_valid(name, "mindex_species_common")
        return self.is_valid(name, "mindex_species_scientific")

    def is_valid_agent_id(self, agent_id: str) -> bool:
        """Validate an agent identifier."""
        return self.is_valid(agent_id, "agent_ids")

    def is_valid_graph_node_type(self, node_type: str) -> bool:
        """Validate a knowledge graph node type."""
        return self.is_valid(node_type, "search_graph_node_types")

    def is_valid_graph_edge_type(self, edge_type: str) -> bool:
        """Validate a knowledge graph edge/relationship type."""
        return self.is_valid(edge_type, "search_graph_edge_types")

    def is_valid_crep_domain(self, domain: str) -> bool:
        """Validate a CREP domain name."""
        return self.is_valid(domain, "crep_domains")

    def is_valid_nlm_prediction_type(self, pred_type: str) -> bool:
        """Validate an NLM prediction type."""
        return self.is_valid(pred_type, "nlm_prediction_types")

    def is_valid_data_format(self, fmt: str) -> bool:
        """Validate a data format identifier."""
        return self.is_valid(fmt, "obs_data_formats")

    def is_valid_biome(self, biome: str) -> bool:
        """Validate a biome identifier."""
        return self.is_valid(biome, "geo_biomes")

    def get_stats(self) -> Dict[str, Any]:
        """Get validator statistics."""
        indexes = self._engine.list_indexes()
        return {
            "initialized": self._initialized,
            "total_indexes": len(indexes),
            "index_names": sorted(indexes.keys()),
        }


# --- Singleton pattern for system-wide access ---

_validator_instance: Optional[STATICValidator] = None


def get_static_validator() -> STATICValidator:
    """
    Get the global STATIC validator instance.

    This is the recommended way to access the validator from anywhere
    in the system. The instance is created lazily on first access.
    """
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = STATICValidator()
    return _validator_instance


def set_static_validator(validator: STATICValidator) -> None:
    """Set the global STATIC validator instance (for testing or custom setup)."""
    global _validator_instance
    _validator_instance = validator
