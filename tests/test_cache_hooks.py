"""Tests for cache manager hooks.

Date: 2026-03-21
"""

import pytest
from uuid import uuid4

from mycosoft_mas.serving.cache_hooks import CacheHooks, _estimate_bytes
from mycosoft_mas.serving.schemas import (
    CacheMode,
    ServingProfile,
    TargetStack,
)


def _make_profile(cache_mode=CacheMode.BASELINE, **kwargs):
    return ServingProfile(
        model_build_id=uuid4(),
        profile_name="test",
        cache_mode=cache_mode,
        target_stack=TargetStack.VLLM,
        **kwargs,
    )


class TestCacheHooksPassthrough:
    def test_baseline_is_passthrough(self):
        hooks = CacheHooks(profile=_make_profile())
        assert not hooks.enabled

    def test_no_artifact_is_passthrough(self):
        hooks = CacheHooks(
            profile=_make_profile(cache_mode=CacheMode.KVTC_16X),
            artifact_data=None,
        )
        assert not hooks.enabled

    def test_passthrough_offload(self):
        hooks = CacheHooks(profile=_make_profile())
        result = hooks.on_offload(b"test_data", seq_len=100)
        assert result.compression_ratio == 1.0
        assert result.tokens_compressed == 0


class TestCacheHooksEnabled:
    def test_enabled_with_artifact(self):
        hooks = CacheHooks(
            profile=_make_profile(cache_mode=CacheMode.KVTC_16X),
            artifact_data={"projections": {}, "bitplans": {}},
        )
        assert hooks.enabled

    def test_hot_window_defaults(self):
        hooks = CacheHooks(profile=_make_profile())
        assert hooks.hot_window == 128
        assert hooks.sink_tokens == 4

    def test_offload_with_artifact(self):
        hooks = CacheHooks(
            profile=_make_profile(cache_mode=CacheMode.KVTC_16X),
            artifact_data={"projections": {}, "bitplans": {}},
        )
        result = hooks.on_offload(b"test", seq_len=256)
        assert result.tokens_passthrough > 0
        # 256 - 4 (sink) - 128 (window) = 124 compressible
        assert result.tokens_compressed == 124

    def test_transport_same_as_offload(self):
        hooks = CacheHooks(
            profile=_make_profile(cache_mode=CacheMode.KVTC_8X),
            artifact_data={"projections": {}, "bitplans": {}},
        )
        offload = hooks.on_offload(b"test", seq_len=200)
        transport = hooks.on_transport(b"test", seq_len=200)
        assert offload.tokens_compressed == transport.tokens_compressed

    def test_restore_passthrough(self):
        hooks = CacheHooks(profile=_make_profile())
        offload = hooks.on_offload(b"test", seq_len=100)
        restore = hooks.on_restore(offload)
        assert restore.layers_decompressed == 0


class TestEstimateBytes:
    def test_estimate_bytes_bytes(self):
        assert _estimate_bytes(b"hello") == 5

    def test_estimate_bytes_none(self):
        assert _estimate_bytes(None) == 0

    def test_estimate_bytes_torch(self):
        try:
            import torch
            t = torch.randn(10, 128)
            assert _estimate_bytes(t) == 10 * 128 * 4  # float32
        except ImportError:
            pytest.skip("torch not available")
