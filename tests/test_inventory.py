"""Tests for model architecture inventory.

Date: 2026-03-21
"""

import pytest
from uuid import uuid4

from mycosoft_mas.nlm.calibration.inventory import (
    inventory_model,
    _detect_architecture,
    _detect_rope_type,
    _determine_kvtc_eligibility,
)
from mycosoft_mas.serving.schemas import ArchitectureType


class TestDetectArchitecture:
    def test_standard_mha(self):
        config = {"num_attention_heads": 32, "num_key_value_heads": 32}
        assert _detect_architecture(config) == ArchitectureType.DECODER_ONLY_MHA

    def test_gqa(self):
        config = {"num_attention_heads": 32, "num_key_value_heads": 8}
        assert _detect_architecture(config) == ArchitectureType.DECODER_ONLY_GQA

    def test_mqa(self):
        config = {"num_attention_heads": 32, "num_key_value_heads": 1}
        assert _detect_architecture(config) == ArchitectureType.DECODER_ONLY_MQA

    def test_hybrid_mamba(self):
        config = {"num_attention_heads": 32, "mamba_d_state": 16}
        assert _detect_architecture(config) == ArchitectureType.HYBRID_ATTENTION_MAMBA

    def test_hybrid_mamba_model_type(self):
        config = {"model_type": "jamba", "num_attention_heads": 32}
        assert _detect_architecture(config) == ArchitectureType.HYBRID_ATTENTION_MAMBA

    def test_moe(self):
        config = {"num_attention_heads": 32, "num_local_experts": 8}
        assert _detect_architecture(config) == ArchitectureType.HYBRID_ATTENTION_MOE

    def test_mla_latent(self):
        config = {"num_attention_heads": 32, "kv_lora_rank": 512}
        assert _detect_architecture(config) == ArchitectureType.MLA_LATENT

    def test_unknown(self):
        config = {}
        assert _detect_architecture(config) == ArchitectureType.UNKNOWN


class TestDetectRopeType:
    def test_standard_rope(self):
        config = {"rope_theta": 10000.0}
        assert _detect_rope_type(config) == "rope"

    def test_rope_scaling(self):
        config = {"rope_scaling": {"type": "yarn"}}
        assert _detect_rope_type(config) == "yarn"

    def test_alibi(self):
        config = {"alibi_bias": True}
        assert _detect_rope_type(config) == "alibi"

    def test_no_positional(self):
        config = {}
        assert _detect_rope_type(config) is None


class TestKvtcEligibility:
    def test_mha_eligible(self):
        eligible, mode, _ = _determine_kvtc_eligibility(ArchitectureType.DECODER_ONLY_MHA)
        assert eligible is True
        assert mode == "full_kv"

    def test_gqa_eligible(self):
        eligible, mode, _ = _determine_kvtc_eligibility(ArchitectureType.DECODER_ONLY_GQA)
        assert eligible is True
        assert mode == "full_kv"

    def test_hybrid_mamba_attention_only(self):
        eligible, mode, notes = _determine_kvtc_eligibility(
            ArchitectureType.HYBRID_ATTENTION_MAMBA
        )
        assert eligible is True
        assert mode == "attention_only"
        assert "Mamba state is NEVER compressed" in notes

    def test_mla_latent_mode(self):
        eligible, mode, _ = _determine_kvtc_eligibility(ArchitectureType.MLA_LATENT)
        assert eligible is True
        assert mode == "latent_cache"

    def test_unknown_not_eligible(self):
        eligible, mode, _ = _determine_kvtc_eligibility(ArchitectureType.UNKNOWN)
        assert eligible is False
        assert mode is None


class TestInventoryModel:
    def test_inventory_with_config_override(self):
        config = {
            "num_hidden_layers": 32,
            "num_attention_heads": 32,
            "num_key_value_heads": 8,
            "hidden_size": 4096,
            "rope_theta": 10000.0,
        }
        result = inventory_model(
            model_build_id=str(uuid4()),
            model_path="/nonexistent",
            config_override=config,
        )
        assert result.architecture_type == ArchitectureType.DECODER_ONLY_GQA
        assert result.num_layers == 32
        assert result.num_kv_heads == 8
        assert result.head_dim == 128
        assert result.kvtc_eligible is True
        assert result.kvtc_mode == "full_kv"
        assert result.rope_type == "rope"

    def test_inventory_missing_config(self):
        result = inventory_model(
            model_build_id=str(uuid4()),
            model_path="/nonexistent/path",
        )
        assert result.architecture_type == ArchitectureType.UNKNOWN
        assert result.kvtc_eligible is False

    def test_inventory_nemotron_gqa(self):
        """Nemotron-style config: GQA with RoPE."""
        config = {
            "model_type": "nemotron",
            "num_hidden_layers": 40,
            "num_attention_heads": 64,
            "num_key_value_heads": 8,
            "hidden_size": 6144,
            "rope_theta": 500000.0,
        }
        result = inventory_model(
            model_build_id=str(uuid4()),
            model_path="",
            config_override=config,
        )
        assert result.architecture_type == ArchitectureType.DECODER_ONLY_GQA
        assert result.kvtc_eligible is True
        assert result.num_kv_heads == 8
        assert result.head_dim == 96  # 6144 / 64

    def test_inventory_kv_cache_size(self):
        config = {
            "num_hidden_layers": 32,
            "num_attention_heads": 32,
            "num_key_value_heads": 8,
            "hidden_size": 4096,
        }
        result = inventory_model(
            model_build_id=str(uuid4()),
            model_path="",
            config_override=config,
        )
        # 2 * 32 * 8 * 128 * 2 * 1000 = 131,072,000
        expected = 2 * 32 * 8 * 128 * 2 * 1000
        assert result.kv_cache_bytes_per_1k_tokens == expected
