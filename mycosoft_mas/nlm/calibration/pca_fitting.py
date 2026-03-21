"""Per-layer PCA fitting on captured KV tensors.

For each layer, computes:
- Mean vectors (μk, μv) for centering
- Principal component matrices (Vk, Vv) via SVD
- Singular values for importance-weighted bit allocation

Date: 2026-03-21
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def fit_pca_per_layer(
    kv_tensors: dict[str, Any],
    rank_cap: int = 10_000,
) -> dict[str, Any]:
    """Fit PCA projection matrices per layer on captured KV tensors.

    For each layer l:
        1. Center: K_centered = K[l] - mean(K[l])
        2. SVD: U, S, Vt = svd(K_centered)
        3. Keep top-rank_cap components
        4. Store Vk[l] = Vt[:rank_cap], μk[l] = mean(K[l])
        Same for V tensors.

    Args:
        kv_tensors: Output from capture.capture_kv_tensors().
        rank_cap: Maximum number of PCA components per layer.

    Returns:
        Dict with:
            projections: {layer_idx: {vk, vv, muk, muv, sk, sv}}
            effective_rank: int (actual rank used)
            num_layers: int
    """
    keys = kv_tensors.get("keys", {})
    values = kv_tensors.get("values", {})

    if not keys:
        logger.warning("No KV tensors provided — returning empty PCA result")
        return {
            "projections": {},
            "effective_rank": 0,
            "num_layers": 0,
        }

    try:
        import torch

        projections: dict[int, dict[str, Any]] = {}
        effective_rank = rank_cap

        for layer_idx in sorted(keys.keys()):
            k_tensor = keys[layer_idx]  # (tokens, num_heads, head_dim) or (tokens, head_dim)
            v_tensor = values[layer_idx]

            # Flatten heads if present: (tokens, num_heads, head_dim) -> (tokens * num_heads, head_dim)
            if k_tensor.dim() == 3:
                tokens, num_heads, head_dim = k_tensor.shape
                k_flat = k_tensor.reshape(-1, head_dim).float()
                v_flat = v_tensor.reshape(-1, head_dim).float()
            else:
                k_flat = k_tensor.float()
                v_flat = v_tensor.float()

            # Center
            mu_k = k_flat.mean(dim=0)
            mu_v = v_flat.mean(dim=0)
            k_centered = k_flat - mu_k
            v_centered = v_flat - mu_v

            # SVD
            # For large tensors, use randomized SVD via torch.svd_lowrank
            actual_rank = min(rank_cap, k_centered.shape[1], k_centered.shape[0])

            try:
                u_k, s_k, v_k = torch.svd_lowrank(k_centered, q=actual_rank)
                u_v, s_v, v_v = torch.svd_lowrank(v_centered, q=actual_rank)
            except Exception:
                # Fallback to full SVD for small tensors
                u_k, s_k, v_k = torch.linalg.svd(k_centered, full_matrices=False)
                u_v, s_v, v_v = torch.linalg.svd(v_centered, full_matrices=False)
                v_k = v_k[:actual_rank]
                s_k = s_k[:actual_rank]
                v_v = v_v[:actual_rank]
                s_v = s_v[:actual_rank]

            effective_rank = min(effective_rank, actual_rank)

            projections[layer_idx] = {
                "vk": v_k.cpu(),  # (rank, head_dim)
                "vv": v_v.cpu(),
                "muk": mu_k.cpu(),  # (head_dim,)
                "muv": mu_v.cpu(),
                "sk": s_k.cpu(),  # (rank,) — singular values for bit allocation
                "sv": s_v.cpu(),
            }

            if layer_idx % 10 == 0:
                logger.info(
                    "PCA layer %d: rank=%d variance_explained_k=%.3f variance_explained_v=%.3f",
                    layer_idx,
                    actual_rank,
                    (s_k[:actual_rank] ** 2).sum().item()
                    / (k_centered.norm() ** 2).item()
                    if k_centered.norm().item() > 0
                    else 0.0,
                    (s_v[:actual_rank] ** 2).sum().item()
                    / (v_centered.norm() ** 2).item()
                    if v_centered.norm().item() > 0
                    else 0.0,
                )

        logger.info(
            "PCA complete: %d layers, effective_rank=%d",
            len(projections),
            effective_rank,
        )

        return {
            "projections": projections,
            "effective_rank": effective_rank,
            "num_layers": len(projections),
        }

    except ImportError:
        logger.warning("torch not available — returning empty PCA result")
        return {
            "projections": {},
            "effective_rank": 0,
            "num_layers": 0,
            "error": "torch not installed",
        }
