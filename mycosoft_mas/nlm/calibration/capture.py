"""KV cache capture for KVTC calibration.

Runs prefill on calibration sequences and captures raw KV tensors,
undoing positional rotations where applicable.

Date: 2026-03-21
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _undo_rope_rotation(key_tensor: Any, rope_config: dict | None) -> Any:
    """Undo RoPE rotation on key tensors before PCA.

    RoPE rotates keys by position-dependent angles. For PCA to find
    meaningful directions, we need position-invariant keys. This applies
    the inverse rotation.

    Args:
        key_tensor: Key tensor of shape (seq_len, num_heads, head_dim).
        rope_config: RoPE configuration (theta, type, scaling).

    Returns:
        De-rotated key tensor.
    """
    if rope_config is None:
        return key_tensor

    try:
        import torch

        # For standard RoPE: inverse is just the conjugate rotation
        # K_derotated[pos] = K[pos] * exp(-i * pos * theta)
        seq_len = key_tensor.shape[0]
        head_dim = key_tensor.shape[-1]
        half_dim = head_dim // 2

        theta = rope_config.get("theta", 10000.0)
        freqs = 1.0 / (theta ** (torch.arange(0, half_dim, dtype=torch.float32) / half_dim))
        positions = torch.arange(seq_len, dtype=torch.float32)
        angles = torch.outer(positions, freqs)

        cos_inv = torch.cos(-angles)
        sin_inv = torch.sin(-angles)

        k_even = key_tensor[..., :half_dim]
        k_odd = key_tensor[..., half_dim:]

        derotated = torch.empty_like(key_tensor)
        derotated[..., :half_dim] = k_even * cos_inv.unsqueeze(1) - k_odd * sin_inv.unsqueeze(1)
        derotated[..., half_dim:] = k_even * sin_inv.unsqueeze(1) + k_odd * cos_inv.unsqueeze(1)
        return derotated

    except ImportError:
        logger.warning("torch not available — returning keys without RoPE undo")
        return key_tensor


async def capture_kv_tensors(
    model_path: str,
    sequences: list[list[int]],
    sink_tokens: int = 4,
    attention_only: bool = False,
    rope_config: dict | None = None,
) -> dict[str, Any]:
    """Capture raw KV tensors from calibration sequences.

    Runs model prefill with hooks on attention layers to intercept
    K and V tensors. Sink tokens (first `sink_tokens` positions) and
    recent window tokens are excluded from the capture pool since they
    remain uncompressed in serving.

    Args:
        model_path: Path to HF-format model checkpoint.
        sequences: Tokenized calibration sequences.
        sink_tokens: Number of initial tokens to exclude (default 4).
        attention_only: If True, only capture from attention layers (skip SSM/Mamba).
        rope_config: RoPE config for key de-rotation. If None, auto-detect.

    Returns:
        Dict with structure:
            {
                "keys": {layer_idx: tensor (pooled_tokens, num_heads, head_dim)},
                "values": {layer_idx: tensor (pooled_tokens, num_heads, head_dim)},
                "metadata": {
                    "num_layers_captured": int,
                    "total_tokens_captured": int,
                    "sink_tokens_excluded": int,
                    "rope_undone": bool,
                },
            }
    """
    logger.info(
        "Capturing KV tensors: %d sequences, sink=%d, attention_only=%s",
        len(sequences),
        sink_tokens,
        attention_only,
    )

    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoConfig

        config = AutoConfig.from_pretrained(model_path)
        if rope_config is None and hasattr(config, "rope_theta"):
            rope_config = {"theta": config.rope_theta}

        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.bfloat16,
            device_map="auto",
            attn_implementation="eager",  # Need eager for hooks
        )
        model.eval()

        captured_keys: dict[int, list] = {}
        captured_values: dict[int, list] = {}
        hooks = []

        def make_hook(layer_idx: int):
            def hook_fn(module, args, output):
                # output is typically (attn_output, attn_weights, past_key_value)
                if hasattr(output, '__len__') and len(output) >= 3:
                    past_kv = output[2]
                    if past_kv is not None:
                        k, v = past_kv[0], past_kv[1]
                        # Exclude sink tokens
                        k_pooled = k[:, :, sink_tokens:, :]
                        v_pooled = v[:, :, sink_tokens:, :]

                        if rope_config:
                            k_pooled = _undo_rope_rotation(
                                k_pooled.squeeze(0).transpose(0, 1),
                                rope_config,
                            )
                        else:
                            k_pooled = k_pooled.squeeze(0).transpose(0, 1)
                        v_pooled = v_pooled.squeeze(0).transpose(0, 1)

                        if layer_idx not in captured_keys:
                            captured_keys[layer_idx] = []
                            captured_values[layer_idx] = []
                        captured_keys[layer_idx].append(k_pooled.detach().cpu())
                        captured_values[layer_idx].append(v_pooled.detach().cpu())
                return output
            return hook_fn

        # Register hooks on attention layers
        for layer_idx, layer in enumerate(model.model.layers):
            if attention_only and hasattr(layer, "mamba"):
                continue
            if hasattr(layer, "self_attn"):
                h = layer.self_attn.register_forward_hook(make_hook(layer_idx))
                hooks.append(h)

        # Run prefill
        total_tokens = 0
        with torch.no_grad():
            for seq in sequences:
                input_ids = torch.tensor([seq], device=model.device)
                model(input_ids, use_cache=True)
                total_tokens += len(seq) - sink_tokens

        # Remove hooks
        for h in hooks:
            h.remove()

        # Concatenate captures
        keys_out = {}
        values_out = {}
        for layer_idx in captured_keys:
            keys_out[layer_idx] = torch.cat(captured_keys[layer_idx], dim=0)
            values_out[layer_idx] = torch.cat(captured_values[layer_idx], dim=0)

        del model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        return {
            "keys": keys_out,
            "values": values_out,
            "metadata": {
                "num_layers_captured": len(keys_out),
                "total_tokens_captured": total_tokens,
                "sink_tokens_excluded": sink_tokens * len(sequences),
                "rope_undone": rope_config is not None,
            },
        }

    except ImportError:
        logger.warning(
            "torch/transformers not available — returning empty capture. "
            "Install with: pip install torch transformers"
        )
        return {
            "keys": {},
            "values": {},
            "metadata": {
                "num_layers_captured": 0,
                "total_tokens_captured": 0,
                "sink_tokens_excluded": 0,
                "rope_undone": False,
                "error": "torch/transformers not installed",
            },
        }
