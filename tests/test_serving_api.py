"""Tests for serving API router.

Date: 2026-03-21
"""

import pytest
from uuid import uuid4

from mycosoft_mas.serving.schemas import (
    CacheMode,
    DeploymentBundleCreate,
    ServingProfileCreate,
    TargetAlias,
    TargetStack,
)


@pytest.fixture(autouse=True)
def clear_state():
    """Clear all in-memory state."""
    from mycosoft_mas.serving import profile_manager as pm_mod
    from mycosoft_mas.serving import bundle_manager as bm_mod
    pm_mod._profiles.clear()
    bm_mod._bundles.clear()
    bm_mod._eval_runs.clear()
    bm_mod._active_bundles.clear()


class TestServingAPIImports:
    """Verify serving API router imports correctly.

    Note: Full router import requires all MAS dependencies (httpx, etc.).
    Tests skip gracefully when full dependency chain is not available.
    """

    def _import_serving_router(self):
        try:
            import importlib
            mod = importlib.import_module("mycosoft_mas.core.routers.serving_api")
            return mod.router
        except (ImportError, ModuleNotFoundError) as e:
            pytest.skip(f"Serving router dependency unavailable: {e}")

    def test_router_importable(self):
        router = self._import_serving_router()
        assert router is not None
        assert router.prefix == "/api/serving"

    def test_router_has_routes(self):
        router = self._import_serving_router()
        route_paths = [r.path for r in router.routes]
        assert "/api/serving/health" in route_paths
        assert "/api/serving/profiles" in route_paths
        assert "/api/serving/bundles" in route_paths
        assert "/api/serving/calibrate" in route_paths

    def test_router_tags(self):
        router = self._import_serving_router()
        assert "serving" in router.tags


class TestServingSchemaIntegration:
    """Integration tests for schema usage in API context."""

    def test_profile_create_roundtrip(self):
        from mycosoft_mas.serving.profile_manager import ProfileManager
        pm = ProfileManager()
        created = pm.create_profile(ServingProfileCreate(
            model_build_id=uuid4(),
            profile_name="api-test",
            cache_mode=CacheMode.KVTC_16X,
            target_stack=TargetStack.VLLM,
        ))
        fetched = pm.get_profile(created.serving_profile_id)
        assert fetched.profile_name == "api-test"
        assert fetched.cache_mode == CacheMode.KVTC_16X

    def test_bundle_create_with_profile(self):
        from mycosoft_mas.serving.profile_manager import ProfileManager
        from mycosoft_mas.serving.bundle_manager import BundleManager

        pm = ProfileManager()
        bm = BundleManager()

        profile = pm.create_profile(ServingProfileCreate(
            model_build_id=uuid4(),
            profile_name="api-test",
        ))
        pm.update_status(profile.serving_profile_id, "ready")

        bundle = bm.create_bundle(DeploymentBundleCreate(
            model_build_id=profile.model_build_id,
            serving_profile_id=profile.serving_profile_id,
            target_alias=TargetAlias.MYCA_CORE,
            target_runtime="vllm",
        ))
        assert bundle.rollout_state.value == "shadow"
