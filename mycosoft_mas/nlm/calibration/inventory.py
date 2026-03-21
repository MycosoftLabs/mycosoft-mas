"""Model architecture inventory for KVTC compatibility assessment.

Scans a model build and returns:
- architecture type (decoder-only MHA/GQA/MQA, hybrid attention+Mamba, MLA)
- KV cache geometry (layers, heads, head_dim)
- RoPE/positional embedding type
- whether kvtc is applicable and in what mode

Date: 2026-03-21
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from mycosoft_mas.serving.schemas import ArchitectureType, ModelInventoryResult

logger = logging.getLogger(__name__)


def _detect_architecture(config: dict[str, Any]) -> ArchitectureType:
    """Detect model architecture type from HF-format config.json fields."""
    model_type = config.get("model_type", "").lower()

    # Check for Mamba/SSM indicators (must check before standard attention)
    has_mamba = any(
        k in config
        for k in ("mamba_d_state", "ssm_cfg", "mamba_layers", "ssm_d_state")
    )
    # model_type contains "mamba" (e.g., "jamba", "mamba", "zamba")
    if has_mamba or "mamba" in model_type or model_type in ("jamba", "zamba"):
        return ArchitectureType.HYBRID_ATTENTION_MAMBA

    # Check for MoE indicators
    has_moe = any(
        k in config
        for k in ("num_experts", "num_local_experts", "moe_num_experts")
    )
    if has_moe:
        return ArchitectureType.HYBRID_ATTENTION_MOE

    # Check for MLA (Multi-head Latent Attention) — DeepSeek-style
    if config.get("kv_lora_rank") or config.get("qk_nope_head_dim"):
        return ArchitectureType.MLA_LATENT

    # Standard attention — MHA, GQA, or MQA
    num_attn_heads = config.get("num_attention_heads", 0)
    num_kv_heads = config.get("num_key_value_heads", num_attn_heads)

    if num_attn_heads == 0:
        return ArchitectureType.UNKNOWN

    if num_kv_heads == 1:
        return ArchitectureType.DECODER_ONLY_MQA
    elif num_kv_heads < num_attn_heads:
        return ArchitectureType.DECODER_ONLY_GQA
    elif num_kv_heads == num_attn_heads:
        return ArchitectureType.DECODER_ONLY_MHA

    return ArchitectureType.UNKNOWN


def _detect_rope_type(config: dict[str, Any]) -> Optional[str]:
    """Detect positional embedding type."""
    rope_cfg = config.get("rope_scaling")
    if rope_cfg:
        rope_type = rope_cfg.get("type", rope_cfg.get("rope_type", ""))
        if rope_type:
            return rope_type.lower()

    if config.get("rope_theta") or config.get("rotary_emb_base"):
        return "rope"

    if config.get("alibi_bias"):
        return "alibi"

    return None


def _determine_kvtc_eligibility(
    arch_type: ArchitectureType,
) -> tuple[bool, Optional[str], str]:
    """Return (eligible, mode, notes) for KVTC based on architecture.

    Returns:
        Tuple of (kvtc_eligible, kvtc_mode, notes).
    """
    mapping = {
        ArchitectureType.DECODER_ONLY_MHA: (
            True,
            "full_kv",
            "Standard MHA — full KV cache eligible for KVTC",
        ),
        ArchitectureType.DECODER_ONLY_GQA: (
            True,
            "full_kv",
            "GQA — full KV cache eligible for KVTC",
        ),
        ArchitectureType.DECODER_ONLY_MQA: (
            True,
            "full_kv",
            "MQA — single KV head, eligible but lower savings",
        ),
        ArchitectureType.HYBRID_ATTENTION_MAMBA: (
            True,
            "attention_only",
            "Hybrid — KVTC applies to attention layers ONLY. Mamba state is NEVER compressed.",
        ),
        ArchitectureType.HYBRID_ATTENTION_MOE: (
            True,
            "full_kv",
            "MoE — KV cache from attention layers eligible. Expert routing unaffected.",
        ),
        ArchitectureType.MLA_LATENT: (
            True,
            "latent_cache",
            "MLA — compress latent KV cache, not projected KV",
        ),
        ArchitectureType.UNKNOWN: (
            False,
            None,
            "Unknown architecture — KVTC not applicable without manual review",
        ),
    }
    return mapping.get(arch_type, (False, None, "Unrecognized architecture"))


def inventory_model(
    model_build_id: str,
    model_path: str,
    config_override: Optional[dict[str, Any]] = None,
) -> ModelInventoryResult:
    """Inspect a model's config and return KVTC compatibility assessment.

    Args:
        model_build_id: UUID string of the model build.
        model_path: Path to HF-format checkpoint directory (contains config.json).
        config_override: Optional config dict to use instead of loading from disk.

    Returns:
        ModelInventoryResult with architecture classification and KVTC eligibility.
    """
    # Load config
    if config_override:
        config = config_override
    else:
        config_path = Path(model_path) / "config.json"
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
        else:
            logger.warning(
                "No config.json found at %s — returning unknown architecture",
                config_path,
            )
            return ModelInventoryResult(
                model_build_id=model_build_id,
                architecture_type=ArchitectureType.UNKNOWN,
                num_layers=0,
                num_kv_heads=0,
                head_dim=0,
                kv_cache_bytes_per_1k_tokens=0,
                kvtc_eligible=False,
                notes=f"config.json not found at {model_path}",
            )

    # Extract geometry
    arch_type = _detect_architecture(config)
    num_layers = config.get("num_hidden_layers", config.get("n_layer", 0))
    num_attn_heads = config.get("num_attention_heads", config.get("n_head", 0))
    num_kv_heads = config.get("num_key_value_heads", num_attn_heads)
    hidden_size = config.get("hidden_size", config.get("n_embd", 0))
    head_dim = config.get("head_dim", hidden_size // max(num_attn_heads, 1))
    rope_type = _detect_rope_type(config)

    # KV cache size: 2 (K+V) * num_layers * num_kv_heads * head_dim * 2 (bf16) * 1000 tokens
    kv_cache_bytes_per_1k = 2 * num_layers * num_kv_heads * head_dim * 2 * 1000

    # KVTC eligibility
    kvtc_eligible, kvtc_mode, notes = _determine_kvtc_eligibility(arch_type)

    has_mamba = arch_type == ArchitectureType.HYBRID_ATTENTION_MAMBA
    has_moe = arch_type == ArchitectureType.HYBRID_ATTENTION_MOE
    mla_latent = arch_type == ArchitectureType.MLA_LATENT

    result = ModelInventoryResult(
        model_build_id=model_build_id,
        architecture_type=arch_type,
        num_layers=num_layers,
        num_kv_heads=num_kv_heads,
        head_dim=head_dim,
        rope_type=rope_type,
        mla_latent=mla_latent,
        has_mamba_layers=has_mamba,
        has_moe_layers=has_moe,
        kv_cache_bytes_per_1k_tokens=kv_cache_bytes_per_1k,
        kvtc_eligible=kvtc_eligible,
        kvtc_mode=kvtc_mode,
        notes=notes,
    )

    logger.info(
        "Inventory for %s: arch=%s eligible=%s mode=%s",
        model_build_id,
        arch_type.value,
        kvtc_eligible,
        kvtc_mode,
    )
    return result
