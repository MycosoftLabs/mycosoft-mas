"""Tests for KVTC calibration pipeline components.

Date: 2026-03-21
"""

import pytest
from mycosoft_mas.nlm.calibration.dataset_builder import (
    build_calibration_dataset,
    DATASET_PROFILES,
    _generate_synthetic_sequences,
)
from mycosoft_mas.nlm.calibration.bit_allocation import (
    _dp_allocate_layer,
    allocate_bits,
    TARGET_BITS,
)
from mycosoft_mas.serving.schemas import CompressionTarget


class TestDatasetBuilder:
    @pytest.mark.asyncio
    async def test_build_default_dataset(self):
        result = await build_calibration_dataset(
            num_tokens=8192, seq_length=512,
        )
        assert "sequences" in result
        assert "metadata" in result
        assert len(result["sequences"]) > 0
        assert result["metadata"]["profile"] == "mixed_fineweb_openr1"

    @pytest.mark.asyncio
    async def test_build_mycology_dataset(self):
        result = await build_calibration_dataset(
            profile="mycology_domain",
            num_tokens=4096,
            seq_length=256,
        )
        assert result["metadata"]["profile"] == "mycology_domain"
        assert "mindex_mycology" in result["metadata"]["sources"]

    @pytest.mark.asyncio
    async def test_unknown_profile_raises(self):
        with pytest.raises(ValueError, match="Unknown dataset profile"):
            await build_calibration_dataset(profile="nonexistent")

    def test_synthetic_sequences_deterministic(self):
        s1 = _generate_synthetic_sequences("test", 1024, 256)
        s2 = _generate_synthetic_sequences("test", 1024, 256)
        assert s1 == s2

    def test_synthetic_sequences_different_sources(self):
        s1 = _generate_synthetic_sequences("fineweb", 1024, 256)
        s2 = _generate_synthetic_sequences("openr1", 1024, 256)
        assert s1 != s2

    def test_all_profiles_valid(self):
        for name, sources in DATASET_PROFILES.items():
            total_ratio = sum(r for _, r in sources)
            assert abs(total_ratio - 1.0) < 0.01, f"Profile {name} ratios don't sum to 1.0"

    @pytest.mark.asyncio
    async def test_dataset_hash_reproducible(self):
        r1 = await build_calibration_dataset(num_tokens=4096, seq_length=256)
        r2 = await build_calibration_dataset(num_tokens=4096, seq_length=256)
        assert r1["metadata"]["dataset_hash"] == r2["metadata"]["dataset_hash"]


class TestBitAllocation:
    def test_dp_allocate_basic(self):
        singular_values = [10.0, 5.0, 2.0, 1.0]
        bits = _dp_allocate_layer(singular_values, total_bits=8)
        assert sum(bits) <= 8
        assert len(bits) == 4
        # Higher singular values should get more bits
        assert bits[0] >= bits[-1]

    def test_dp_allocate_zero_budget(self):
        bits = _dp_allocate_layer([10.0, 5.0], total_bits=0)
        assert sum(bits) == 0

    def test_dp_allocate_empty(self):
        bits = _dp_allocate_layer([], total_bits=10)
        assert bits == []

    def test_dp_allocate_max_bits_cap(self):
        bits = _dp_allocate_layer([100.0], total_bits=16, max_bits_per_component=8)
        assert bits[0] <= 8

    def test_target_bits_mapping(self):
        assert TARGET_BITS["8x"] == 2.0
        assert TARGET_BITS["16x"] == 1.0
        assert TARGET_BITS["32x"] == 0.5

    def test_allocate_bits_empty_pca(self):
        result = allocate_bits(
            pca_result={"projections": {}, "effective_rank": 0, "num_layers": 0},
            compression_target=CompressionTarget.CR_16X,
            num_layers=32,
            head_dim=128,
        )
        assert result["total_key_bits"] == 0
        assert result["total_value_bits"] == 0
