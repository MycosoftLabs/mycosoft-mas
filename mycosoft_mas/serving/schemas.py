"""Pydantic models for serving registry, KVTC artifacts, deployment bundles, and serving evals.

Frozen contract — do not change field semantics without updating ADR-001 and ADR-002.
Date: 2026-03-21
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CacheMode(str, Enum):
    BASELINE = "baseline"
    KVTC_8X = "kvtc8x"
    KVTC_16X = "kvtc16x"
    KVTC_32X = "kvtc32x"
    HYBRID_ATTENTION_ONLY = "hybrid_attention_only"


class TargetStack(str, Enum):
    VLLM = "vllm"
    LMCACHE = "lmcache"
    MEGATRON = "megatron"
    CUSTOM = "custom"


class RolloutState(str, Enum):
    SHADOW = "shadow"
    CANARY = "canary"
    ACTIVE = "active"
    ROLLBACK = "rollback"
    RETIRED = "retired"


class TargetAlias(str, Enum):
    MYCA_CORE = "myca_core"
    MYCA_EDGE = "myca_edge"
    AVANI_CORE = "avani_core"
    FALLBACK_LOCAL = "fallback_local"


class RegressionVerdict(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


class CompressionTarget(str, Enum):
    CR_8X = "8x"
    CR_16X = "16x"
    CR_32X = "32x"
    CR_64X = "64x"


class ArchitectureType(str, Enum):
    DECODER_ONLY_MHA = "decoder_only_mha"
    DECODER_ONLY_GQA = "decoder_only_gqa"
    DECODER_ONLY_MQA = "decoder_only_mqa"
    HYBRID_ATTENTION_MAMBA = "hybrid_attention_mamba"
    HYBRID_ATTENTION_MOE = "hybrid_attention_moe"
    MLA_LATENT = "mla_latent"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Architecture Inventory
# ---------------------------------------------------------------------------


class ModelInventoryResult(BaseModel):
    """Result of scanning a model build for KVTC compatibility."""

    model_build_id: UUID
    architecture_type: ArchitectureType
    num_layers: int
    num_kv_heads: int
    head_dim: int
    rope_type: Optional[str] = None
    mla_latent: bool = False
    has_mamba_layers: bool = False
    has_moe_layers: bool = False
    kv_cache_bytes_per_1k_tokens: int
    kvtc_eligible: bool = False
    kvtc_mode: Optional[str] = None
    notes: str = ""


# ---------------------------------------------------------------------------
# Serving Profile
# ---------------------------------------------------------------------------


class ServingProfileCreate(BaseModel):
    """Request to create a serving profile."""

    model_build_id: UUID
    profile_name: str
    cache_mode: CacheMode = CacheMode.BASELINE
    hot_window_tokens: int = 128
    sink_tokens: int = 4
    rope_handling: Optional[str] = None
    attention_only: bool = False
    mla_latent_mode: bool = False
    offload_policy: dict = Field(default_factory=dict)
    transport_policy: dict = Field(default_factory=dict)
    target_stack: TargetStack = TargetStack.VLLM
    artifact_ref: Optional[UUID] = None
    edge_eligible: bool = False


class ServingProfile(ServingProfileCreate):
    """Persisted serving profile."""

    serving_profile_id: UUID = Field(default_factory=uuid4)
    status: str = "draft"
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# KVTC Artifact
# ---------------------------------------------------------------------------


class KvtcArtifactCreate(BaseModel):
    """Request to register a KVTC calibration artifact."""

    model_build_id: UUID
    compression_target: CompressionTarget
    vk_uri: str
    vv_uri: str
    muk_uri: str
    muv_uri: str
    key_bitplan: list[int]
    value_bitplan: list[int]
    pca_rank: Optional[int] = None
    calibration_tokens: Optional[int] = None
    rope_undo_required: bool = False
    attention_only: bool = False
    mla_latent_mode: bool = False
    calibration_dataset_hash: str
    artifact_hash: str


class KvtcArtifact(KvtcArtifactCreate):
    """Persisted KVTC artifact."""

    kvtc_artifact_id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Deployment Bundle
# ---------------------------------------------------------------------------


class DeploymentBundleCreate(BaseModel):
    """Request to create a deployment bundle."""

    model_build_id: UUID
    adapter_set_id: Optional[UUID] = None
    serving_profile_id: UUID
    cache_policy: dict = Field(default_factory=dict)
    target_alias: TargetAlias
    target_runtime: str
    rollback_bundle_id: Optional[UUID] = None


class DeploymentBundle(DeploymentBundleCreate):
    """Persisted deployment bundle — the actual promoted serving unit."""

    deployment_bundle_id: UUID = Field(default_factory=uuid4)
    rollout_state: RolloutState = RolloutState.SHADOW
    promoted_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Serving Eval Run
# ---------------------------------------------------------------------------


class ServingEvalRunCreate(BaseModel):
    """Request to record a serving eval run."""

    deployment_bundle_id: UUID
    eval_suite: str
    ttft_ms_p50: Optional[float] = None
    ttft_ms_p95: Optional[float] = None
    cache_hit_rate: Optional[float] = None
    recomputation_rate: Optional[float] = None
    hbm_bytes_saved: Optional[int] = None
    warm_bytes_saved: Optional[int] = None
    transfer_bytes_saved: Optional[int] = None
    compression_ratio_actual: Optional[float] = None
    task_success_delta: Optional[float] = None
    tool_validity_delta: Optional[float] = None
    hallucination_delta: Optional[float] = None
    long_context_score: Optional[float] = None
    regression_verdict: Optional[RegressionVerdict] = None
    raw_results: Optional[dict] = None


class ServingEvalRun(ServingEvalRunCreate):
    """Persisted serving eval run."""

    serving_eval_run_id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Calibration Request / Response
# ---------------------------------------------------------------------------


class CalibrationRequest(BaseModel):
    """Request to run KVTC calibration for a model build."""

    model_build_id: UUID
    compression_target: CompressionTarget
    dataset_profile: str = "mixed_fineweb_openr1"
    attention_only: bool = False
    calibration_tokens: int = 160_000
    pca_rank_cap: int = 10_000


class CalibrationResponse(BaseModel):
    """Response from a KVTC calibration job."""

    kvtc_artifact_id: UUID
    model_build_id: UUID
    compression_target: CompressionTarget
    vk_uri: str
    vv_uri: str
    artifact_hash: str
    calibration_summary: dict


# ---------------------------------------------------------------------------
# Bundle Promotion
# ---------------------------------------------------------------------------

# Valid promotion transitions
VALID_TRANSITIONS: dict[RolloutState, list[RolloutState]] = {
    RolloutState.SHADOW: [RolloutState.CANARY, RolloutState.RETIRED],
    RolloutState.CANARY: [RolloutState.ACTIVE, RolloutState.ROLLBACK, RolloutState.RETIRED],
    RolloutState.ACTIVE: [RolloutState.ROLLBACK, RolloutState.RETIRED],
    RolloutState.ROLLBACK: [RolloutState.SHADOW, RolloutState.RETIRED],
    RolloutState.RETIRED: [],
}


class BundlePromotionRequest(BaseModel):
    """Request to promote a deployment bundle to a new rollout state."""

    deployment_bundle_id: UUID
    target_state: RolloutState
    reason: str = ""


class BundlePromotionResponse(BaseModel):
    """Response from a bundle promotion."""

    deployment_bundle_id: UUID
    previous_state: RolloutState
    new_state: RolloutState
    rollback_bundle_id: Optional[UUID] = None
    alias_updated: bool = False
