"""Serving API — REST endpoints for serving profiles, bundles, calibration, and promotion.

Routes:
    POST   /api/serving/profiles          — Create serving profile
    GET    /api/serving/profiles/{id}      — Get profile
    GET    /api/serving/profiles           — List profiles
    POST   /api/serving/bundles            — Create deployment bundle
    GET    /api/serving/bundles/{id}       — Get bundle
    GET    /api/serving/bundles            — List bundles
    POST   /api/serving/bundles/{id}/eval  — Run serving eval
    POST   /api/serving/bundles/{id}/promote — Promote bundle
    GET    /api/serving/active/{alias}     — Get active bundle for alias
    POST   /api/serving/calibrate          — Trigger KVTC calibration
    GET    /api/serving/inventory/{model_build_id} — Architecture inventory
    GET    /api/serving/health             — Health check

Date: 2026-03-21
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from mycosoft_mas.serving.bundle_manager import get_bundle_manager
from mycosoft_mas.serving.profile_manager import get_profile_manager
from mycosoft_mas.serving.promotion import PromotionError, get_promotion_engine
from mycosoft_mas.serving.schemas import (
    BundlePromotionRequest,
    BundlePromotionResponse,
    CacheMode,
    CalibrationRequest,
    CalibrationResponse,
    DeploymentBundle,
    DeploymentBundleCreate,
    ModelInventoryResult,
    RolloutState,
    ServingEvalRun,
    ServingProfile,
    ServingProfileCreate,
    TargetAlias,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/serving", tags=["serving"])


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@router.get("/health")
async def health():
    """Serving subsystem health check."""
    return {
        "status": "healthy",
        "subsystem": "serving",
        "components": {
            "profile_manager": "ok",
            "bundle_manager": "ok",
            "promotion_engine": "ok",
        },
    }


# ---------------------------------------------------------------------------
# Serving Profiles
# ---------------------------------------------------------------------------


@router.post("/profiles", response_model=ServingProfile)
async def create_profile(request: ServingProfileCreate):
    """Create a new serving profile."""
    pm = get_profile_manager()
    return pm.create_profile(request)


@router.get("/profiles/{profile_id}", response_model=ServingProfile)
async def get_profile(profile_id: UUID):
    """Get a serving profile by ID."""
    pm = get_profile_manager()
    profile = pm.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.get("/profiles", response_model=list[ServingProfile])
async def list_profiles(
    model_build_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    cache_mode: Optional[CacheMode] = Query(None),
):
    """List serving profiles with optional filters."""
    pm = get_profile_manager()
    return pm.list_profiles(
        model_build_id=model_build_id,
        status=status,
        cache_mode=cache_mode,
    )


@router.post("/profiles/{profile_id}/status")
async def update_profile_status(profile_id: UUID, new_status: str):
    """Transition a profile to a new status."""
    pm = get_profile_manager()
    try:
        profile = pm.update_status(profile_id, new_status)
        return {"status": "ok", "profile": profile}
    except KeyError:
        raise HTTPException(status_code=404, detail="Profile not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# Deployment Bundles
# ---------------------------------------------------------------------------


@router.post("/bundles", response_model=DeploymentBundle)
async def create_bundle(request: DeploymentBundleCreate):
    """Create a new deployment bundle."""
    bm = get_bundle_manager()
    try:
        return bm.create_bundle(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/bundles/{bundle_id}", response_model=DeploymentBundle)
async def get_bundle(bundle_id: UUID):
    """Get a deployment bundle by ID."""
    bm = get_bundle_manager()
    bundle = bm.get_bundle(bundle_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")
    return bundle


@router.get("/bundles", response_model=list[DeploymentBundle])
async def list_bundles(
    target_alias: Optional[TargetAlias] = Query(None),
    rollout_state: Optional[RolloutState] = Query(None),
    model_build_id: Optional[UUID] = Query(None),
):
    """List deployment bundles with optional filters."""
    bm = get_bundle_manager()
    return bm.list_bundles(
        target_alias=target_alias,
        rollout_state=rollout_state,
        model_build_id=model_build_id,
    )


@router.get("/active/{alias}")
async def get_active_bundle(alias: str):
    """Get the active deployment bundle for a target alias."""
    bm = get_bundle_manager()
    bundle = bm.get_active_bundle(alias)
    if not bundle:
        raise HTTPException(
            status_code=404,
            detail=f"No active bundle for alias '{alias}'",
        )
    return bundle


# ---------------------------------------------------------------------------
# Serving Eval
# ---------------------------------------------------------------------------


@router.post("/bundles/{bundle_id}/eval", response_model=ServingEvalRun)
async def run_serving_eval(
    bundle_id: UUID,
    eval_suite: str = "standard_serving",
):
    """Run a serving eval against a deployment bundle."""
    from mycosoft_mas.serving.eval_suite import ServingEvalSuite

    bm = get_bundle_manager()
    bundle = bm.get_bundle(bundle_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")

    pm = get_profile_manager()
    profile = pm.get_profile(bundle.serving_profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Serving profile not found")

    suite = ServingEvalSuite()
    return await suite.run_eval(bundle, profile, eval_suite)


@router.get("/bundles/{bundle_id}/evals", response_model=list[ServingEvalRun])
async def list_bundle_evals(bundle_id: UUID):
    """List all eval runs for a bundle."""
    bm = get_bundle_manager()
    return bm.get_evals_for_bundle(bundle_id)


# ---------------------------------------------------------------------------
# Promotion
# ---------------------------------------------------------------------------


@router.post("/bundles/{bundle_id}/promote", response_model=BundlePromotionResponse)
async def promote_bundle(bundle_id: UUID, target_state: RolloutState, reason: str = ""):
    """Promote a deployment bundle to a new rollout state."""
    engine = get_promotion_engine()
    try:
        return engine.promote(
            BundlePromotionRequest(
                deployment_bundle_id=bundle_id,
                target_state=target_state,
                reason=reason,
            )
        )
    except PromotionError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# Calibration
# ---------------------------------------------------------------------------


@router.post("/calibrate", response_model=CalibrationResponse)
async def trigger_calibration(request: CalibrationRequest):
    """Trigger KVTC calibration for a model build."""
    from mycosoft_mas.nlm.calibration import run_calibration_pipeline

    try:
        return await run_calibration_pipeline(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotImplementedError as e:
        raise HTTPException(
            status_code=501,
            detail=f"Calibration not fully wired: {e}",
        )


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------


@router.get("/inventory/{model_build_id}", response_model=ModelInventoryResult)
async def get_model_inventory(model_build_id: str, model_path: str = ""):
    """Get architecture inventory and KVTC compatibility for a model."""
    from mycosoft_mas.nlm.calibration.inventory import inventory_model

    return inventory_model(model_build_id=model_build_id, model_path=model_path)
