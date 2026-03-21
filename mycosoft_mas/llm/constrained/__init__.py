"""
STATIC Constrained Decoding Module

Implements Google's STATIC (Sparse Transition-Accelerated Trie Index and Constraining)
framework for efficient constrained decoding in LLM-based generative retrieval.

Paper: "Vectorizing the Trie: Efficient Constrained Decoding for LLM-based
        Generative Retrieval on Accelerators" (Su et al., 2026)
Reference: https://github.com/youtube/static-constraint-decoding

Key concepts:
- Hybrid dense/sparse trie index stored as CSR matrices
- O(1) constraint masking regardless of constraint count
- 948x speedup over naive trie-based constrained decoding
- Accelerator-native design (GPU/TPU vectorized operations)

Created: March 3, 2026
"""

from mycosoft_mas.llm.constrained.constraint_engine import (
    ConstrainedGenerationResult,
    ConstraintEngine,
)
from mycosoft_mas.llm.constrained.domain_builders import (
    DOMAIN_BUILDERS,
    DomainIndexReport,
    build_agent_index,
    build_all_domain_indexes,
    build_biosphere_index,
    build_crep_index,
    build_device_index,
    build_environment_index,
    build_geospatial_index,
    build_infrastructure_index,
    build_mindex_species_index,
    build_nlm_index,
    build_observation_index,
    build_search_index,
    build_signal_index,
    build_taxonomy_index,
    build_user_index,
)
from mycosoft_mas.llm.constrained.static_index import (
    IndexConfig,
    STATICIndex,
    build_static_index,
)
from mycosoft_mas.llm.constrained.token_masker import (
    MaskingStrategy,
    TokenMasker,
)
from mycosoft_mas.llm.constrained.validator import (
    STATICValidator,
    ValidationResult,
    get_static_validator,
    set_static_validator,
)

__all__ = [
    "STATICIndex",
    "build_static_index",
    "IndexConfig",
    "ConstraintEngine",
    "ConstrainedGenerationResult",
    "TokenMasker",
    "MaskingStrategy",
    "build_all_domain_indexes",
    "build_mindex_species_index",
    "build_taxonomy_index",
    "build_crep_index",
    "build_nlm_index",
    "build_agent_index",
    "build_device_index",
    "build_signal_index",
    "build_user_index",
    "build_biosphere_index",
    "build_environment_index",
    "build_infrastructure_index",
    "build_geospatial_index",
    "build_observation_index",
    "build_search_index",
    "DomainIndexReport",
    "DOMAIN_BUILDERS",
    "STATICValidator",
    "ValidationResult",
    "get_static_validator",
    "set_static_validator",
]
