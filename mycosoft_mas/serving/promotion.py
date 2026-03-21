"""Bundle promotion engine — manages rollout state transitions.

State machine: shadow → canary → active → rollback → retired

Promotion rules:
    1. Serving eval must pass (verdict != 'fail') before any promotion
    2. shadow → canary: requires at least one passing eval
    3. canary → active: requires canary-duration eval coverage
    4. active → rollback: immediate (emergency path)
    5. rollback → shadow: re-enter pipeline for re-evaluation

On activation, updates the alias resolution layer so backend_selection.py
routes to the new bundle's serving config.

Date: 2026-03-21
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from .bundle_manager import get_bundle_manager
from .schemas import (
    BundlePromotionRequest,
    BundlePromotionResponse,
    RegressionVerdict,
    RolloutState,
    VALID_TRANSITIONS,
)

logger = logging.getLogger(__name__)


class PromotionError(Exception):
    """Raised when a promotion fails validation."""


class BundlePromotionEngine:
    """Manages deployment bundle promotion through rollout states."""

    def promote(self, request: BundlePromotionRequest) -> BundlePromotionResponse:
        """Promote a bundle to a new rollout state.

        Args:
            request: Promotion request with bundle ID, target state, and reason.

        Returns:
            BundlePromotionResponse with transition details.

        Raises:
            PromotionError: If the promotion fails validation.
        """
        bm = get_bundle_manager()
        bundle = bm.get_bundle(request.deployment_bundle_id)
        if not bundle:
            raise PromotionError(
                f"Bundle {request.deployment_bundle_id} not found"
            )

        current_state = bundle.rollout_state
        target_state = request.target_state

        # Validate transition
        valid_targets = VALID_TRANSITIONS.get(current_state, [])
        if target_state not in valid_targets:
            raise PromotionError(
                f"Invalid transition: {current_state.value} → {target_state.value}. "
                f"Valid targets: {[s.value for s in valid_targets]}"
            )

        # Check eval requirements (except for rollback/retire which are emergency paths)
        if target_state in (RolloutState.CANARY, RolloutState.ACTIVE):
            self._check_eval_requirements(bundle.deployment_bundle_id, target_state)

        # Execute transition
        previous_state = current_state
        alias_updated = False
        rollback_bundle_id = None

        if target_state == RolloutState.ACTIVE:
            bm.set_active(bundle.deployment_bundle_id)
            alias_updated = True
            logger.info(
                "PROMOTED bundle %s to ACTIVE for alias %s (reason: %s)",
                bundle.deployment_bundle_id,
                bundle.target_alias.value,
                request.reason,
            )

        elif target_state == RolloutState.ROLLBACK:
            rollback_target = bm.set_rollback(bundle.deployment_bundle_id)
            if rollback_target:
                rollback_bundle_id = rollback_target.deployment_bundle_id
                alias_updated = True
            logger.warning(
                "ROLLBACK bundle %s (reason: %s). Activated: %s",
                bundle.deployment_bundle_id,
                request.reason,
                rollback_bundle_id,
            )

        elif target_state == RolloutState.RETIRED:
            bundle.rollout_state = RolloutState.RETIRED
            logger.info(
                "RETIRED bundle %s (reason: %s)",
                bundle.deployment_bundle_id,
                request.reason,
            )

        else:
            # SHADOW, CANARY — just update state
            bundle.rollout_state = target_state
            logger.info(
                "Bundle %s: %s → %s (reason: %s)",
                bundle.deployment_bundle_id,
                previous_state.value,
                target_state.value,
                request.reason,
            )

        # Persist to MINDEX via plasticity registry
        self._persist_to_mindex(bundle, previous_state, target_state, request.reason)

        return BundlePromotionResponse(
            deployment_bundle_id=bundle.deployment_bundle_id,
            previous_state=previous_state,
            new_state=target_state,
            rollback_bundle_id=rollback_bundle_id,
            alias_updated=alias_updated,
        )

    def _check_eval_requirements(
        self, bundle_id: UUID, target_state: RolloutState
    ) -> None:
        """Verify that eval requirements are met for promotion.

        Raises PromotionError if requirements are not met.
        """
        bm = get_bundle_manager()
        evals = bm.get_evals_for_bundle(bundle_id)

        if not evals:
            raise PromotionError(
                f"Cannot promote to {target_state.value}: no eval runs found. "
                f"Run a serving eval first."
            )

        # Check for any failing evals
        failing = [
            e for e in evals
            if e.regression_verdict == RegressionVerdict.FAIL
        ]
        if failing:
            raise PromotionError(
                f"Cannot promote to {target_state.value}: "
                f"{len(failing)} eval(s) have FAIL verdict. "
                f"Fix regressions before promoting."
            )

        # For ACTIVE: require at least one PASS (not just WARN)
        if target_state == RolloutState.ACTIVE:
            passing = [
                e for e in evals
                if e.regression_verdict == RegressionVerdict.PASS
            ]
            if not passing:
                raise PromotionError(
                    f"Cannot promote to ACTIVE: no eval with PASS verdict. "
                    f"All evals are WARN — resolve warnings before activating."
                )

    def _persist_to_mindex(
        self,
        bundle: Any,
        from_state: RolloutState,
        to_state: RolloutState,
        reason: str,
    ) -> None:
        """Persist promotion decision to MINDEX via plasticity registry.

        Best-effort — does not fail the promotion if MINDEX is unreachable.
        """
        try:
            from mycosoft_mas.integrations.plasticity_registry import (
                create_promotion_decision,
                lineage_event_create,
                update_deployment_bundle,
            )

            # Update bundle state in MINDEX
            promoted_at = None
            if to_state == RolloutState.ACTIVE:
                promoted_at = datetime.now(timezone.utc).isoformat()

            update_deployment_bundle(
                bundle_id=str(bundle.deployment_bundle_id),
                rollout_state=to_state.value,
                promoted_at=promoted_at,
            )

            # Record promotion decision
            create_promotion_decision(
                decision_id=str(uuid4()),
                candidate_id=str(bundle.model_build_id),
                from_lifecycle=from_state.value,
                to_lifecycle=to_state.value,
                alias=bundle.target_alias.value if hasattr(bundle.target_alias, 'value') else str(bundle.target_alias),
                decided_by="serving_promotion_engine",
            )

            # Record lineage event
            lineage_event_create(
                event_id=str(uuid4()),
                candidate_id=str(bundle.model_build_id),
                event_type=f"bundle_promotion_{to_state.value}",
                payload={
                    "bundle_id": str(bundle.deployment_bundle_id),
                    "from_state": from_state.value,
                    "to_state": to_state.value,
                    "reason": reason,
                    "serving_profile_id": str(bundle.serving_profile_id),
                },
            )

            logger.info(
                "Persisted promotion to MINDEX: bundle=%s %s→%s",
                bundle.deployment_bundle_id,
                from_state.value,
                to_state.value,
            )
        except Exception as e:
            logger.warning(
                "Failed to persist promotion to MINDEX (non-fatal): %s", e
            )


# Module-level singleton
_engine: Optional[BundlePromotionEngine] = None


def get_promotion_engine() -> BundlePromotionEngine:
    """Get or create the promotion engine singleton."""
    global _engine
    if _engine is None:
        _engine = BundlePromotionEngine()
    return _engine
