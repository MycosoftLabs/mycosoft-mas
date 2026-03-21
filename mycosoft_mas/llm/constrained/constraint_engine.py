"""
STATIC Constraint Engine

Applies STATIC index constraints during LLM decoding. Supports both:
1. Direct logit masking for local models (Ollama/PyTorch)
2. Constrained reranking for API-based providers (OpenAI/Anthropic)

The engine implements the hybrid dense/sparse transition logic from the paper:
- Dense path for initial decoding steps (O(1) lookup)
- CSR sparse path for deeper steps (coalesced memory reads)

Created: March 3, 2026
"""

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from mycosoft_mas.llm.constrained.static_index import STATICIndex

logger = logging.getLogger(__name__)


@dataclass
class ConstrainedGenerationResult:
    """Result of a constrained generation run."""

    sequences: List[List[int]]
    scores: List[float]
    text_outputs: List[str]
    num_steps: int
    constraint_violations_blocked: int
    latency_ms: float
    index_name: str = ""

    def best(self) -> str:
        """Return the highest-scoring output."""
        if not self.text_outputs:
            return ""
        best_idx = int(np.argmax(self.scores))
        return self.text_outputs[best_idx]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sequences": self.sequences,
            "scores": self.scores,
            "text_outputs": self.text_outputs,
            "num_steps": self.num_steps,
            "constraint_violations_blocked": self.constraint_violations_blocked,
            "latency_ms": round(self.latency_ms, 2),
            "index_name": self.index_name,
        }


class ConstraintEngine:
    """
    Applies STATIC constraints during LLM token generation.

    Works with both local (logit-level) and API-based (reranking) models.
    """

    def __init__(self):
        self._indexes: Dict[str, STATICIndex] = {}
        self._decode_fns: Dict[str, Callable] = {}
        logger.info("ConstraintEngine initialized")

    def register_index(self, name: str, index: STATICIndex) -> None:
        """Register a named STATIC index for use during decoding."""
        self._indexes[name] = index
        logger.info(
            f"Registered index '{name}': {index.num_states} states, "
            f"{index.num_sequences} sequences"
        )

    def get_index(self, name: str) -> Optional[STATICIndex]:
        return self._indexes.get(name)

    def list_indexes(self) -> Dict[str, Dict[str, Any]]:
        return {name: idx.to_dict() for name, idx in self._indexes.items()}

    def remove_index(self, name: str) -> bool:
        if name in self._indexes:
            del self._indexes[name]
            return True
        return False

    def get_valid_tokens_at_step(
        self,
        index_name: str,
        current_states: List[int],
        step: int,
    ) -> Dict[int, List[Tuple[int, int]]]:
        """
        Get valid (token, next_state) pairs for each current state at a given step.

        Uses dense lookup for early steps, CSR for later steps.

        Args:
            index_name: Name of the registered index.
            current_states: List of current trie states (one per beam).
            step: Current decoding step (0-indexed).

        Returns:
            Dict mapping state → list of (token_id, next_state) pairs.
        """
        index = self._indexes.get(index_name)
        if index is None:
            raise ValueError(f"Index '{index_name}' not registered")

        results: Dict[int, List[Tuple[int, int]]] = {}

        if step == 0:
            # Use start_mask for first step
            valid_tokens = np.where(index.start_mask)[0]
            # For step 0, all beams start from root (state 0)
            root_children = []
            for tok in valid_tokens:
                # Find the child state for this token from dense layer
                if index.dense_masks.shape[0] > 0:
                    slot_mask = index.dense_masks[0, 0]
                    for slot in range(len(slot_mask)):
                        if slot_mask[slot]:
                            t = int(index.dense_states[0, 0, slot, 0])
                            s = int(index.dense_states[0, 0, slot, 1])
                            if t == tok:
                                root_children.append((int(tok), s))
                                break
                    else:
                        root_children.append((int(tok), 0))
                else:
                    root_children.append((int(tok), 0))
            results[0] = root_children
            return results

        # For subsequent steps, use dense or sparse lookup
        for state in current_states:
            children = self._get_children(index, state, step)
            results[state] = children

        return results

    def _get_children(
        self,
        index: STATICIndex,
        state: int,
        step: int,
    ) -> List[Tuple[int, int]]:
        """Get children of a state using dense or sparse path."""
        children = []

        # Try dense path first
        if step < index.dense_masks.shape[0] and state < index.dense_masks.shape[1]:
            slot_mask = index.dense_masks[step, state]
            for slot in range(len(slot_mask)):
                if slot_mask[slot]:
                    token = int(index.dense_states[step, state, slot, 0])
                    next_state = int(index.dense_states[step, state, slot, 1])
                    children.append((token, next_state))
            if children:
                return children

        # Fall back to CSR sparse path
        if state + 1 < len(index.csr_indptr):
            start = int(index.csr_indptr[state])
            end = int(index.csr_indptr[state + 1])
            for idx in range(start, end):
                if idx < len(index.csr_packed):
                    token = int(index.csr_packed[idx, 0])
                    next_state = int(index.csr_packed[idx, 1])
                    children.append((token, next_state))

        return children

    def build_logit_mask(
        self,
        index_name: str,
        current_states: List[int],
        step: int,
        vocab_size: Optional[int] = None,
    ) -> np.ndarray:
        """
        Build a logit mask for the current decoding step.

        Returns a boolean mask of shape (num_beams, vocab_size) where True
        indicates a valid token. Apply via: logits[~mask] = -inf

        This is the core STATIC operation — vectorized masking.
        """
        index = self._indexes.get(index_name)
        if index is None:
            raise ValueError(f"Index '{index_name}' not registered")

        vs = vocab_size or index.config.vocab_size
        num_beams = len(current_states)
        mask = np.zeros((num_beams, vs), dtype=np.bool_)

        if step == 0:
            # All beams use start_mask
            for b in range(num_beams):
                mask[b, : len(index.start_mask)] = index.start_mask[
                    : min(vs, len(index.start_mask))
                ]
        else:
            valid_tokens = self.get_valid_tokens_at_step(index_name, current_states, step)
            for b, state in enumerate(current_states):
                for token, _ in valid_tokens.get(state, []):
                    if 0 <= token < vs:
                        mask[b, token] = True

        return mask

    def constrained_beam_search(
        self,
        index_name: str,
        logit_fn: Callable[[List[List[int]], int], np.ndarray],
        beam_width: int = 4,
        max_steps: Optional[int] = None,
        detokenize_fn: Optional[Callable[[List[int]], str]] = None,
    ) -> ConstrainedGenerationResult:
        """
        Run constrained beam search using a STATIC index.

        Args:
            index_name: Name of the registered constraint index.
            logit_fn: Callable that takes (partial_sequences, step) and returns
                      logits of shape (num_beams, vocab_size).
            beam_width: Number of beams to maintain.
            max_steps: Maximum decoding steps. Defaults to index max_depth.
            detokenize_fn: Optional function to convert token IDs to strings.

        Returns:
            ConstrainedGenerationResult with top beam outputs.
        """
        t0 = time.time()

        index = self._indexes.get(index_name)
        if index is None:
            raise ValueError(f"Index '{index_name}' not registered")

        max_steps = max_steps or index.max_depth
        violations_blocked = 0

        # Initialize beams: (score, token_sequence, current_state)
        beams: List[Tuple[float, List[int], int]] = [(0.0, [], 0)]

        for step in range(max_steps):
            if not beams:
                break

            current_states = [b[2] for b in beams]
            partial_seqs = [b[1] for b in beams]

            # Get logits from model
            logits = logit_fn(partial_seqs, step)

            # Build constraint mask
            mask = self.build_logit_mask(index_name, current_states, step, logits.shape[-1])

            # Count violations that would be blocked
            for b in range(len(beams)):
                # Tokens that have positive logits but are masked out
                positive_logits = logits[b] > -1e6
                blocked = positive_logits & ~mask[b]
                violations_blocked += int(np.sum(blocked))

            # Apply mask: set invalid tokens to -inf
            masked_logits = np.where(mask, logits, -np.inf)

            # Expand beams
            candidates: List[Tuple[float, List[int], int]] = []
            valid_tokens_map = self.get_valid_tokens_at_step(index_name, current_states, step)

            for b, (score, seq, state) in enumerate(beams):
                children = valid_tokens_map.get(state, [])
                for token, next_state in children:
                    if 0 <= token < masked_logits.shape[1]:
                        token_score = float(masked_logits[b, token])
                        if token_score > -1e6:
                            candidates.append((score + token_score, seq + [token], next_state))

            if not candidates:
                break

            # Keep top-k beams
            candidates.sort(key=lambda x: x[0], reverse=True)
            beams = candidates[:beam_width]

        # Build results
        sequences = [b[1] for b in beams]
        scores = [b[0] for b in beams]

        if detokenize_fn:
            text_outputs = [detokenize_fn(seq) for seq in sequences]
        else:
            text_outputs = [str(seq) for seq in sequences]

        latency = (time.time() - t0) * 1000

        return ConstrainedGenerationResult(
            sequences=sequences,
            scores=scores,
            text_outputs=text_outputs,
            num_steps=min(step + 1, max_steps) if beams else 0,
            constraint_violations_blocked=violations_blocked,
            latency_ms=latency,
            index_name=index_name,
        )

    def constrained_rerank(
        self,
        index_name: str,
        candidates: List[str],
        tokenizer_fn: Callable[[str], List[int]],
        score_fn: Optional[Callable[[str], float]] = None,
    ) -> List[Tuple[str, float, bool]]:
        """
        Rerank candidates by checking which satisfy index constraints.

        For API-based providers where we can't mask logits directly,
        this validates and reranks generated candidates against the index.

        Args:
            index_name: Name of the registered constraint index.
            candidates: List of candidate strings to validate.
            tokenizer_fn: Tokenizer function.
            score_fn: Optional scoring function for valid candidates.

        Returns:
            List of (candidate, score, is_valid) tuples, sorted by validity then score.
        """
        index = self._indexes.get(index_name)
        if index is None:
            raise ValueError(f"Index '{index_name}' not registered")

        results: List[Tuple[str, float, bool]] = []

        for candidate in candidates:
            tokens = tokenizer_fn(candidate)
            is_valid = self._validate_sequence(index, tokens)
            score = score_fn(candidate) if score_fn else (1.0 if is_valid else 0.0)
            results.append((candidate, score, is_valid))

        # Sort: valid first, then by score descending
        results.sort(key=lambda x: (-int(x[2]), -x[1]))
        return results

    def _validate_sequence(
        self,
        index: STATICIndex,
        tokens: List[int],
    ) -> bool:
        """Check if a token sequence is valid according to the index."""
        if not tokens:
            return False

        # Check first token
        if tokens[0] < 0 or tokens[0] >= len(index.start_mask):
            return False
        if not index.start_mask[tokens[0]]:
            return False

        # Walk the trie
        state = 0
        for step, token in enumerate(tokens):
            children = self._get_children(index, state, step)
            found = False
            for child_token, next_state in children:
                if child_token == token:
                    state = next_state
                    found = True
                    break
            if not found:
                return False

        return True
