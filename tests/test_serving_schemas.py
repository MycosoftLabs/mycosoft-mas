"""Tests for serving module schemas.

Date: 2026-03-21
"""

import pytest
from uuid import uuid4

from mycosoft_mas.serving.schemas import (
    ArchitectureType,
    BundlePromotionRequest,
    BundlePromotionResponse,
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
    VALID_TRANSITIONS,
)


class TestEnums:
    def test_cache_mode_values(self):
        assert CacheMode.BASELINE == "baseline"
        assert CacheMode.KVTC_16X == "kvtc16x"
        assert len(CacheMode) == 5

    def test_rollout_state_values(self):
        assert RolloutState.SHADOW == "shadow"
        assert RolloutState.ACTIVE == "active"
        assert len(RolloutState) == 5

    def test_compression_target_values(self):
        assert CompressionTarget.CR_8X == "8x"
        assert CompressionTarget.CR_64X == "64x"

    def test_architecture_types(self):
        assert ArchitectureType.DECODER_ONLY_GQA == "decoder_only_gqa"
        assert ArchitectureType.HYBRID_ATTENTION_MAMBA == "hybrid_attention_mamba"
        assert ArchitectureType.MLA_LATENT == "mla_latent"

    def test_target_alias_values(self):
        assert TargetAlias.MYCA_CORE == "myca_core"
        assert TargetAlias.FALLBACK_LOCAL == "fallback_local"

    def test_regression_verdict(self):
        assert RegressionVerdict.PASS == "pass"
        assert RegressionVerdict.FAIL == "fail"


class TestModelInventoryResult:
    def test_create_inventory(self):
        inv = ModelInventoryResult(
            model_build_id=uuid4(),
            architecture_type=ArchitectureType.DECODER_ONLY_GQA,
            num_layers=32,
            num_kv_heads=8,
            head_dim=128,
            kv_cache_bytes_per_1k_tokens=131072000,
            kvtc_eligible=True,
            kvtc_mode="full_kv",
        )
        assert inv.kvtc_eligible is True
        assert inv.has_mamba_layers is False
        assert inv.mla_latent is False

    def test_hybrid_mamba_inventory(self):
        inv = ModelInventoryResult(
            model_build_id=uuid4(),
            architecture_type=ArchitectureType.HYBRID_ATTENTION_MAMBA,
            num_layers=40,
            num_kv_heads=8,
            head_dim=128,
            kv_cache_bytes_per_1k_tokens=0,
            kvtc_eligible=True,
            kvtc_mode="attention_only",
            has_mamba_layers=True,
        )
        assert inv.has_mamba_layers is True
        assert inv.kvtc_mode == "attention_only"


class TestServingProfile:
    def test_create_profile_defaults(self):
        p = ServingProfileCreate(
            model_build_id=uuid4(),
            profile_name="test-baseline",
        )
        assert p.cache_mode == CacheMode.BASELINE
        assert p.hot_window_tokens == 128
        assert p.sink_tokens == 4
        assert p.target_stack == TargetStack.VLLM

    def test_create_kvtc_profile(self):
        p = ServingProfileCreate(
            model_build_id=uuid4(),
            profile_name="test-kvtc16x",
            cache_mode=CacheMode.KVTC_16X,
            target_stack=TargetStack.LMCACHE,
            attention_only=True,
        )
        assert p.cache_mode == CacheMode.KVTC_16X
        assert p.attention_only is True

    def test_serving_profile_has_id(self):
        p = ServingProfile(
            model_build_id=uuid4(),
            profile_name="test",
        )
        assert p.serving_profile_id is not None
        assert p.status == "draft"


class TestKvtcArtifact:
    def test_create_artifact(self):
        a = KvtcArtifactCreate(
            model_build_id=uuid4(),
            compression_target=CompressionTarget.CR_16X,
            vk_uri="/artifacts/vk.bin",
            vv_uri="/artifacts/vv.bin",
            muk_uri="/artifacts/muk.bin",
            muv_uri="/artifacts/muv.bin",
            key_bitplan=[2, 2, 1, 1],
            value_bitplan=[2, 2, 1, 1],
            calibration_dataset_hash="abc123",
            artifact_hash="def456",
        )
        assert a.compression_target == CompressionTarget.CR_16X
        assert a.attention_only is False


class TestDeploymentBundle:
    def test_create_bundle(self):
        b = DeploymentBundleCreate(
            model_build_id=uuid4(),
            serving_profile_id=uuid4(),
            target_alias=TargetAlias.MYCA_CORE,
            target_runtime="vllm",
        )
        assert b.target_alias == TargetAlias.MYCA_CORE
        assert b.adapter_set_id is None

    def test_bundle_default_state(self):
        b = DeploymentBundle(
            model_build_id=uuid4(),
            serving_profile_id=uuid4(),
            target_alias=TargetAlias.MYCA_CORE,
            target_runtime="vllm",
        )
        assert b.rollout_state == RolloutState.SHADOW
        assert b.promoted_at is None


class TestServingEvalRun:
    def test_create_eval(self):
        e = ServingEvalRunCreate(
            deployment_bundle_id=uuid4(),
            eval_suite="standard_serving",
            ttft_ms_p50=25.0,
            ttft_ms_p95=50.0,
            compression_ratio_actual=15.5,
            regression_verdict=RegressionVerdict.PASS,
        )
        assert e.regression_verdict == RegressionVerdict.PASS


class TestCalibration:
    def test_calibration_request_defaults(self):
        r = CalibrationRequest(
            model_build_id=uuid4(),
            compression_target=CompressionTarget.CR_16X,
        )
        assert r.calibration_tokens == 160_000
        assert r.pca_rank_cap == 10_000
        assert r.dataset_profile == "mixed_fineweb_openr1"

    def test_calibration_response(self):
        r = CalibrationResponse(
            kvtc_artifact_id=uuid4(),
            model_build_id=uuid4(),
            compression_target=CompressionTarget.CR_16X,
            vk_uri="/vk.bin",
            vv_uri="/vv.bin",
            artifact_hash="abc",
            calibration_summary={"layers": 32},
        )
        assert r.compression_target == CompressionTarget.CR_16X


class TestValidTransitions:
    def test_shadow_transitions(self):
        assert RolloutState.CANARY in VALID_TRANSITIONS[RolloutState.SHADOW]
        assert RolloutState.RETIRED in VALID_TRANSITIONS[RolloutState.SHADOW]
        assert RolloutState.ACTIVE not in VALID_TRANSITIONS[RolloutState.SHADOW]

    def test_canary_transitions(self):
        assert RolloutState.ACTIVE in VALID_TRANSITIONS[RolloutState.CANARY]
        assert RolloutState.ROLLBACK in VALID_TRANSITIONS[RolloutState.CANARY]

    def test_active_transitions(self):
        assert RolloutState.ROLLBACK in VALID_TRANSITIONS[RolloutState.ACTIVE]
        assert RolloutState.CANARY not in VALID_TRANSITIONS[RolloutState.ACTIVE]

    def test_retired_is_terminal(self):
        assert VALID_TRANSITIONS[RolloutState.RETIRED] == []


class TestBundlePromotion:
    def test_promotion_request(self):
        r = BundlePromotionRequest(
            deployment_bundle_id=uuid4(),
            target_state=RolloutState.CANARY,
            reason="Eval passed",
        )
        assert r.target_state == RolloutState.CANARY

    def test_promotion_response(self):
        r = BundlePromotionResponse(
            deployment_bundle_id=uuid4(),
            previous_state=RolloutState.SHADOW,
            new_state=RolloutState.CANARY,
            alias_updated=False,
        )
        assert r.alias_updated is False
