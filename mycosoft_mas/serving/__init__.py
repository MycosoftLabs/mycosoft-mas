"""
Serving module — KVTC serving lane, deployment bundles, and promotion.

Part of Plasticity Forge Phase 1.

Components:
- schemas: Pydantic models for serving profiles, KVTC artifacts, bundles, evals
- profile_manager: CRUD for serving profiles
- bundle_manager: Deployment bundle lifecycle
- cache_hooks: Runtime KV-cache compression hooks
- eval_suite: Serving-specific evaluations
- promotion: Bundle promotion engine (shadow → canary → active → rollback)
"""

from .config import get_alias_defaults, get_calibration_defaults, get_promotion_thresholds, load_kvtc_config
from .schemas import (
    CacheMode,
    CalibrationRequest,
    CalibrationResponse,
    CompressionTarget,
    DeploymentBundle,
    DeploymentBundleCreate,
    KvtcArtifact,
    KvtcArtifactCreate,
    ModelInventoryResult,
    RegressionVerdict,
    RolloutState,
    ServingEvalRun,
    ServingEvalRunCreate,
    ServingProfile,
    ServingProfileCreate,
    TargetAlias,
    TargetStack,
)

__all__ = [
    "load_kvtc_config",
    "get_alias_defaults",
    "get_calibration_defaults",
    "get_promotion_thresholds",
    "CacheMode",
    "CalibrationRequest",
    "CalibrationResponse",
    "CompressionTarget",
    "DeploymentBundle",
    "DeploymentBundleCreate",
    "KvtcArtifact",
    "KvtcArtifactCreate",
    "ModelInventoryResult",
    "RegressionVerdict",
    "RolloutState",
    "ServingEvalRun",
    "ServingEvalRunCreate",
    "ServingProfile",
    "ServingProfileCreate",
    "TargetAlias",
    "TargetStack",
]
