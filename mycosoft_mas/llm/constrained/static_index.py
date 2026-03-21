"""
STATIC Index Builder

Implements the core STATIC algorithm: converting valid token sequences into a
hybrid dense/sparse CSR (Compressed Sparse Row) matrix for O(1) constraint
masking during LLM decoding.

Based on: Su et al., "Vectorizing the Trie: Efficient Constrained Decoding for
LLM-based Generative Retrieval on Accelerators" (2026)

The index has two tiers:
1. Dense lookup tables for initial trie layers (O(1) access, high fan-out)
2. CSR sparse matrices for deeper layers (memory-efficient, O(log K) access)

Created: March 3, 2026
"""

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class IndexConfig:
    """Configuration for STATIC index construction."""

    vocab_size: int = 32000
    dense_depth: int = 2
    max_depth: Optional[int] = None
    enable_compression: bool = True
    dtype: str = "int32"


@dataclass
class STATICIndex:
    """
    Hybrid dense/sparse trie index for constrained decoding.

    Attributes:
        start_mask: Boolean vector of valid first tokens (vocab_size,)
        dense_masks: Dense lookup tables for initial layers
                     Shape: (dense_depth, vocab_size, max_children)
        dense_states: State ID lookup for dense layers
                      Shape: (dense_depth, vocab_size, max_children)
        csr_indptr: CSR row pointers for sparse layers
        csr_packed: Packed [token_id, next_state] pairs for CSR
        num_states: Total number of unique trie states
        max_depth: Maximum sequence depth in the index
        layer_branching: Max branching factor per layer
        config: Index configuration used during build
        build_time_ms: Time taken to build the index
        num_sequences: Number of sequences indexed
    """

    start_mask: np.ndarray
    dense_masks: np.ndarray
    dense_states: np.ndarray
    csr_indptr: np.ndarray
    csr_packed: np.ndarray
    num_states: int
    max_depth: int
    layer_branching: List[int]
    config: IndexConfig
    build_time_ms: float = 0.0
    num_sequences: int = 0

    def memory_usage_bytes(self) -> int:
        """Calculate total memory usage of the index."""
        total = 0
        for arr in [
            self.start_mask,
            self.dense_masks,
            self.dense_states,
            self.csr_indptr,
            self.csr_packed,
        ]:
            total += arr.nbytes
        return total

    def memory_usage_mb(self) -> float:
        return self.memory_usage_bytes() / (1024 * 1024)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize index metadata (not arrays) for API responses."""
        return {
            "num_states": self.num_states,
            "max_depth": self.max_depth,
            "num_sequences": self.num_sequences,
            "layer_branching": self.layer_branching,
            "memory_mb": round(self.memory_usage_mb(), 2),
            "build_time_ms": round(self.build_time_ms, 2),
            "config": {
                "vocab_size": self.config.vocab_size,
                "dense_depth": self.config.dense_depth,
            },
        }

    def save(self, path: str) -> None:
        """Save index to disk as compressed numpy archive."""
        np.savez_compressed(
            path,
            start_mask=self.start_mask,
            dense_masks=self.dense_masks,
            dense_states=self.dense_states,
            csr_indptr=self.csr_indptr,
            csr_packed=self.csr_packed,
            metadata=np.array(
                [self.num_states, self.max_depth, self.num_sequences],
                dtype=np.int64,
            ),
            layer_branching=np.array(self.layer_branching, dtype=np.int32),
            config=np.array(
                [self.config.vocab_size, self.config.dense_depth],
                dtype=np.int32,
            ),
        )
        logger.info(f"Saved STATIC index to {path}")

    @classmethod
    def load(cls, path: str) -> "STATICIndex":
        """Load index from disk."""
        data = np.load(path, allow_pickle=False)
        metadata = data["metadata"]
        config_arr = data["config"]
        config = IndexConfig(
            vocab_size=int(config_arr[0]),
            dense_depth=int(config_arr[1]),
        )
        return cls(
            start_mask=data["start_mask"],
            dense_masks=data["dense_masks"],
            dense_states=data["dense_states"],
            csr_indptr=data["csr_indptr"],
            csr_packed=data["csr_packed"],
            num_states=int(metadata[0]),
            max_depth=int(metadata[1]),
            num_sequences=int(metadata[2]),
            layer_branching=data["layer_branching"].tolist(),
            config=config,
        )


def build_static_index(
    sequences: np.ndarray,
    config: Optional[IndexConfig] = None,
) -> STATICIndex:
    """
    Build a STATIC index from valid token sequences.

    This implements the core algorithm from the paper:
    1. Sort sequences and detect unique trie prefixes via vectorized diff
    2. Assign state IDs to each unique prefix
    3. Collect parent→child edges across all depths
    4. Build dense lookup tables for initial layers
    5. Build CSR matrix for deeper layers

    Args:
        sequences: 2D array of shape (num_sequences, max_length) containing
                   valid token ID sequences. Padded with -1 for variable length.
        config: Index configuration. Uses defaults if None.

    Returns:
        STATICIndex with hybrid dense/sparse representation.
    """
    t0 = time.time()
    config = config or IndexConfig()

    if sequences.ndim != 2:
        raise ValueError(f"sequences must be 2D, got shape {sequences.shape}")

    num_sequences, max_len = sequences.shape
    if config.max_depth is not None:
        max_len = min(max_len, config.max_depth)
        sequences = sequences[:, :max_len]

    vocab_size = config.vocab_size
    dtype = np.int32

    # Sort sequences for efficient prefix detection
    sort_keys = [sequences[:, i] for i in range(max_len - 1, -1, -1)]
    sort_idx = np.lexsort(sort_keys)
    sorted_seqs = sequences[sort_idx]

    logger.info(
        f"Building STATIC index: {num_sequences} sequences, "
        f"max_depth={max_len}, vocab_size={vocab_size}"
    )

    # --- Step 1: Detect unique prefixes at each depth ---
    # A new node is created when the prefix up to depth d differs
    # from the previous sequence's prefix at the same depth.
    state_ids = np.zeros((num_sequences, max_len), dtype=dtype)
    next_state_id = 1  # 0 is reserved for root

    # Track edges: list of (depth, parent_state, token, child_state)
    edges: List[Tuple[int, int, int, int]] = []
    layer_branching: List[int] = []

    for d in range(max_len):
        if d == 0:
            # Level 0: unique first tokens
            unique_tokens, inverse = np.unique(sorted_seqs[:, 0], return_inverse=True)
            # Filter out padding (-1)
            valid_mask = unique_tokens >= 0
            token_to_state = {}
            for tok in unique_tokens[valid_mask]:
                token_to_state[int(tok)] = next_state_id
                edges.append((0, 0, int(tok), next_state_id))
                next_state_id += 1
            # Assign state IDs
            for i in range(num_sequences):
                tok = int(sorted_seqs[i, 0])
                if tok >= 0:
                    state_ids[i, 0] = token_to_state[tok]
            layer_branching.append(len(token_to_state))
        else:
            # For depth d, a new node exists when prefix[:d+1] differs
            # from the previous row's prefix[:d+1]
            prev_prefix = sorted_seqs[:-1, : d + 1]
            curr_prefix = sorted_seqs[1:, : d + 1]
            differs = np.any(prev_prefix != curr_prefix, axis=1)

            # First row at this depth is always a new node (if valid)
            new_node_mask = np.concatenate([[True], differs])

            # Only consider rows where token at depth d is valid
            valid_at_d = sorted_seqs[:, d] >= 0
            new_node_mask &= valid_at_d

            branching_count = 0
            parent_children: Dict[int, int] = {}

            for i in range(num_sequences):
                if not valid_at_d[i]:
                    continue

                parent_state = int(state_ids[i, d - 1])
                token = int(sorted_seqs[i, d])

                if new_node_mask[i]:
                    child_state = next_state_id
                    next_state_id += 1
                    state_ids[i, d] = child_state
                    edges.append((d, parent_state, token, child_state))
                    branching_count += 1

                    # Track children per parent for branching stats
                    parent_children[parent_state] = parent_children.get(parent_state, 0) + 1
                else:
                    # Same node as previous row at this depth
                    state_ids[i, d] = state_ids[i - 1, d]

            max_branch = max(parent_children.values()) if parent_children else 0
            layer_branching.append(max_branch)

    num_states = next_state_id
    logger.info(f"Trie has {num_states} states, {len(edges)} edges")

    # --- Step 2: Build start mask ---
    start_mask = np.zeros(vocab_size, dtype=np.bool_)
    for depth, parent, token, child in edges:
        if depth == 0 and 0 <= token < vocab_size:
            start_mask[token] = True

    # --- Step 3: Build dense lookup tables for initial layers ---
    dense_depth = min(config.dense_depth, max_len)

    # For each dense layer, we need: given a state, what tokens are valid
    # and what states do they lead to?
    # Dense representation: state → list of (token, next_state)
    edges_by_depth: Dict[int, List[Tuple[int, int, int]]] = {}
    for depth, parent, token, child in edges:
        if depth not in edges_by_depth:
            edges_by_depth[depth] = []
        edges_by_depth[depth].append((parent, token, child))

    # Compute max children across dense layers for array sizing
    max_children_dense = 1
    for d in range(dense_depth):
        depth_edges = edges_by_depth.get(d, [])
        children_per_parent: Dict[int, int] = {}
        for parent, token, child in depth_edges:
            children_per_parent[parent] = children_per_parent.get(parent, 0) + 1
        if children_per_parent:
            max_children_dense = max(max_children_dense, max(children_per_parent.values()))

    # Build dense arrays
    # dense_masks[d][state] = boolean mask of valid children slots
    # dense_states[d][state][slot] = (token, next_state) packed as int64
    dense_masks = np.zeros((dense_depth, num_states, max_children_dense), dtype=np.bool_)
    dense_states = np.zeros((dense_depth, num_states, max_children_dense, 2), dtype=dtype)

    for d in range(dense_depth):
        depth_edges = edges_by_depth.get(d, [])
        # Group by parent
        parent_edges: Dict[int, List[Tuple[int, int]]] = {}
        for parent, token, child in depth_edges:
            if parent not in parent_edges:
                parent_edges[parent] = []
            parent_edges[parent].append((token, child))

        for parent, children in parent_edges.items():
            for slot, (token, child_state) in enumerate(children):
                if slot < max_children_dense:
                    dense_masks[d, parent, slot] = True
                    dense_states[d, parent, slot, 0] = token
                    dense_states[d, parent, slot, 1] = child_state

    # --- Step 4: Build CSR for sparse layers ---
    # Collect all edges for depths >= dense_depth
    sparse_edges: List[Tuple[int, int, int]] = []
    for d in range(dense_depth, max_len):
        for parent, token, child in edges_by_depth.get(d, []):
            sparse_edges.append((parent, token, child))

    # Sort by parent state for CSR construction
    if sparse_edges:
        sparse_edges.sort(key=lambda x: x[0])

        # Build CSR indptr and packed data
        max_parent = max(e[0] for e in sparse_edges)
        csr_indptr = np.zeros(max_parent + 2, dtype=dtype)
        csr_packed = np.zeros((len(sparse_edges), 2), dtype=dtype)

        for idx, (parent, token, child) in enumerate(sparse_edges):
            csr_packed[idx, 0] = token
            csr_packed[idx, 1] = child
            csr_indptr[parent + 1] += 1

        # Cumulative sum for CSR row pointers
        np.cumsum(csr_indptr, out=csr_indptr)
    else:
        csr_indptr = np.zeros(2, dtype=dtype)
        csr_packed = np.zeros((0, 2), dtype=dtype)

    build_time = (time.time() - t0) * 1000

    index = STATICIndex(
        start_mask=start_mask,
        dense_masks=dense_masks,
        dense_states=dense_states,
        csr_indptr=csr_indptr,
        csr_packed=csr_packed,
        num_states=num_states,
        max_depth=max_len,
        layer_branching=layer_branching,
        config=config,
        build_time_ms=build_time,
        num_sequences=num_sequences,
    )

    logger.info(
        f"STATIC index built in {build_time:.1f}ms | "
        f"{num_states} states | {index.memory_usage_mb():.2f} MB"
    )

    return index


def build_index_from_strings(
    valid_strings: List[str],
    tokenizer_fn,
    config: Optional[IndexConfig] = None,
    pad_value: int = -1,
) -> STATICIndex:
    """
    Build a STATIC index from a list of valid strings.

    Convenience wrapper that tokenizes strings before building the index.

    Args:
        valid_strings: List of valid output strings to constrain to.
        tokenizer_fn: Callable that maps str → List[int] token IDs.
        config: Index configuration.
        pad_value: Padding value for variable-length sequences.

    Returns:
        STATICIndex
    """
    tokenized = [tokenizer_fn(s) for s in valid_strings]
    max_len = max(len(t) for t in tokenized) if tokenized else 1

    sequences = np.full((len(tokenized), max_len), pad_value, dtype=np.int32)
    for i, tokens in enumerate(tokenized):
        sequences[i, : len(tokens)] = tokens

    return build_static_index(sequences, config)
