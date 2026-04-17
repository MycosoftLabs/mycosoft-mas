"""Meta-harness optimisation hooks — latency/token benchmarks (turbo-quant vs plain)."""

from __future__ import annotations

import statistics
import time
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

T = TypeVar("T")


async def benchmark_async(
    label: str,
    fn: Callable[[], Coroutine[Any, Any, T]],
    iterations: int = 5,
) -> dict[str, Any]:
    latencies: list[float] = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        await fn()
        latencies.append((time.perf_counter() - t0) * 1000)
    return {
        "label": label,
        "iterations": iterations,
        "p50_ms": statistics.median(latencies),
        "max_ms": max(latencies),
    }


def compare_token_estimate(baseline_chars: int, compressed_chars: int) -> dict[str, float]:
    """Rough payload comparison for telemetry (not tokenizer-accurate)."""
    return {
        "baseline_chars": float(baseline_chars),
        "compressed_chars": float(compressed_chars),
        "ratio": compressed_chars / max(baseline_chars, 1),
    }
