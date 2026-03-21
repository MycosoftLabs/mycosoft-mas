"""Tests for deployment bundle and profile management.

Date: 2026-03-21
"""

import pytest
from uuid import uuid4

from mycosoft_mas.serving.profile_manager import ProfileManager, VALID_STATUS_TRANSITIONS
from mycosoft_mas.serving.bundle_manager import BundleManager
from mycosoft_mas.serving.schemas import (
    CacheMode,
    DeploymentBundleCreate,
    RegressionVerdict,
    RolloutState,
    ServingEvalRunCreate,
    ServingProfileCreate,
    TargetAlias,
    TargetStack,
)


@pytest.fixture
def profile_manager():
    """Fresh profile manager with cleared state."""
    from mycosoft_mas.serving import profile_manager as pm_mod
    pm_mod._profiles.clear()
    return ProfileManager()


@pytest.fixture
def bundle_manager(profile_manager):
    """Fresh bundle manager with cleared state."""
    from mycosoft_mas.serving import bundle_manager as bm_mod
    bm_mod._bundles.clear()
    bm_mod._eval_runs.clear()
    bm_mod._active_bundles.clear()
    return BundleManager()


@pytest.fixture
def sample_profile(profile_manager):
    """Create a sample profile in 'ready' state."""
    p = profile_manager.create_profile(ServingProfileCreate(
        model_build_id=uuid4(),
        profile_name="test-kvtc16x",
        cache_mode=CacheMode.KVTC_16X,
        target_stack=TargetStack.VLLM,
    ))
    profile_manager.update_status(p.serving_profile_id, "ready")
    return p


class TestProfileManager:
    def test_create_profile(self, profile_manager):
        p = profile_manager.create_profile(ServingProfileCreate(
            model_build_id=uuid4(),
            profile_name="test",
        ))
        assert p.status == "draft"
        assert p.cache_mode == CacheMode.BASELINE

    def test_get_profile(self, profile_manager):
        p = profile_manager.create_profile(ServingProfileCreate(
            model_build_id=uuid4(),
            profile_name="test",
        ))
        fetched = profile_manager.get_profile(p.serving_profile_id)
        assert fetched is not None
        assert fetched.profile_name == "test"

    def test_list_profiles(self, profile_manager):
        mid = uuid4()
        profile_manager.create_profile(ServingProfileCreate(
            model_build_id=mid, profile_name="a",
        ))
        profile_manager.create_profile(ServingProfileCreate(
            model_build_id=mid, profile_name="b",
        ))
        results = profile_manager.list_profiles(model_build_id=mid)
        assert len(results) == 2

    def test_status_transitions(self, profile_manager):
        p = profile_manager.create_profile(ServingProfileCreate(
            model_build_id=uuid4(), profile_name="t",
        ))
        p = profile_manager.update_status(p.serving_profile_id, "ready")
        assert p.status == "ready"

    def test_invalid_status_transition(self, profile_manager):
        p = profile_manager.create_profile(ServingProfileCreate(
            model_build_id=uuid4(), profile_name="t",
        ))
        with pytest.raises(ValueError, match="Cannot transition"):
            profile_manager.update_status(p.serving_profile_id, "active")

    def test_link_artifact(self, profile_manager):
        p = profile_manager.create_profile(ServingProfileCreate(
            model_build_id=uuid4(), profile_name="t",
        ))
        art_id = uuid4()
        p = profile_manager.link_artifact(p.serving_profile_id, art_id)
        assert p.artifact_ref == art_id

    def test_delete_draft_profile(self, profile_manager):
        p = profile_manager.create_profile(ServingProfileCreate(
            model_build_id=uuid4(), profile_name="t",
        ))
        assert profile_manager.delete_profile(p.serving_profile_id) is True
        assert profile_manager.get_profile(p.serving_profile_id) is None

    def test_cannot_delete_non_draft(self, profile_manager):
        p = profile_manager.create_profile(ServingProfileCreate(
            model_build_id=uuid4(), profile_name="t",
        ))
        profile_manager.update_status(p.serving_profile_id, "ready")
        with pytest.raises(ValueError, match="Cannot delete"):
            profile_manager.delete_profile(p.serving_profile_id)


class TestBundleManager:
    def test_create_bundle(self, bundle_manager, sample_profile):
        b = bundle_manager.create_bundle(DeploymentBundleCreate(
            model_build_id=sample_profile.model_build_id,
            serving_profile_id=sample_profile.serving_profile_id,
            target_alias=TargetAlias.MYCA_CORE,
            target_runtime="vllm",
        ))
        assert b.rollout_state == RolloutState.SHADOW
        assert b.target_alias == TargetAlias.MYCA_CORE

    def test_create_bundle_invalid_profile(self, bundle_manager):
        with pytest.raises(ValueError, match="not found"):
            bundle_manager.create_bundle(DeploymentBundleCreate(
                model_build_id=uuid4(),
                serving_profile_id=uuid4(),
                target_alias=TargetAlias.MYCA_CORE,
                target_runtime="vllm",
            ))

    def test_list_bundles(self, bundle_manager, sample_profile):
        for _ in range(3):
            bundle_manager.create_bundle(DeploymentBundleCreate(
                model_build_id=sample_profile.model_build_id,
                serving_profile_id=sample_profile.serving_profile_id,
                target_alias=TargetAlias.MYCA_CORE,
                target_runtime="vllm",
            ))
        results = bundle_manager.list_bundles(target_alias=TargetAlias.MYCA_CORE)
        assert len(results) == 3

    def test_set_active(self, bundle_manager, sample_profile):
        b = bundle_manager.create_bundle(DeploymentBundleCreate(
            model_build_id=sample_profile.model_build_id,
            serving_profile_id=sample_profile.serving_profile_id,
            target_alias=TargetAlias.MYCA_CORE,
            target_runtime="vllm",
        ))
        bundle_manager.set_active(b.deployment_bundle_id)
        active = bundle_manager.get_active_bundle("myca_core")
        assert active is not None
        assert active.deployment_bundle_id == b.deployment_bundle_id
        assert active.rollout_state == RolloutState.ACTIVE

    def test_set_active_retires_previous(self, bundle_manager, sample_profile):
        b1 = bundle_manager.create_bundle(DeploymentBundleCreate(
            model_build_id=sample_profile.model_build_id,
            serving_profile_id=sample_profile.serving_profile_id,
            target_alias=TargetAlias.MYCA_CORE,
            target_runtime="vllm",
        ))
        bundle_manager.set_active(b1.deployment_bundle_id)

        b2 = bundle_manager.create_bundle(DeploymentBundleCreate(
            model_build_id=sample_profile.model_build_id,
            serving_profile_id=sample_profile.serving_profile_id,
            target_alias=TargetAlias.MYCA_CORE,
            target_runtime="vllm",
        ))
        bundle_manager.set_active(b2.deployment_bundle_id)

        b1_refreshed = bundle_manager.get_bundle(b1.deployment_bundle_id)
        assert b1_refreshed.rollout_state == RolloutState.RETIRED

    def test_record_eval(self, bundle_manager, sample_profile):
        b = bundle_manager.create_bundle(DeploymentBundleCreate(
            model_build_id=sample_profile.model_build_id,
            serving_profile_id=sample_profile.serving_profile_id,
            target_alias=TargetAlias.MYCA_CORE,
            target_runtime="vllm",
        ))
        ev = bundle_manager.record_eval(ServingEvalRunCreate(
            deployment_bundle_id=b.deployment_bundle_id,
            eval_suite="test",
            regression_verdict=RegressionVerdict.PASS,
        ))
        assert ev.regression_verdict == RegressionVerdict.PASS
        evals = bundle_manager.get_evals_for_bundle(b.deployment_bundle_id)
        assert len(evals) == 1

    def test_rollback(self, bundle_manager, sample_profile):
        b1 = bundle_manager.create_bundle(DeploymentBundleCreate(
            model_build_id=sample_profile.model_build_id,
            serving_profile_id=sample_profile.serving_profile_id,
            target_alias=TargetAlias.MYCA_CORE,
            target_runtime="vllm",
        ))
        bundle_manager.set_active(b1.deployment_bundle_id)

        b2 = bundle_manager.create_bundle(DeploymentBundleCreate(
            model_build_id=sample_profile.model_build_id,
            serving_profile_id=sample_profile.serving_profile_id,
            target_alias=TargetAlias.MYCA_CORE,
            target_runtime="vllm",
            rollback_bundle_id=b1.deployment_bundle_id,
        ))
        bundle_manager.set_active(b2.deployment_bundle_id)

        rollback_target = bundle_manager.set_rollback(b2.deployment_bundle_id)
        assert rollback_target is not None
        assert rollback_target.deployment_bundle_id == b1.deployment_bundle_id

        b2_refreshed = bundle_manager.get_bundle(b2.deployment_bundle_id)
        assert b2_refreshed.rollout_state == RolloutState.ROLLBACK
