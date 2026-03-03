"""
Token Masker - Logit-level constraint enforcement for local models.

Provides integration with local inference engines (Ollama, vLLM) by
applying STATIC index masks directly to model logits before sampling.

Also implements MaskingStrategy patterns for different use cases:
- HARD: Block all invalid tokens (-inf masking)
- SOFT: Penalize invalid tokens (additive bias)
- SAMPLING: Adjust sampling probabilities proportionally

Created: March 3, 2026
"""

import logging
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from mycosoft_mas.llm.constrained.static_index import STATICIndex

logger = logging.getLogger(__name__)


class MaskingStrategy(str, Enum):
    """How to apply constraint masks to logits."""

    HARD = "hard"  # -inf for invalid tokens (strict constraint)
    SOFT = "soft"  # Additive penalty for invalid tokens (guidance)
    SAMPLING = "sampling"  # Adjust sampling probabilities


class TokenMasker:
    """
    Applies STATIC constraint masks to model logits.

    Designed for integration with local inference engines where we
    have direct access to logit tensors before sampling.
    """

    def __init__(
        self,
        index: STATICIndex,
        strategy: MaskingStrategy = MaskingStrategy.HARD,
        soft_penalty: float = -10.0,
        sampling_temperature: float = 1.0,
    ):
        self.index = index
        self.strategy = strategy
        self.soft_penalty = soft_penalty
        self.sampling_temperature = sampling_temperature

        # Pre-compute start mask as float for efficient masking
        self._start_mask_float = index.start_mask.astype(np.float32)

        # Cache for frequently accessed state transitions
        self._transition_cache: Dict[Tuple[int, int], List[Tuple[int, int]]] = {}
        self._cache_hits = 0
        self._cache_misses = 0

    def apply_mask(
        self,
        logits: np.ndarray,
        states: List[int],
        step: int,
    ) -> np.ndarray:
        """
        Apply constraint mask to logits based on current states and step.

        Args:
            logits: Raw logits from model, shape (batch, vocab_size) or (vocab_size,).
            states: Current trie states for each beam/sample.
            step: Current decoding step.

        Returns:
            Modified logits with constraints applied.
        """
        single = logits.ndim == 1
        if single:
            logits = logits[np.newaxis, :]
            states = states[:1] if states else [0]

        batch_size, vocab_size = logits.shape
        masked_logits = logits.copy()

        for b in range(batch_size):
            state = states[b] if b < len(states) else 0
            valid_mask = self._get_valid_mask(state, step, vocab_size)

            if self.strategy == MaskingStrategy.HARD:
                masked_logits[b, ~valid_mask] = -np.inf
            elif self.strategy == MaskingStrategy.SOFT:
                masked_logits[b, ~valid_mask] += self.soft_penalty
            elif self.strategy == MaskingStrategy.SAMPLING:
                # Convert to probabilities, zero out invalid, renormalize
                probs = _softmax(masked_logits[b] / self.sampling_temperature)
                probs[~valid_mask] = 0.0
                prob_sum = probs.sum()
                if prob_sum > 0:
                    probs /= prob_sum
                # Convert back to logits
                probs = np.clip(probs, 1e-10, 1.0)
                masked_logits[b] = np.log(probs) * self.sampling_temperature

        if single:
            return masked_logits[0]
        return masked_logits

    def get_next_state(self, current_state: int, token: int, step: int) -> int:
        """
        Get the next trie state after emitting a token.

        Returns -1 if the transition is invalid.
        """
        children = self._get_children_cached(current_state, step)
        for child_token, next_state in children:
            if child_token == token:
                return next_state
        return -1

    def _get_valid_mask(
        self, state: int, step: int, vocab_size: int
    ) -> np.ndarray:
        """Build a boolean mask of valid tokens for a given state and step."""
        mask = np.zeros(vocab_size, dtype=np.bool_)

        if step == 0:
            mask_len = min(vocab_size, len(self.index.start_mask))
            mask[:mask_len] = self.index.start_mask[:mask_len]
            return mask

        children = self._get_children_cached(state, step)
        for token, _ in children:
            if 0 <= token < vocab_size:
                mask[token] = True

        return mask

    def _get_children_cached(
        self, state: int, step: int
    ) -> List[Tuple[int, int]]:
        """Get children with caching for repeated lookups."""
        cache_key = (state, step)
        if cache_key in self._transition_cache:
            self._cache_hits += 1
            return self._transition_cache[cache_key]

        self._cache_misses += 1
        children = self._get_children(state, step)
        self._transition_cache[cache_key] = children
        return children

    def _get_children(
        self, state: int, step: int
    ) -> List[Tuple[int, int]]:
        """Get children of a state using dense or sparse path."""
        children = []
        index = self.index

        # Try dense path
        if step < index.dense_masks.shape[0] and state < index.dense_masks.shape[1]:
            slot_mask = index.dense_masks[step, state]
            for slot in range(len(slot_mask)):
                if slot_mask[slot]:
                    token = int(index.dense_states[step, state, slot, 0])
                    next_state = int(index.dense_states[step, state, slot, 1])
                    children.append((token, next_state))
            if children:
                return children

        # CSR sparse path
        if state + 1 < len(index.csr_indptr):
            start = int(index.csr_indptr[state])
            end = int(index.csr_indptr[state + 1])
            for idx in range(start, end):
                if idx < len(index.csr_packed):
                    token = int(index.csr_packed[idx, 0])
                    next_state = int(index.csr_packed[idx, 1])
                    children.append((token, next_state))

        return children

    def reset_cache(self) -> None:
        """Clear the transition cache."""
        self._transition_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0

    def cache_stats(self) -> Dict[str, int]:
        return {
            "cache_size": len(self._transition_cache),
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
        }

    def create_ollama_logit_processor(self) -> Callable:
        """
        Create a logit processor compatible with Ollama's generation API.

        Returns a callable that can be used as a logit bias function.
        The processor maintains internal state across decoding steps.
        """
        step_counter = [0]
        current_state = [0]

        def processor(logits: np.ndarray) -> np.ndarray:
            step = step_counter[0]
            state = current_state[0]

            masked = self.apply_mask(logits, [state], step)

            # Find which token will be selected (argmax for greedy)
            selected_token = int(np.argmax(masked))
            next_state = self.get_next_state(state, selected_token, step)

            if next_state >= 0:
                current_state[0] = next_state
            step_counter[0] += 1

            return masked

        return processor


def _softmax(x: np.ndarray) -> np.ndarray:
    """Numerically stable softmax."""
    x_max = np.max(x)
    exp_x = np.exp(x - x_max)
    return exp_x / exp_x.sum()
