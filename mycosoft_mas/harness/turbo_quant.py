"""
Turbo-quant compression bridge for Nemotron prompt/response payloads.

The production algorithm is proprietary; when ``turbo_quant_nda_mode`` is True,
:class:`TurboQuantCompressor` applies a documented placeholder (zlib) so telemetry
(ratio, latency) can be collected without exposing IP. Replace internals only
under NDA-approved deployment packages.
"""

from __future__ import annotations

import logging
import time
import zlib

logger = logging.getLogger(__name__)


class TurboQuantCompressor:
    """compress / decompress with ratio + timing logs."""

    def __init__(self, nda_mode: bool = True) -> None:
        self._nda_mode = nda_mode

    def compress(self, prompt: str) -> bytes:
        t0 = time.perf_counter()
        raw = prompt.encode("utf-8")
        # Placeholder: zlib; swap for turbo-quant binary protocol under NDA.
        out = zlib.compress(raw, level=6)
        elapsed = time.perf_counter() - t0
        ratio = len(out) / max(len(raw), 1)
        logger.info(
            "turbo_quant compress ratio=%.4f time_ms=%.3f nda=%s",
            ratio,
            elapsed * 1000,
            self._nda_mode,
        )
        return out

    def decompress(self, data: bytes) -> str:
        t0 = time.perf_counter()
        raw = zlib.decompress(data)
        elapsed = time.perf_counter() - t0
        logger.info("turbo_quant decompress bytes=%s time_ms=%.3f", len(data), elapsed * 1000)
        return raw.decode("utf-8")
