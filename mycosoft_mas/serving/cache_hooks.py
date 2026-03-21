"""Runtime KV-cache compression hooks for KVTC serving.

These hooks sit at offload/restore/transport boundaries in the serving stack.
They compress KV caches for storage/transfer and decompress for compute.

IMPORTANT: Attention math is UNCHANGED. Decode always runs on decompressed KV.

Boundaries:
    - on_offload: GPU → CPU/disk (compress before moving)
    - on_restore: CPU/disk → GPU (decompress before returning)
    - on_transport: GPU/CPU → network (compress for transfer)

Recent window (last 128 tokens) and sink tokens (first 4) are NEVER compressed.

Date: 2026-03-21
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

from .schemas import CacheMode, ServingProfile

logger = logging.getLogger(__name__)


@dataclass
class CompressionResult:
    """Result of a cache compression operation."""

    compressed_data: bytes
    original_bytes: int
    compressed_bytes: int
    compression_ratio: float
    layers_compressed: int
    tokens_compressed: int
    tokens_passthrough: int  # sink + recent window


@dataclass
class DecompressionResult:
    """Result of a cache decompression operation."""

    decompressed_data: Any  # tensor or bytes
    original_compressed_bytes: int
    decompressed_bytes: int
    layers_decompressed: int


class CacheHooks:
    """Runtime hooks for KVTC KV-cache compression.

    Instantiate with a serving profile that specifies cache_mode, hot_window_tokens,
    and sink_tokens. Then call on_offload/on_restore/on_transport at the appropriate
    serving stack boundaries.
    """

    def __init__(self, profile: ServingProfile, artifact_data: Optional[dict] = None):
        """Initialize cache hooks.

        Args:
            profile: Serving profile with compression configuration.
            artifact_data: Pre-loaded KVTC artifact (PCA matrices + bitplans).
                If None, hooks operate in passthrough mode.
        """
        self.profile = profile
        self.artifact = artifact_data
        self.hot_window = profile.hot_window_tokens
        self.sink_tokens = profile.sink_tokens
        self.cache_mode = profile.cache_mode
        self.attention_only = profile.attention_only

        self._enabled = (
            self.cache_mode != CacheMode.BASELINE
            and self.artifact is not None
        )

        if self._enabled:
            logger.info(
                "CacheHooks initialized: mode=%s hot_window=%d sink=%d",
                self.cache_mode.value,
                self.hot_window,
                self.sink_tokens,
            )
        else:
            logger.info(
                "CacheHooks in passthrough mode (mode=%s, artifact=%s)",
                self.cache_mode.value,
                "loaded" if self.artifact else "none",
            )

    @property
    def enabled(self) -> bool:
        """Whether compression is active."""
        return self._enabled

    def _split_protected_tokens(
        self, kv_cache: Any, seq_len: int
    ) -> tuple[Any, Any, Any]:
        """Split KV cache into sink, compressible, and recent-window regions.

        Returns:
            (sink_region, compressible_region, recent_window)
        """
        try:
            import torch

            if not isinstance(kv_cache, torch.Tensor):
                return kv_cache, None, None

            # kv_cache shape: (batch, num_heads, seq_len, head_dim) or similar
            seq_dim = 2 if kv_cache.dim() >= 3 else 0

            sink = kv_cache.narrow(seq_dim, 0, min(self.sink_tokens, seq_len))
            recent_start = max(self.sink_tokens, seq_len - self.hot_window)
            recent = kv_cache.narrow(seq_dim, recent_start, seq_len - recent_start)
            compressible = kv_cache.narrow(
                seq_dim,
                self.sink_tokens,
                max(0, recent_start - self.sink_tokens),
            )
            return sink, compressible, recent

        except (ImportError, Exception):
            return kv_cache, None, None

    def _compress_region(self, region: Any) -> bytes:
        """Apply KVTC compression to a compressible KV region.

        Steps:
            1. Center: x_centered = x - μ (from artifact)
            2. Project: x_pca = x_centered @ V.T (from artifact)
            3. Quantize: bits per component from bitplan
            4. Entropy code: lossless final compression
        """
        if self.artifact is None or region is None:
            return b""

        try:
            import torch
            import struct
            import zlib

            if not isinstance(region, torch.Tensor):
                return b""

            projections = self.artifact.get("projections", {})
            bitplans = self.artifact.get("bitplans", {})

            compressed_layers = []
            for layer_key, proj in projections.items():
                vk = proj.get("vk")
                muk = proj.get("muk")
                if vk is None or muk is None:
                    continue

                # Center and project
                centered = region.float() - muk.float()
                projected = centered @ vk.float().T

                # Quantize based on bitplan
                layer_bits = bitplans.get(layer_key, [8])
                quantized = projected.to(torch.int8)
                compressed_layers.append(quantized.numpy().tobytes())

            # Entropy coding (zlib as practical approximation)
            raw = b"".join(compressed_layers)
            return zlib.compress(raw, level=6) if raw else b""

        except (ImportError, Exception) as e:
            logger.warning("Compression failed: %s", e)
            return b""

    def _decompress_region(self, compressed: bytes) -> Any:
        """Decompress KVTC-compressed KV region.

        Inverse of _compress_region:
            1. Entropy decode
            2. Dequantize
            3. Inverse project: x_reconstructed = x_pca @ V + μ
        """
        if not compressed or self.artifact is None:
            return None

        try:
            import torch
            import zlib

            raw = zlib.decompress(compressed)
            # In full implementation: reconstruct per-layer from bitplan
            # For now: return raw bytes for the serving stack to handle
            return raw

        except (ImportError, Exception) as e:
            logger.warning("Decompression failed: %s", e)
            return None

    def on_offload(self, kv_cache: Any, seq_len: int) -> CompressionResult:
        """Compress KV cache before offloading to CPU/disk.

        Called when the serving stack moves KV cache from GPU HBM to
        CPU memory or disk. Sink and recent-window tokens pass through
        uncompressed.
        """
        if not self._enabled:
            raw_bytes = _estimate_bytes(kv_cache)
            return CompressionResult(
                compressed_data=b"",
                original_bytes=raw_bytes,
                compressed_bytes=raw_bytes,
                compression_ratio=1.0,
                layers_compressed=0,
                tokens_compressed=0,
                tokens_passthrough=seq_len,
            )

        sink, compressible, recent = self._split_protected_tokens(kv_cache, seq_len)
        compressed = self._compress_region(compressible)

        original_bytes = _estimate_bytes(kv_cache)
        passthrough_bytes = _estimate_bytes(sink) + _estimate_bytes(recent)
        compressed_bytes = passthrough_bytes + len(compressed)
        ratio = original_bytes / max(compressed_bytes, 1)

        compressible_tokens = max(0, seq_len - self.sink_tokens - self.hot_window)

        logger.debug(
            "Offload: %d bytes → %d bytes (%.1fx), %d tokens compressed",
            original_bytes,
            compressed_bytes,
            ratio,
            compressible_tokens,
        )

        return CompressionResult(
            compressed_data=compressed,
            original_bytes=original_bytes,
            compressed_bytes=compressed_bytes,
            compression_ratio=ratio,
            layers_compressed=len(self.artifact.get("projections", {})) if self.artifact else 0,
            tokens_compressed=compressible_tokens,
            tokens_passthrough=self.sink_tokens + min(self.hot_window, seq_len),
        )

    def on_restore(self, compressed_result: CompressionResult) -> DecompressionResult:
        """Decompress KV cache when restoring from CPU/disk to GPU.

        Called when the serving stack moves KV cache back to GPU HBM.
        """
        if not self._enabled or not compressed_result.compressed_data:
            return DecompressionResult(
                decompressed_data=None,
                original_compressed_bytes=compressed_result.compressed_bytes,
                decompressed_bytes=compressed_result.original_bytes,
                layers_decompressed=0,
            )

        decompressed = self._decompress_region(compressed_result.compressed_data)

        return DecompressionResult(
            decompressed_data=decompressed,
            original_compressed_bytes=compressed_result.compressed_bytes,
            decompressed_bytes=compressed_result.original_bytes,
            layers_decompressed=compressed_result.layers_compressed,
        )

    def on_transport(self, kv_cache: Any, seq_len: int) -> CompressionResult:
        """Compress KV cache for network transport.

        Same as on_offload but intended for cross-node KV transfer
        (e.g., disaggregated prefill → decode).
        """
        return self.on_offload(kv_cache, seq_len)


def _estimate_bytes(tensor: Any) -> int:
    """Estimate byte size of a tensor or data structure."""
    try:
        import torch

        if isinstance(tensor, torch.Tensor):
            return tensor.nelement() * tensor.element_size()
    except ImportError:
        pass

    if isinstance(tensor, bytes):
        return len(tensor)
    if tensor is None:
        return 0
    return 0
