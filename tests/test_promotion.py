"""Tests for bundle promotion engine.

Date: 2026-03-21
"""

import pytest
from uuid import uuid4

from mycosoft_mas.serving.profile_manager import ProfileManager
from mycosoft_mas.serving.bundle_manager import BundleManager
from mycosoft_mas.serving.promotion import BundlePromotionEngine, PromotionError
from mycosoft_mas.serving.schemas import (
    BundlePromotionRequest,
    CacheMode,
    DeploymentBundleCreate,
    RegressionVerdict,
    RolloutState,
    ServingEvalRunCreate,
    ServingProfileCreate,
    TargetAlias,
)


@pytest.fixture(autouse=True)
def clear_state():
    """Clear all in-memory state before each test."""
    from mycosoft_mas.serving import profile_manager as pm_mod
    from mycosoft_mas.serving import bundle_manager as bm_mod
    pm_mod._profiles.clear()
    bm_mod._bundles.clear()
    bm_mod._eval_runs.clear()
    bm_mod._active_bundles.clear()


@pytest.fixture
def setup():
    """Set up profile, bundle, and managers."""
    pm = ProfileManager()
    bm = BundleManager()
    engine = BundlePromotionEngine()

    profile = pm.create_profile(ServingProfileCreate(
        model_build_id=uuid4(),
        profile_name="test",
        cache_mode=CacheMode.KVTC_16X,
    ))
    pm.update_status(profile.serving_profile_id, "ready")

    bundle = bm.create_bundle(DeploymentBundleCreate(
        model_build_id=profile.model_build_id,
        serving_profile_id=profile.serving_profile_id,
        target_alias=TargetAlias.MYCA_CORE,
        target_runtime="vllm",
    ))

    return pm, bm, engine, profile, bundle


class TestPromotionEngine:
    def test_promote_shadow_to_canary_requires_eval(self, setup):
        _, _, engine, _, bundle = setup
        with pytest.raises(PromotionError, match="no eval runs"):
            engine.promote(BundlePromotionRequest(
                deployment_bundle_id=bundle.deployment_bundle_id,
                target_state=RolloutState.CANARY,
            ))

    def test_promote_shadow_to_canary_with_passing_eval(self, setup):
        _, bm, engine, _, bundle = setup
        bm.record_eval(ServingEvalRunCreate(
            deployment_bundle_id=bundle.deployment_bundle_id,
            eval_suite="test",
            regression_verdict=RegressionVerdict.PASS,
        ))
        result = engine.promote(BundlePromotionRequest(
            deployment_bundle_id=bundle.deployment_bundle_id,
            target_state=RolloutState.CANARY,
            reason="Eval passed",
        ))
        assert result.previous_state == RolloutState.SHADOW
        assert result.new_state == RolloutState.CANARY

    def test_promote_canary_to_active(self, setup):
        _, bm, engine, _, bundle = setup
        bm.record_eval(ServingEvalRunCreate(
            deployment_bundle_id=bundle.deployment_bundle_id,
            eval_suite="test",
            regression_verdict=RegressionVerdict.PASS,
        ))
        engine.promote(BundlePromotionRequest(
            deployment_bundle_id=bundle.deployment_bundle_id,
            target_state=RolloutState.CANARY,
        ))
        result = engine.promote(BundlePromotionRequest(
            deployment_bundle_id=bundle.deployment_bundle_id,
            target_state=RolloutState.ACTIVE,
        ))
        assert result.new_state == RolloutState.ACTIVE
        assert result.alias_updated is True

    def test_cannot_skip_canary(self, setup):
        _, bm, engine, _, bundle = setup
        bm.record_eval(ServingEvalRunCreate(
            deployment_bundle_id=bundle.deployment_bundle_id,
            eval_suite="test",
            regression_verdict=RegressionVerdict.PASS,
        ))
        with pytest.raises(PromotionError, match="Invalid transition"):
            engine.promote(BundlePromotionRequest(
                deployment_bundle_id=bundle.deployment_bundle_id,
                target_state=RolloutState.ACTIVE,
            ))

    def test_cannot_promote_with_failing_eval(self, setup):
        _, bm, engine, _, bundle = setup
        bm.record_eval(ServingEvalRunCreate(
            deployment_bundle_id=bundle.deployment_bundle_id,
            eval_suite="test",
            regression_verdict=RegressionVerdict.FAIL,
        ))
        with pytest.raises(PromotionError, match="FAIL verdict"):
            engine.promote(BundlePromotionRequest(
                deployment_bundle_id=bundle.deployment_bundle_id,
                target_state=RolloutState.CANARY,
            ))

    def test_cannot_promote_to_active_with_only_warns(self, setup):
        _, bm, engine, _, bundle = setup
        bm.record_eval(ServingEvalRunCreate(
            deployment_bundle_id=bundle.deployment_bundle_id,
            eval_suite="test",
            regression_verdict=RegressionVerdict.WARN,
        ))
        engine.promote(BundlePromotionRequest(
            deployment_bundle_id=bundle.deployment_bundle_id,
            target_state=RolloutState.CANARY,
        ))
        with pytest.raises(PromotionError, match="no eval with PASS"):
            engine.promote(BundlePromotionRequest(
                deployment_bundle_id=bundle.deployment_bundle_id,
                target_state=RolloutState.ACTIVE,
            ))

    def test_rollback(self, setup):
        _, bm, engine, _, bundle = setup
        bm.record_eval(ServingEvalRunCreate(
            deployment_bundle_id=bundle.deployment_bundle_id,
            eval_suite="test",
            regression_verdict=RegressionVerdict.PASS,
        ))
        engine.promote(BundlePromotionRequest(
            deployment_bundle_id=bundle.deployment_bundle_id,
            target_state=RolloutState.CANARY,
        ))
        result = engine.promote(BundlePromotionRequest(
            deployment_bundle_id=bundle.deployment_bundle_id,
            target_state=RolloutState.ROLLBACK,
            reason="Emergency rollback",
        ))
        assert result.new_state == RolloutState.ROLLBACK

    def test_retire_from_shadow(self, setup):
        _, _, engine, _, bundle = setup
        result = engine.promote(BundlePromotionRequest(
            deployment_bundle_id=bundle.deployment_bundle_id,
            target_state=RolloutState.RETIRED,
            reason="Not needed",
        ))
        assert result.new_state == RolloutState.RETIRED

    def test_bundle_not_found(self, setup):
        _, _, engine, _, _ = setup
        with pytest.raises(PromotionError, match="not found"):
            engine.promote(BundlePromotionRequest(
                deployment_bundle_id=uuid4(),
                target_state=RolloutState.CANARY,
            ))
