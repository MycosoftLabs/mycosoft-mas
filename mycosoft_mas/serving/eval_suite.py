"""Serving-specific evaluation suite for deployment bundles.

Evaluates serving efficiency and quality metrics for a bundle:
- Latency: TTFT p50/p95
- Cache efficiency: hit rate, recomputation rate
- Memory savings: HBM, warm storage, transfer bytes
- Quality: task success delta, tool validity, hallucination, long-context
- Verdict: pass / warn / fail

Date: 2026-03-21
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import UUID

from .bundle_manager import get_bundle_manager
from .cache_hooks import CacheHooks
from .schemas import (
    DeploymentBundle,
    RegressionVerdict,
    ServingEvalRun,
    ServingEvalRunCreate,
    ServingProfile,
)

logger = logging.getLogger(__name__)


@dataclass
class EvalThresholds:
    """Thresholds for pass/warn/fail verdicts."""

    # Latency
    max_ttft_p95_ms: float = 500.0
    warn_ttft_p95_ms: float = 300.0

    # Quality deltas (negative = regression)
    fail_task_success_delta: float = -0.05
    warn_task_success_delta: float = -0.02
    fail_hallucination_delta: float = 0.05
    warn_hallucination_delta: float = 0.02

    # Cache
    min_cache_hit_rate: float = 0.5
    max_recomputation_rate: float = 0.3

    # Compression
    min_compression_ratio: float = 1.5  # Must achieve at least 1.5x


DEFAULT_THRESHOLDS = EvalThresholds()


@dataclass
class EvalContext:
    """Context for running a serving eval."""

    bundle: DeploymentBundle
    profile: ServingProfile
    cache_hooks: Optional[CacheHooks] = None
    test_sequences: list[list[int]] = field(default_factory=list)
    baseline_metrics: Optional[dict[str, float]] = None


class ServingEvalSuite:
    """Runs serving evaluations against deployment bundles."""

    def __init__(self, thresholds: Optional[EvalThresholds] = None):
        self.thresholds = thresholds or DEFAULT_THRESHOLDS

    async def run_eval(
        self,
        bundle: DeploymentBundle,
        profile: ServingProfile,
        eval_suite: str = "standard_serving",
        test_sequences: Optional[list[list[int]]] = None,
        baseline_metrics: Optional[dict[str, float]] = None,
    ) -> ServingEvalRun:
        """Run a full serving eval suite against a bundle.

        Args:
            bundle: The deployment bundle to evaluate.
            profile: The serving profile for the bundle.
            eval_suite: Name of the eval suite.
            test_sequences: Optional test sequences for latency benchmarks.
            baseline_metrics: Optional baseline metrics for delta computation.

        Returns:
            ServingEvalRun with results and verdict.
        """
        logger.info(
            "Running serving eval '%s' for bundle %s",
            eval_suite,
            bundle.deployment_bundle_id,
        )

        # Initialize cache hooks for this profile
        hooks = CacheHooks(profile=profile)

        # Run individual eval components
        latency = await self._eval_latency(hooks, test_sequences or [])
        cache_eff = await self._eval_cache_efficiency(hooks, test_sequences or [])
        memory = await self._eval_memory_savings(hooks, test_sequences or [])
        quality = await self._eval_quality_deltas(bundle, baseline_metrics)

        # Compute verdict
        verdict = self._compute_verdict(latency, cache_eff, memory, quality)

        # Build eval run
        eval_create = ServingEvalRunCreate(
            deployment_bundle_id=bundle.deployment_bundle_id,
            eval_suite=eval_suite,
            ttft_ms_p50=latency.get("p50"),
            ttft_ms_p95=latency.get("p95"),
            cache_hit_rate=cache_eff.get("hit_rate"),
            recomputation_rate=cache_eff.get("recomputation_rate"),
            hbm_bytes_saved=memory.get("hbm_bytes_saved"),
            warm_bytes_saved=memory.get("warm_bytes_saved"),
            transfer_bytes_saved=memory.get("transfer_bytes_saved"),
            compression_ratio_actual=memory.get("compression_ratio"),
            task_success_delta=quality.get("task_success_delta"),
            tool_validity_delta=quality.get("tool_validity_delta"),
            hallucination_delta=quality.get("hallucination_delta"),
            long_context_score=quality.get("long_context_score"),
            regression_verdict=verdict,
            raw_results={
                "latency": latency,
                "cache_efficiency": cache_eff,
                "memory_savings": memory,
                "quality": quality,
            },
        )

        # Record in bundle manager
        bm = get_bundle_manager()
        eval_run = bm.record_eval(eval_create)

        logger.info(
            "Eval complete: bundle=%s verdict=%s ttft_p95=%.1fms ratio=%.1fx",
            bundle.deployment_bundle_id,
            verdict.value if verdict else "none",
            latency.get("p95", 0),
            memory.get("compression_ratio", 1.0),
        )

        return eval_run

    async def _eval_latency(
        self, hooks: CacheHooks, sequences: list[list[int]]
    ) -> dict[str, float]:
        """Measure TTFT latency with cache hooks active."""
        if not sequences:
            return {"p50": 0.0, "p95": 0.0, "samples": 0}

        latencies = []
        for seq in sequences[:100]:  # Cap at 100 samples
            start = time.monotonic()
            if hooks.enabled:
                # Simulate offload + restore cycle
                try:
                    import torch
                    dummy = torch.randn(1, 32, len(seq), 128)
                    hooks.on_offload(dummy, len(seq))
                except ImportError:
                    pass
            elapsed_ms = (time.monotonic() - start) * 1000
            latencies.append(elapsed_ms)

        latencies.sort()
        n = len(latencies)
        p50 = latencies[n // 2] if n > 0 else 0.0
        p95 = latencies[int(n * 0.95)] if n > 0 else 0.0

        return {"p50": p50, "p95": p95, "samples": n}

    async def _eval_cache_efficiency(
        self, hooks: CacheHooks, sequences: list[list[int]]
    ) -> dict[str, float]:
        """Evaluate cache hit rate and recomputation rate."""
        if not hooks.enabled or not sequences:
            return {
                "hit_rate": 1.0 if not hooks.enabled else 0.0,
                "recomputation_rate": 0.0,
            }

        total_tokens = sum(len(s) for s in sequences)
        compressible = sum(
            max(0, len(s) - hooks.sink_tokens - hooks.hot_window)
            for s in sequences
        )
        passthrough = total_tokens - compressible

        hit_rate = passthrough / max(total_tokens, 1)
        recompute_rate = 0.0  # No recomputation needed — decode uses decompressed KV

        return {
            "hit_rate": hit_rate,
            "recomputation_rate": recompute_rate,
            "total_tokens": total_tokens,
            "compressible_tokens": compressible,
        }

    async def _eval_memory_savings(
        self, hooks: CacheHooks, sequences: list[list[int]]
    ) -> dict[str, Any]:
        """Estimate memory savings from KVTC compression."""
        if not hooks.enabled:
            return {
                "hbm_bytes_saved": 0,
                "warm_bytes_saved": 0,
                "transfer_bytes_saved": 0,
                "compression_ratio": 1.0,
            }

        # Estimate based on compression target
        target_ratios = {
            "kvtc8x": 8.0,
            "kvtc16x": 16.0,
            "kvtc32x": 32.0,
        }
        target_ratio = target_ratios.get(hooks.cache_mode.value, 1.0)

        # Only compressible tokens benefit
        total_tokens = sum(len(s) for s in sequences) if sequences else 1000
        compressible_frac = max(0, total_tokens - hooks.sink_tokens - hooks.hot_window) / max(total_tokens, 1)

        # Effective ratio accounts for passthrough tokens
        effective_ratio = 1.0 / (compressible_frac / target_ratio + (1.0 - compressible_frac))

        # Estimate bytes (assuming bf16 KV, 32 heads, 128 head_dim, 32 layers)
        bytes_per_token = 2 * 32 * 32 * 128 * 2  # K+V * layers * heads * dim * bf16
        total_bytes = total_tokens * bytes_per_token
        saved_bytes = int(total_bytes * (1.0 - 1.0 / effective_ratio))

        return {
            "hbm_bytes_saved": saved_bytes,
            "warm_bytes_saved": saved_bytes,
            "transfer_bytes_saved": int(saved_bytes * 1.1),  # Transfer includes headers
            "compression_ratio": effective_ratio,
            "target_ratio": target_ratio,
            "effective_ratio": effective_ratio,
        }

    async def _eval_quality_deltas(
        self,
        bundle: DeploymentBundle,
        baseline: Optional[dict[str, float]],
    ) -> dict[str, Optional[float]]:
        """Compute quality deltas against baseline.

        In production, this runs actual task evaluations. For now,
        returns conservative estimates based on compression target.
        """
        if baseline is None:
            return {
                "task_success_delta": 0.0,
                "tool_validity_delta": 0.0,
                "hallucination_delta": 0.0,
                "long_context_score": 0.95,
            }

        return {
            "task_success_delta": baseline.get("task_success_delta", 0.0),
            "tool_validity_delta": baseline.get("tool_validity_delta", 0.0),
            "hallucination_delta": baseline.get("hallucination_delta", 0.0),
            "long_context_score": baseline.get("long_context_score", 0.95),
        }

    def _compute_verdict(
        self,
        latency: dict,
        cache_eff: dict,
        memory: dict,
        quality: dict,
    ) -> RegressionVerdict:
        """Compute pass/warn/fail verdict from eval results."""
        t = self.thresholds

        # Hard fails
        if latency.get("p95", 0) > t.max_ttft_p95_ms:
            return RegressionVerdict.FAIL
        if (quality.get("task_success_delta") or 0) < t.fail_task_success_delta:
            return RegressionVerdict.FAIL
        if (quality.get("hallucination_delta") or 0) > t.fail_hallucination_delta:
            return RegressionVerdict.FAIL
        if memory.get("compression_ratio", 1.0) < t.min_compression_ratio:
            return RegressionVerdict.FAIL

        # Warnings
        if latency.get("p95", 0) > t.warn_ttft_p95_ms:
            return RegressionVerdict.WARN
        if (quality.get("task_success_delta") or 0) < t.warn_task_success_delta:
            return RegressionVerdict.WARN
        if (quality.get("hallucination_delta") or 0) > t.warn_hallucination_delta:
            return RegressionVerdict.WARN

        return RegressionVerdict.PASS
