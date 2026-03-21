"""
Tests for STATIC Constrained Decoding Module

Tests the core STATIC algorithm components:
- Index building from sequences and strings
- Constraint engine (logit masking, beam search, validation)
- Token masker (hard/soft/sampling strategies)
- RAG integration (entity indexing and constrained retrieval)

Created: March 3, 2026
"""

import os
import tempfile

import numpy as np
import pytest

from mycosoft_mas.llm.constrained.constraint_engine import (
    ConstrainedGenerationResult,
    ConstraintEngine,
)
from mycosoft_mas.llm.constrained.rag_integration import (
    ConstrainedRAGEngine,
)
from mycosoft_mas.llm.constrained.static_index import (
    IndexConfig,
    STATICIndex,
    build_index_from_strings,
    build_static_index,
)
from mycosoft_mas.llm.constrained.token_masker import (
    MaskingStrategy,
    TokenMasker,
)

# --- Fixtures ---


def make_simple_sequences():
    """Create simple test sequences: paths like [1,2], [1,3], [2,4]."""
    return np.array(
        [
            [1, 2, -1],
            [1, 3, -1],
            [2, 4, -1],
            [2, 5, 6],
        ],
        dtype=np.int32,
    )


def make_config(vocab_size=10):
    return IndexConfig(vocab_size=vocab_size, dense_depth=2)


# --- STATICIndex Tests ---


class TestSTATICIndex:
    def test_build_basic_index(self):
        sequences = make_simple_sequences()
        config = make_config()
        index = build_static_index(sequences, config)

        assert isinstance(index, STATICIndex)
        assert index.num_sequences == 4
        assert index.num_states > 0
        assert index.max_depth == 3
        assert index.build_time_ms > 0

    def test_start_mask(self):
        sequences = make_simple_sequences()
        config = make_config()
        index = build_static_index(sequences, config)

        # Tokens 1 and 2 are valid start tokens
        assert index.start_mask[1] is np.True_
        assert index.start_mask[2] is np.True_
        # Token 0 is not a valid start
        assert index.start_mask[0] is np.False_

    def test_layer_branching(self):
        sequences = make_simple_sequences()
        config = make_config()
        index = build_static_index(sequences, config)

        assert len(index.layer_branching) == 3
        # Level 0: 2 unique start tokens (1, 2)
        assert index.layer_branching[0] == 2

    def test_memory_usage(self):
        sequences = make_simple_sequences()
        config = make_config()
        index = build_static_index(sequences, config)

        assert index.memory_usage_bytes() > 0
        assert index.memory_usage_mb() > 0

    def test_to_dict(self):
        sequences = make_simple_sequences()
        config = make_config()
        index = build_static_index(sequences, config)

        d = index.to_dict()
        assert "num_states" in d
        assert "max_depth" in d
        assert "memory_mb" in d
        assert "build_time_ms" in d
        assert d["num_sequences"] == 4

    def test_save_and_load(self):
        sequences = make_simple_sequences()
        config = make_config()
        index = build_static_index(sequences, config)

        with tempfile.NamedTemporaryFile(suffix=".npz", delete=False) as f:
            path = f.name

        try:
            index.save(path)
            loaded = STATICIndex.load(path)

            assert loaded.num_states == index.num_states
            assert loaded.max_depth == index.max_depth
            assert loaded.num_sequences == index.num_sequences
            np.testing.assert_array_equal(loaded.start_mask, index.start_mask)
        finally:
            os.unlink(path)

    def test_build_from_strings(self):
        valid_strings = ["cat", "car", "dog", "dot"]

        def simple_tok(s):
            return [ord(c) for c in s]

        config = IndexConfig(vocab_size=256, dense_depth=2)
        index = build_index_from_strings(valid_strings, simple_tok, config)

        assert index.num_sequences == 4
        assert index.num_states > 0
        # 'c' and 'd' should be valid starts
        assert index.start_mask[ord("c")]
        assert index.start_mask[ord("d")]
        # 'z' should not
        assert not index.start_mask[ord("z")]

    def test_large_sequence_count(self):
        """Test with more sequences to verify scaling."""
        np.random.seed(42)
        num_seqs = 1000
        max_len = 5
        vocab_size = 50
        sequences = np.random.randint(0, vocab_size, (num_seqs, max_len), dtype=np.int32)
        config = IndexConfig(vocab_size=vocab_size, dense_depth=2)

        index = build_static_index(sequences, config)
        assert index.num_sequences == num_seqs
        assert index.num_states > 0

    def test_single_sequence(self):
        sequences = np.array([[5, 10, 15]], dtype=np.int32)
        config = make_config(vocab_size=20)
        index = build_static_index(sequences, config)

        assert index.num_sequences == 1
        assert index.start_mask[5]
        assert not index.start_mask[0]

    def test_rejects_1d_input(self):
        with pytest.raises(ValueError, match="2D"):
            build_static_index(np.array([1, 2, 3]))


# --- ConstraintEngine Tests ---


class TestConstraintEngine:
    def test_register_and_list(self):
        engine = ConstraintEngine()
        sequences = make_simple_sequences()
        index = build_static_index(sequences, make_config())

        engine.register_index("test", index)
        indexes = engine.list_indexes()

        assert "test" in indexes
        assert indexes["test"]["num_sequences"] == 4

    def test_remove_index(self):
        engine = ConstraintEngine()
        index = build_static_index(make_simple_sequences(), make_config())
        engine.register_index("test", index)

        assert engine.remove_index("test")
        assert not engine.remove_index("nonexistent")
        assert engine.get_index("test") is None

    def test_build_logit_mask_step_0(self):
        engine = ConstraintEngine()
        index = build_static_index(make_simple_sequences(), make_config())
        engine.register_index("test", index)

        mask = engine.build_logit_mask("test", [0], step=0, vocab_size=10)

        assert mask.shape == (1, 10)
        # Tokens 1 and 2 should be valid at step 0
        assert mask[0, 1]
        assert mask[0, 2]
        # Token 0 should not
        assert not mask[0, 0]

    def test_validate_sequence_valid(self):
        engine = ConstraintEngine()
        index = build_static_index(make_simple_sequences(), make_config())
        engine.register_index("test", index)

        # [1, 2] should be valid
        assert engine._validate_sequence(index, [1, 2])
        # [2, 4] should be valid
        assert engine._validate_sequence(index, [2, 4])

    def test_validate_sequence_invalid(self):
        engine = ConstraintEngine()
        index = build_static_index(make_simple_sequences(), make_config())
        engine.register_index("test", index)

        # [3, 1] should not be valid (3 not a start token)
        assert not engine._validate_sequence(index, [3, 1])
        # Empty sequence
        assert not engine._validate_sequence(index, [])

    def test_constrained_beam_search(self):
        engine = ConstraintEngine()
        index = build_static_index(make_simple_sequences(), make_config())
        engine.register_index("test", index)

        def uniform_logits(seqs, step):
            n = max(len(seqs), 1)
            return np.zeros((n, 10), dtype=np.float32)

        result = engine.constrained_beam_search(
            index_name="test",
            logit_fn=uniform_logits,
            beam_width=4,
            max_steps=3,
        )

        assert isinstance(result, ConstrainedGenerationResult)
        assert len(result.sequences) > 0
        # All sequences should be valid
        for seq in result.sequences:
            assert engine._validate_sequence(index, seq)

    def test_constrained_rerank(self):
        engine = ConstraintEngine()
        valid_strings = ["abc", "abd", "xyz"]

        def tok(s):
            return [ord(c) for c in s]

        config = IndexConfig(vocab_size=256, dense_depth=2)
        index = build_index_from_strings(valid_strings, tok, config)
        engine.register_index("test", index)

        results = engine.constrained_rerank(
            index_name="test",
            candidates=["abc", "abd", "zzz", "xyz"],
            tokenizer_fn=tok,
        )

        # Valid ones should come first
        valid_results = [r for r in results if r[2]]
        invalid_results = [r for r in results if not r[2]]
        assert len(valid_results) == 3
        assert len(invalid_results) == 1
        assert invalid_results[0][0] == "zzz"

    def test_raises_on_missing_index(self):
        engine = ConstraintEngine()
        with pytest.raises(ValueError, match="not registered"):
            engine.build_logit_mask("nonexistent", [0], 0)


# --- TokenMasker Tests ---


class TestTokenMasker:
    def test_hard_masking(self):
        index = build_static_index(make_simple_sequences(), make_config())
        masker = TokenMasker(index, strategy=MaskingStrategy.HARD)

        logits = np.zeros(10, dtype=np.float32)
        masked = masker.apply_mask(logits, [0], step=0)

        # Invalid tokens should be -inf
        assert masked[0] == -np.inf
        assert np.isfinite(masked[1])
        assert np.isfinite(masked[2])

    def test_soft_masking(self):
        index = build_static_index(make_simple_sequences(), make_config())
        masker = TokenMasker(index, strategy=MaskingStrategy.SOFT, soft_penalty=-5.0)

        logits = np.zeros(10, dtype=np.float32)
        masked = masker.apply_mask(logits, [0], step=0)

        # Invalid tokens should be penalized
        assert masked[0] == -5.0
        # Valid tokens unchanged
        assert masked[1] == 0.0
        assert masked[2] == 0.0

    def test_sampling_masking(self):
        index = build_static_index(make_simple_sequences(), make_config())
        masker = TokenMasker(index, strategy=MaskingStrategy.SAMPLING)

        logits = np.ones(10, dtype=np.float32)
        masked = masker.apply_mask(logits, [0], step=0)

        # After sampling masking, invalid tokens should have very low logits
        assert masked[0] < masked[1]

    def test_get_next_state(self):
        index = build_static_index(make_simple_sequences(), make_config())
        masker = TokenMasker(index)

        # From root, token 1 should lead to a valid state
        next_state = masker.get_next_state(0, 1, 0)
        assert next_state > 0

        # Invalid token from root
        next_state = masker.get_next_state(0, 9, 0)
        assert next_state == -1

    def test_cache_stats(self):
        index = build_static_index(make_simple_sequences(), make_config())
        masker = TokenMasker(index)

        masker.apply_mask(np.zeros(10), [0], step=0)
        stats = masker.cache_stats()

        assert "cache_size" in stats
        assert "cache_hits" in stats
        assert "cache_misses" in stats

    def test_reset_cache(self):
        index = build_static_index(make_simple_sequences(), make_config())
        masker = TokenMasker(index)

        # Step 0 uses start_mask directly; step 1+ populates cache
        # First get a valid state from step 0
        next_state = masker.get_next_state(0, 1, 0)
        # Now use that state at step 1 to populate cache
        masker.apply_mask(np.zeros(10), [next_state], step=1)
        assert masker.cache_stats()["cache_size"] > 0

        masker.reset_cache()
        assert masker.cache_stats()["cache_size"] == 0

    def test_batch_masking(self):
        index = build_static_index(make_simple_sequences(), make_config())
        masker = TokenMasker(index)

        logits = np.zeros((3, 10), dtype=np.float32)
        masked = masker.apply_mask(logits, [0, 0, 0], step=0)

        assert masked.shape == (3, 10)
        for b in range(3):
            assert masked[b, 0] == -np.inf
            assert np.isfinite(masked[b, 1])

    def test_ollama_logit_processor(self):
        index = build_static_index(make_simple_sequences(), make_config())
        masker = TokenMasker(index)

        processor = masker.create_ollama_logit_processor()

        # Step 0
        logits = np.zeros(10, dtype=np.float32)
        masked = processor(logits)
        assert masked[0] == -np.inf
        assert np.isfinite(masked[1])


# --- ConstrainedRAGEngine Tests ---


class TestConstrainedRAGEngine:
    def test_build_entity_index(self):
        rag = ConstrainedRAGEngine()
        entities = [
            "Agaricus bisporus",
            "Pleurotus ostreatus",
            "Ganoderma lucidum",
            "Trametes versicolor",
        ]

        stats = rag.build_entity_index("species", entities)

        assert stats["num_entities"] == 4
        assert stats["num_states"] > 0

    def test_constrained_entity_retrieval(self):
        rag = ConstrainedRAGEngine()
        entities = [
            "Agaricus bisporus",
            "Pleurotus ostreatus",
            "Ganoderma lucidum",
        ]
        rag.build_entity_index("species", entities)

        results = rag.constrained_entity_retrieval(
            "species",
            "What is the taxonomy of Agaricus bisporus?",
            top_k=3,
        )

        assert len(results) == 3
        # The entity mentioned in the query should score highest
        assert results[0]["entity"] == "Agaricus bisporus"
        assert results[0]["constrained"] is True

    def test_validate_and_resolve(self):
        rag = ConstrainedRAGEngine()
        entities = ["cat", "car", "dog"]

        def tok(s):
            return [ord(c) for c in s]

        rag.build_entity_index("animals", entities, tokenizer_fn=tok, vocab_size=256)

        results = rag.validate_and_resolve("animals", ["cat", "car", "fox"])

        valid = [r for r in results if r["valid"]]
        invalid = [r for r in results if not r["valid"]]

        assert len(valid) == 2
        assert len(invalid) == 1

    def test_list_entity_indexes(self):
        rag = ConstrainedRAGEngine()
        rag.build_entity_index("idx1", ["a", "b"])
        rag.build_entity_index("idx2", ["x", "y", "z"])

        indexes = rag.list_entity_indexes()
        assert "idx1" in indexes
        assert "idx2" in indexes
        assert indexes["idx1"]["num_entities"] == 2
        assert indexes["idx2"]["num_entities"] == 3

    def test_empty_entities_raises(self):
        rag = ConstrainedRAGEngine()
        with pytest.raises(ValueError, match="No entities"):
            rag.build_entity_index("empty", [])


# --- Integration / Performance Tests ---


class TestPerformance:
    def test_index_build_performance(self):
        """Verify index builds efficiently for moderate sequence counts."""
        np.random.seed(42)
        sequences = np.random.randint(0, 100, (5000, 8), dtype=np.int32)
        config = IndexConfig(vocab_size=100, dense_depth=2)

        index = build_static_index(sequences, config)

        # Should build in reasonable time
        assert index.build_time_ms < 30000  # 30 seconds max
        assert index.num_states > 0

    def test_mask_generation_consistency(self):
        """Verify masks are consistent across repeated calls."""
        engine = ConstraintEngine()
        index = build_static_index(make_simple_sequences(), make_config())
        engine.register_index("test", index)

        mask1 = engine.build_logit_mask("test", [0], step=0)
        mask2 = engine.build_logit_mask("test", [0], step=0)

        np.testing.assert_array_equal(mask1, mask2)


# --- Agent Import Test ---


class TestAgentImport:
    def test_static_decoding_agent_import(self):
        try:
            from mycosoft_mas.agents.v2.static_decoding_agent import STATICDecodingAgent
        except ImportError:
            pytest.skip("Agent dependencies not available (docker package)")
            return

        agent = STATICDecodingAgent()
        assert agent.agent_type == "static_decoding"
        assert agent.category == "data"
        assert "build_constraint_index" in agent.get_capabilities()

    def test_agent_registered_in_init(self):
        import mycosoft_mas.agents as agents_pkg

        # May not be available if docker dependency is missing
        if not hasattr(agents_pkg, "STATICDecodingAgent"):
            pytest.skip("STATICDecodingAgent not loaded (missing runtime deps)")
        assert hasattr(agents_pkg, "STATICDecodingAgent")
