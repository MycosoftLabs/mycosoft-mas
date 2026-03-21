"""
Plasticity Forge Phase 1 — compression lane for myca_edge and avani_edge.

Teacher-student distillation, quantization, pruning, and Jetson benchmarking.
Produces edge candidates and acceptance gates (latency, memory, accuracy delta).
Real compression runs are delegated to training/export pipelines; this module
defines the lane contract, recipes, and benchmark harness interface.

Created: March 14, 2026
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class CompressionRecipeType(str, Enum):
    """Supported compression recipe types."""

    DISTILLATION = "distillation"
    QUANTIZATION = "quantization"
    PRUNING = "pruning"
    DISTILLATION_QUANTIZATION = "distillation_quantization"


@dataclass
class CompressionRecipe:
    """A single compression recipe (e.g. 8-bit quantization, 2x pruning)."""

    recipe_id: str
    recipe_type: str  # CompressionRecipeType value
    target_alias: str  # myca_edge or avani_edge
    params: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class EdgeAcceptanceGate:
    """Acceptance criteria for edge deployment (Jetson benchmark)."""

    max_latency_p99_ms: float = 500.0
    max_memory_mb: float = 2048.0
    max_accuracy_delta_pct: float = 5.0
    min_retention_ratio: float = 0.85
    jetson_benchmark_required: bool = True


def make_distillation_recipe(
    teacher_candidate_id: str,
    temperature: float = 2.0,
    alpha: float = 0.5,
    target_alias: str = "myca_edge",
) -> CompressionRecipe:
    """Build a distillation recipe for teacher -> student."""
    params = {
        "teacher_candidate_id": teacher_candidate_id,
        "temperature": temperature,
        "alpha": alpha,
    }
    return CompressionRecipe(
        recipe_id=f"distill_{teacher_candidate_id}_{target_alias}",
        recipe_type=CompressionRecipeType.DISTILLATION.value,
        target_alias=target_alias,
        params=params,
    )


def make_quantization_recipe(
    bits: int = 8,
    target_alias: str = "myca_edge",
    per_channel: bool = True,
) -> CompressionRecipe:
    """Build a quantization recipe."""
    params = {"bits": bits, "per_channel": per_channel}
    return CompressionRecipe(
        recipe_id=f"quant_{bits}b_{target_alias}",
        recipe_type=CompressionRecipeType.QUANTIZATION.value,
        target_alias=target_alias,
        params=params,
    )


def make_pruning_recipe(
    ratio: float = 0.5,
    target_alias: str = "avani_edge",
    structured: bool = False,
) -> CompressionRecipe:
    """Build a pruning recipe."""
    params = {"ratio": ratio, "structured": structured}
    return CompressionRecipe(
        recipe_id=f"prune_{ratio}_{target_alias}",
        recipe_type=CompressionRecipeType.PRUNING.value,
        target_alias=target_alias,
        params=params,
    )


def default_edge_gate(alias: str) -> EdgeAcceptanceGate:
    """Default acceptance gate for edge alias (Jetson benchmarking)."""
    return EdgeAcceptanceGate(
        max_latency_p99_ms=500.0,
        max_memory_mb=2048.0,
        max_accuracy_delta_pct=5.0,
        min_retention_ratio=0.85,
        jetson_benchmark_required=True,
    )


def check_edge_acceptance(
    candidate_metrics: Dict[str, Any],
    gate: Optional[EdgeAcceptanceGate] = None,
    alias: str = "myca_edge",
) -> tuple[bool, List[str]]:
    """
    Check candidate against edge acceptance gate.
    Returns (passed, list of failure reasons).
    """
    gate = gate or default_edge_gate(alias)
    failures = []

    latency = candidate_metrics.get("latency_p99_ms")
    if latency is not None and latency > gate.max_latency_p99_ms:
        failures.append(f"latency_p99_ms {latency} > {gate.max_latency_p99_ms}")

    memory = candidate_metrics.get("memory_mb")
    if memory is not None and memory > gate.max_memory_mb:
        failures.append(f"memory_mb {memory} > {gate.max_memory_mb}")

    accuracy_delta = candidate_metrics.get("accuracy_delta_pct")
    if accuracy_delta is not None and accuracy_delta > gate.max_accuracy_delta_pct:
        failures.append(f"accuracy_delta_pct {accuracy_delta} > {gate.max_accuracy_delta_pct}")

    retention = candidate_metrics.get("retention_ratio")
    if retention is not None and retention < gate.min_retention_ratio:
        failures.append(f"retention_ratio {retention} < {gate.min_retention_ratio}")

    if gate.jetson_benchmark_required and not candidate_metrics.get("jetson_benchmark_passed"):
        failures.append("jetson_benchmark_passed required but missing or false")

    return (len(failures) == 0, failures)


def recipe_to_dict(recipe: CompressionRecipe) -> Dict[str, Any]:
    """Serialize for registry or API."""
    return asdict(recipe)


def list_recipe_types() -> List[str]:
    """Return all recipe type values."""
    return [t.value for t in CompressionRecipeType]
