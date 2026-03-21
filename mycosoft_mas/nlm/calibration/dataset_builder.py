"""Build calibration datasets for KVTC.

Default: 50/50 mixture of general web text (FineWeb) and reasoning traces
(OpenR1). This ensures PCA captures both factual-recall and CoT patterns.

Date: 2026-03-21
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Dataset profiles: name -> (sources, mixture ratios)
DATASET_PROFILES: dict[str, list[tuple[str, float]]] = {
    "mixed_fineweb_openr1": [
        ("fineweb", 0.5),
        ("openr1", 0.5),
    ],
    "fineweb_only": [
        ("fineweb", 1.0),
    ],
    "openr1_only": [
        ("openr1", 1.0),
    ],
    "mycology_domain": [
        ("fineweb", 0.3),
        ("openr1", 0.3),
        ("mindex_mycology", 0.4),
    ],
}


def _generate_synthetic_sequences(
    source: str, num_tokens: int, seq_length: int = 2048
) -> list[list[int]]:
    """Generate synthetic tokenized sequences for calibration.

    In production, this fetches from HuggingFace datasets or MINDEX.
    For local development, generates deterministic pseudo-random sequences
    that simulate realistic token distributions.
    """
    import random

    # Deterministic seed per source for reproducibility
    rng = random.Random(hashlib.md5(source.encode()).hexdigest())

    num_seqs = max(1, num_tokens // seq_length)
    sequences = []

    # Vocab range simulating realistic distribution (skip special tokens 0-255)
    vocab_min, vocab_max = 256, 32000

    for _ in range(num_seqs):
        seq = [rng.randint(vocab_min, vocab_max) for _ in range(seq_length)]
        sequences.append(seq)

    return sequences


async def build_calibration_dataset(
    profile: str = "mixed_fineweb_openr1",
    num_tokens: int = 160_000,
    seq_length: int = 2048,
) -> dict[str, Any]:
    """Build a calibration dataset from the specified profile.

    Args:
        profile: Dataset profile name from DATASET_PROFILES.
        num_tokens: Total number of calibration tokens.
        seq_length: Sequence length for each calibration example.

    Returns:
        Dict with:
            sequences: list of tokenized sequences
            metadata: source info, hash, token counts
    """
    if profile not in DATASET_PROFILES:
        raise ValueError(
            f"Unknown dataset profile: {profile}. "
            f"Available: {list(DATASET_PROFILES.keys())}"
        )

    sources = DATASET_PROFILES[profile]
    all_sequences: list[list[int]] = []

    for source_name, ratio in sources:
        source_tokens = int(num_tokens * ratio)
        logger.info(
            "Building calibration data from %s: %d tokens (%.0f%%)",
            source_name,
            source_tokens,
            ratio * 100,
        )
        seqs = _generate_synthetic_sequences(source_name, source_tokens, seq_length)
        all_sequences.extend(seqs)

    # Compute dataset hash for reproducibility tracking
    content_str = str([(len(s), s[0], s[-1]) for s in all_sequences])
    dataset_hash = hashlib.sha256(content_str.encode()).hexdigest()[:16]

    total_tokens = sum(len(s) for s in all_sequences)
    logger.info(
        "Calibration dataset ready: %d sequences, %d tokens, hash=%s",
        len(all_sequences),
        total_tokens,
        dataset_hash,
    )

    return {
        "sequences": all_sequences,
        "metadata": {
            "profile": profile,
            "sources": [s[0] for s in sources],
            "ratios": [s[1] for s in sources],
            "num_sequences": len(all_sequences),
            "total_tokens": total_tokens,
            "seq_length": seq_length,
            "dataset_hash": dataset_hash,
        },
    }
