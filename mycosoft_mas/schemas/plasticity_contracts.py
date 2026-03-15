"""
Plasticity Forge Phase 1 — frozen contracts for model evolution.

CandidateGenome, FitnessProfile, and PromotionPolicy define the canonical
interfaces for the plasticity control plane. Do not change field semantics
without updating PLASTICITY_FORGE_CONTRACTS_FROZEN_MAR14_2026.md and registry.

Created: March 14, 2026
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class CandidateLifecycle(Enum):
    """Lifecycle state of a model candidate."""
    SHADOW = "shadow"       # Serving shadow traffic only
    CANARY = "canary"       # Serving canary fraction
    ACTIVE = "active"       # Promoted; primary alias
    ROLLBACK = "rollback"   # Reverted; kept for lineage
    ARCHIVED = "archived"   # No longer serving


class MutationOperator(Enum):
    """Phase 1–allowed mutation operators (narrow set)."""
    ROUTING_POLICY = "routing_policy"
    RETRIEVAL_POLICY = "retrieval_policy"
    PROMPT_PROGRAM_POLICY = "prompt_program_policy"
    LORA_ADAPTER = "lora_adapter"
    REWARD_TWEAK = "reward_tweak"
    DISTILLATION = "distillation"
    PRUNING = "pruning"
    QUANTIZATION = "quantization"


@dataclass(frozen=False)  # Mutable for builder; treat as immutable after creation
class CandidateGenome:
    """
    First-class record for a model evolution candidate.
    Every branch in the forge has a genome; lineage and rollback are derived from this.
    """
    candidate_id: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Lineage
    parent_candidate_ids: List[str] = field(default_factory=list)
    base_model_id: Optional[str] = None
    artifact_uri: Optional[str] = None

    # Mutation
    mutation_operators_applied: List[str] = field(default_factory=list)  # MutationOperator names
    data_curriculum_hash: Optional[str] = None
    training_code_hash: Optional[str] = None

    # Eval and safety
    eval_suite_ids: List[str] = field(default_factory=list)
    eval_summary: Optional[Dict[str, Any]] = None
    safety_verdict: Optional[str] = None  # e.g. "pass", "fail", "pending"

    # Hardware envelope
    latency_p50_ms: Optional[float] = None
    latency_p99_ms: Optional[float] = None
    memory_mb: Optional[float] = None
    watts: Optional[float] = None
    jetson_compatible: bool = False

    # Lifecycle and rollback
    lifecycle: str = CandidateLifecycle.SHADOW.value
    rollback_target_candidate_id: Optional[str] = None
    promoted_at: Optional[str] = None
    alias: Optional[str] = None  # e.g. "myca_core", "myca_edge", "avani_edge"


@dataclass
class FitnessProfile:
    """
    Hard gates and soft (Pareto) objectives for candidate selection.
    A candidate is rejected if any hard gate fails; otherwise selection
    optimizes over the soft objectives.
    """
    candidate_id: str
    evaluated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Hard gates (all must pass)
    safety_ok: bool = False
    provenance_complete: bool = False
    reproducible: bool = False
    regression_within_cap: bool = False
    hardware_envelope_ok: bool = False
    retention_above_threshold: bool = False

    # Soft objectives (Pareto frontier)
    task_success: float = 0.0
    groundedness: float = 0.0
    calibration: float = 0.0
    latency_score: float = 0.0
    memory_score: float = 0.0
    watts_score: float = 0.0
    retention_score: float = 0.0
    compression_ratio: float = 0.0
    edge_fitness: float = 0.0

    # Joint MYCA + AVANI (optional)
    myca_only_score: Optional[float] = None
    avani_only_score: Optional[float] = None
    joint_score: Optional[float] = None


@dataclass
class PromotionPolicy:
    """
    Policy governing promotion from shadow/canary to active.
    Used by the promotion controller; stored with promotion_decision in registry.
    """
    policy_id: str
    name: str
    description: Optional[str] = None

    # Gates that must hold for promotion
    require_safety_verdict: bool = True
    require_min_canary_duration_seconds: Optional[int] = None
    require_min_eval_coverage: Optional[float] = None  # 0.0–1.0
    require_retention_above: Optional[float] = None
    require_regression_within_cap: bool = True

    # Approval
    require_approval_tier: Optional[str] = None  # e.g. "human", "automated"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
