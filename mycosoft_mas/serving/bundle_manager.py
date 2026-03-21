"""Deployment bundle lifecycle management.

A deployment bundle is the atomic unit of promotion:
    model_build + adapter_set + serving_profile + cache_policy + target

Bundles move through: shadow → canary → active → rollback → retired

Date: 2026-03-21
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from .profile_manager import get_profile_manager
from .schemas import (
    DeploymentBundle,
    DeploymentBundleCreate,
    RolloutState,
    ServingEvalRun,
    ServingEvalRunCreate,
    TargetAlias,
)

logger = logging.getLogger(__name__)

# In-memory stores — production uses MINDEX Postgres
_bundles: dict[UUID, DeploymentBundle] = {}
_eval_runs: dict[UUID, ServingEvalRun] = {}

# Active bundle per target alias (only one active bundle per alias)
_active_bundles: dict[str, UUID] = {}


class BundleManager:
    """Deployment bundle CRUD and lifecycle operations."""

    def create_bundle(self, request: DeploymentBundleCreate) -> DeploymentBundle:
        """Create a new deployment bundle in shadow state.

        Validates that the referenced serving profile exists and is ready.
        """
        pm = get_profile_manager()
        profile = pm.get_profile(request.serving_profile_id)
        if not profile:
            raise ValueError(
                f"Serving profile {request.serving_profile_id} not found"
            )
        if profile.status not in ("ready", "shadow", "canary", "active"):
            raise ValueError(
                f"Serving profile must be in ready+ state, got '{profile.status}'"
            )

        bundle = DeploymentBundle(
            **request.model_dump(),
            deployment_bundle_id=uuid4(),
            rollout_state=RolloutState.SHADOW,
            promoted_at=None,
            created_at=datetime.utcnow(),
        )
        _bundles[bundle.deployment_bundle_id] = bundle

        logger.info(
            "Created bundle %s: model=%s profile=%s alias=%s",
            bundle.deployment_bundle_id,
            bundle.model_build_id,
            bundle.serving_profile_id,
            bundle.target_alias.value,
        )
        return bundle

    def get_bundle(self, bundle_id: UUID) -> Optional[DeploymentBundle]:
        """Get a deployment bundle by ID."""
        return _bundles.get(bundle_id)

    def list_bundles(
        self,
        target_alias: Optional[TargetAlias] = None,
        rollout_state: Optional[RolloutState] = None,
        model_build_id: Optional[UUID] = None,
    ) -> list[DeploymentBundle]:
        """List bundles with optional filters."""
        results = list(_bundles.values())
        if target_alias:
            results = [b for b in results if b.target_alias == target_alias]
        if rollout_state:
            results = [b for b in results if b.rollout_state == rollout_state]
        if model_build_id:
            results = [b for b in results if b.model_build_id == model_build_id]
        return sorted(results, key=lambda b: b.created_at, reverse=True)

    def get_active_bundle(self, target_alias: str) -> Optional[DeploymentBundle]:
        """Get the currently active bundle for a target alias."""
        bundle_id = _active_bundles.get(target_alias)
        if bundle_id:
            return _bundles.get(bundle_id)
        return None

    def record_eval(self, request: ServingEvalRunCreate) -> ServingEvalRun:
        """Record a serving eval run for a bundle."""
        bundle = _bundles.get(request.deployment_bundle_id)
        if not bundle:
            raise ValueError(
                f"Bundle {request.deployment_bundle_id} not found"
            )

        eval_run = ServingEvalRun(
            **request.model_dump(),
            serving_eval_run_id=uuid4(),
            created_at=datetime.utcnow(),
        )
        _eval_runs[eval_run.serving_eval_run_id] = eval_run

        logger.info(
            "Recorded eval %s for bundle %s: verdict=%s",
            eval_run.serving_eval_run_id,
            request.deployment_bundle_id,
            eval_run.regression_verdict,
        )
        return eval_run

    def get_evals_for_bundle(self, bundle_id: UUID) -> list[ServingEvalRun]:
        """Get all eval runs for a bundle."""
        return [
            e for e in _eval_runs.values()
            if e.deployment_bundle_id == bundle_id
        ]

    def set_active(self, bundle_id: UUID) -> None:
        """Set a bundle as the active bundle for its target alias.

        Retires the previously active bundle for the same alias.
        """
        bundle = _bundles.get(bundle_id)
        if not bundle:
            raise KeyError(f"Bundle {bundle_id} not found")

        alias = bundle.target_alias.value

        # Retire previous active
        prev_id = _active_bundles.get(alias)
        if prev_id and prev_id != bundle_id:
            prev = _bundles.get(prev_id)
            if prev and prev.rollout_state == RolloutState.ACTIVE:
                prev.rollout_state = RolloutState.RETIRED
                _bundles[prev_id] = prev
                logger.info("Retired previous active bundle %s for alias %s", prev_id, alias)

        _active_bundles[alias] = bundle_id
        bundle.rollout_state = RolloutState.ACTIVE
        bundle.promoted_at = datetime.utcnow()
        _bundles[bundle_id] = bundle

        logger.info("Bundle %s is now ACTIVE for alias %s", bundle_id, alias)

    def set_rollback(self, bundle_id: UUID) -> Optional[DeploymentBundle]:
        """Roll back a bundle, activating its rollback_bundle_id if set."""
        bundle = _bundles.get(bundle_id)
        if not bundle:
            raise KeyError(f"Bundle {bundle_id} not found")

        bundle.rollout_state = RolloutState.ROLLBACK
        _bundles[bundle_id] = bundle

        alias = bundle.target_alias.value

        # Activate rollback bundle if specified
        rollback_bundle = None
        if bundle.rollback_bundle_id:
            rollback_bundle = _bundles.get(bundle.rollback_bundle_id)
            if rollback_bundle:
                self.set_active(rollback_bundle.deployment_bundle_id)
                logger.info(
                    "Rolled back %s → activated rollback bundle %s",
                    bundle_id,
                    rollback_bundle.deployment_bundle_id,
                )
        else:
            # Remove from active if no rollback target
            if _active_bundles.get(alias) == bundle_id:
                del _active_bundles[alias]

        return rollback_bundle


# Module-level singleton
_manager: Optional[BundleManager] = None


def get_bundle_manager() -> BundleManager:
    """Get or create the bundle manager singleton."""
    global _manager
    if _manager is None:
        _manager = BundleManager()
    return _manager
