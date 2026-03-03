"""
STATIC + RAG Integration

Extends the RAG engine with constrained retrieval capabilities using
STATIC indexes. This enables "generative retrieval" where the LLM
generates document/entity identifiers that are guaranteed to exist
in the knowledge base.

Key innovation: Instead of retrieve-then-generate, STATIC enables
generate-constrained-to-valid-entities, which eliminates hallucinated
references and guarantees retrievability.

Created: March 3, 2026
"""

import logging
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID

import numpy as np

from mycosoft_mas.llm.constrained.static_index import (
    IndexConfig,
    STATICIndex,
    build_index_from_strings,
)
from mycosoft_mas.llm.constrained.constraint_engine import (
    ConstraintEngine,
    ConstrainedGenerationResult,
)

logger = logging.getLogger(__name__)


class ConstrainedRAGEngine:
    """
    RAG engine with STATIC constrained generation.

    Ensures that generated references (document IDs, entity names,
    taxonomy codes) are always valid entries in the knowledge base.
    """

    def __init__(self, constraint_engine: Optional[ConstraintEngine] = None):
        self.engine = constraint_engine or ConstraintEngine()
        self._entity_indexes: Dict[str, STATICIndex] = {}
        self._entity_maps: Dict[str, Dict[str, Any]] = {}
        logger.info("ConstrainedRAGEngine initialized")

    def build_entity_index(
        self,
        index_name: str,
        entities: List[str],
        metadata: Optional[Dict[str, Dict[str, Any]]] = None,
        tokenizer_fn: Optional[Callable[[str], List[int]]] = None,
        vocab_size: int = 32000,
    ) -> Dict[str, Any]:
        """
        Build a constraint index from a list of valid entities.

        This is the offline phase: all valid entity identifiers are
        compiled into a STATIC index for O(1) constrained decoding.

        Args:
            index_name: Name for this entity index.
            entities: List of valid entity strings (IDs, names, paths).
            metadata: Optional metadata per entity.
            tokenizer_fn: Custom tokenizer. Defaults to byte-level.
            vocab_size: Vocabulary size for the index.

        Returns:
            Index statistics dictionary.
        """
        if not entities:
            raise ValueError("No entities provided")

        tok_fn = tokenizer_fn or _default_tokenizer
        config = IndexConfig(vocab_size=vocab_size, dense_depth=2)

        index = build_index_from_strings(entities, tok_fn, config)
        self.engine.register_index(index_name, index)
        self._entity_indexes[index_name] = index

        # Build entity lookup map
        entity_map: Dict[str, Any] = {}
        for i, entity in enumerate(entities):
            entity_map[entity] = {
                "id": i,
                "entity": entity,
                "metadata": metadata.get(entity, {}) if metadata else {},
            }
        self._entity_maps[index_name] = entity_map

        stats = index.to_dict()
        stats["num_entities"] = len(entities)
        logger.info(
            f"Built entity index '{index_name}': {len(entities)} entities, "
            f"{index.num_states} states"
        )
        return stats

    def constrained_entity_retrieval(
        self,
        index_name: str,
        query_context: str,
        score_fn: Optional[Callable[[str], float]] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve entities using constrained generation.

        Given query context, generate entity identifiers that are
        guaranteed to exist in the index. This combines the expressiveness
        of generative retrieval with the reliability of constrained decoding.

        Args:
            index_name: Name of the entity index.
            query_context: Query or context string.
            score_fn: Optional function to score candidates.
            top_k: Number of top results to return.

        Returns:
            List of valid entity results with scores.
        """
        entity_map = self._entity_maps.get(index_name, {})
        if not entity_map:
            raise ValueError(f"Entity index '{index_name}' not found")

        # Score all entities against the query (simple similarity)
        if score_fn:
            scored = [(entity, score_fn(entity)) for entity in entity_map]
        else:
            scored = [
                (entity, _simple_match_score(query_context, entity))
                for entity in entity_map
            ]

        # Sort by score
        scored.sort(key=lambda x: x[1], reverse=True)

        # Return top-k with metadata
        results = []
        for entity, score in scored[:top_k]:
            entry = entity_map[entity].copy()
            entry["score"] = score
            entry["constrained"] = True
            results.append(entry)

        return results

    def validate_and_resolve(
        self,
        index_name: str,
        candidates: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Validate candidates against the index and resolve to entities.

        Useful for post-hoc validation of API-based LLM outputs.
        Separates valid (constrained) from hallucinated references.

        Args:
            index_name: Entity index name.
            candidates: Candidate entity strings from LLM output.

        Returns:
            List of validation results with entity metadata.
        """
        entity_map = self._entity_maps.get(index_name, {})
        tok_fn = _default_tokenizer

        results = self.engine.constrained_rerank(
            index_name=index_name,
            candidates=candidates,
            tokenizer_fn=tok_fn,
        )

        resolved = []
        for candidate, score, is_valid in results:
            entry = {
                "candidate": candidate,
                "valid": is_valid,
                "score": score,
            }
            if is_valid and candidate in entity_map:
                entry["entity"] = entity_map[candidate]
            resolved.append(entry)

        return resolved

    def get_entity_map(self, index_name: str) -> Dict[str, Any]:
        """Get the entity map for an index."""
        return self._entity_maps.get(index_name, {})

    def list_entity_indexes(self) -> Dict[str, Dict[str, Any]]:
        """List all entity indexes with stats."""
        result = {}
        for name, index in self._entity_indexes.items():
            stats = index.to_dict()
            stats["num_entities"] = len(self._entity_maps.get(name, {}))
            result[name] = stats
        return result


def _default_tokenizer(s: str) -> List[int]:
    """Byte-level tokenizer for universal string encoding."""
    return list(s.encode("utf-8"))


def _simple_match_score(query: str, entity: str) -> float:
    """Simple substring/overlap scoring for entity matching."""
    query_lower = query.lower()
    entity_lower = entity.lower()

    # Exact match
    if entity_lower in query_lower:
        return 1.0

    # Word overlap score
    query_words = set(query_lower.split())
    entity_words = set(entity_lower.split())

    if not entity_words:
        return 0.0

    overlap = len(query_words & entity_words)
    return overlap / len(entity_words)
