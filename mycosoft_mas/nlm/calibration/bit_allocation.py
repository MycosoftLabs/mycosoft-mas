"""Dynamic programming bit allocation for KVTC.

Given PCA singular values per layer, optimally distributes a bit budget
across PCA components to minimize total reconstruction error subject to
a target compression ratio.

Algorithm: Lagrange-relaxation DP over (layer, component, bits) grid.

Date: 2026-03-21
"""

from __future__ import annotations

import logging
import math
from typing import Any

from mycosoft_mas.serving.schemas import CompressionTarget

logger = logging.getLogger(__name__)

# Compression target -> target bits per dimension (bf16 baseline = 16 bits)
TARGET_BITS: dict[str, float] = {
    "8x": 2.0,     # 16/8
    "16x": 1.0,    # 16/16
    "32x": 0.5,    # 16/32
    "64x": 0.25,   # 16/64
}


def _dp_allocate_layer(
    singular_values: list[float],
    total_bits: int,
    max_bits_per_component: int = 8,
) -> list[int]:
    """Allocate bits to PCA components for one layer using DP.

    Minimize sum of reconstruction errors:
        E = sum_i sigma_i^2 * 2^(-2 * b_i)
    subject to sum_i b_i <= total_bits, 0 <= b_i <= max_bits_per_component.

    This is solved via Lagrangian relaxation: optimal b_i* = 0.5 * log2(sigma_i^2 / lambda)
    then round and redistribute.
    """
    n = len(singular_values)
    if n == 0:
        return []
    if total_bits <= 0:
        return [0] * n

    # Variance per component
    variances = [s ** 2 for s in singular_values]

    # Water-filling: b_i = max(0, min(max_bits, 0.5 * log2(var_i / lambda)))
    # Binary search for lambda
    lo, hi = 1e-20, max(variances) + 1.0
    for _ in range(100):
        lam = (lo + hi) / 2.0
        bits = []
        for v in variances:
            if v <= 0 or lam <= 0:
                bits.append(0)
            else:
                b = 0.5 * math.log2(v / lam) if v > lam else 0.0
                b = max(0.0, min(float(max_bits_per_component), b))
                bits.append(b)
        total = sum(bits)
        if total > total_bits:
            lo = lam
        else:
            hi = lam

    # Round to integers, greedy redistribute remainder
    int_bits = [max(0, min(max_bits_per_component, round(b))) for b in bits]
    used = sum(int_bits)

    # Redistribute surplus/deficit greedily by marginal gain
    while used > total_bits:
        # Remove bit from component with smallest marginal cost
        best_idx = -1
        best_cost = float("inf")
        for i in range(n):
            if int_bits[i] > 0:
                cost = variances[i] * (2 ** (-2 * (int_bits[i] - 1)) - 2 ** (-2 * int_bits[i]))
                if cost < best_cost:
                    best_cost = cost
                    best_idx = i
        if best_idx < 0:
            break
        int_bits[best_idx] -= 1
        used -= 1

    while used < total_bits:
        best_idx = -1
        best_gain = -1.0
        for i in range(n):
            if int_bits[i] < max_bits_per_component:
                gain = variances[i] * (2 ** (-2 * int_bits[i]) - 2 ** (-2 * (int_bits[i] + 1)))
                if gain > best_gain:
                    best_gain = gain
                    best_idx = i
        if best_idx < 0 or best_gain <= 0:
            break
        int_bits[best_idx] += 1
        used += 1

    return int_bits


def allocate_bits(
    pca_result: dict[str, Any],
    compression_target: CompressionTarget,
    num_layers: int,
    head_dim: int,
) -> dict[str, Any]:
    """Allocate bits across all layers for the target compression ratio.

    Args:
        pca_result: Output from pca_fitting.fit_pca_per_layer().
        compression_target: Target compression (8x, 16x, 32x, 64x).
        num_layers: Number of model layers.
        head_dim: Dimension per attention head.

    Returns:
        Dict with:
            key_bitplan: {layer_idx: [bits_per_component]}
            value_bitplan: {layer_idx: [bits_per_component]}
            total_key_bits: int
            total_value_bits: int
            target_bits_per_dim: float
    """
    target_bpd = TARGET_BITS.get(compression_target.value, 1.0)
    projections = pca_result.get("projections", {})
    effective_rank = pca_result.get("effective_rank", head_dim)

    # Total bit budget per layer = rank * target_bits_per_dim
    bits_per_layer = int(effective_rank * target_bpd)

    key_bitplan: dict[int, list[int]] = {}
    value_bitplan: dict[int, list[int]] = {}
    total_key_bits = 0
    total_value_bits = 0

    for layer_idx in sorted(projections.keys()):
        proj = projections[layer_idx]

        # Extract singular values as plain lists
        sk = proj.get("sk", [])
        sv = proj.get("sv", [])

        try:
            sk_list = sk.tolist() if hasattr(sk, "tolist") else list(sk)
            sv_list = sv.tolist() if hasattr(sv, "tolist") else list(sv)
        except Exception:
            sk_list = [1.0] * effective_rank
            sv_list = [1.0] * effective_rank

        key_bits = _dp_allocate_layer(sk_list, bits_per_layer)
        value_bits = _dp_allocate_layer(sv_list, bits_per_layer)

        key_bitplan[layer_idx] = key_bits
        value_bitplan[layer_idx] = value_bits
        total_key_bits += sum(key_bits)
        total_value_bits += sum(value_bits)

    logger.info(
        "Bit allocation: target=%s bpd=%.2f layers=%d total_key_bits=%d total_value_bits=%d",
        compression_target.value,
        target_bpd,
        len(key_bitplan),
        total_key_bits,
        total_value_bits,
    )

    return {
        "key_bitplan": key_bitplan,
        "value_bitplan": value_bitplan,
        "total_key_bits": total_key_bits,
        "total_value_bits": total_value_bits,
        "target_bits_per_dim": target_bpd,
        "effective_rank": effective_rank,
    }
