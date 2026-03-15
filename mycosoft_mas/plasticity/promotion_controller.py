"""
Plasticity Forge Phase 1 — promotion and rollback controller (Mar 14, 2026).

Alias-based shadow → canary → active and rollback using registry-backed alias state.
Uses plasticity_registry (MINDEX) for set_alias, update_candidate, create_promotion_decision.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from mycosoft_mas.integrations import plasticity_registry
from mycosoft_mas.schemas.plasticity_contracts import CandidateLifecycle

logger = logging.getLogger(__name__)

_ALLOWED_PROMOTE_LIFECYCLES = (CandidateLifecycle.SHADOW.value, CandidateLifecycle.CANARY.value)


def promote_to_active(alias: str, candidate_id: str, decided_by: str | None = None) -> Dict[str, Any]:
    """
    Promote a candidate (shadow or canary) to active for the given alias.
    Sets alias -> candidate_id, updates candidate lifecycle to active, records promotion decision.
    Returns summary dict or raises ValueError on validation/registry failure.
    """
    candidate = plasticity_registry.get_candidate(candidate_id)
    if not candidate:
        raise ValueError(f"candidate_id not found: {candidate_id}")

    lifecycle = (candidate.get("lifecycle") or "").lower()
    if lifecycle not in _ALLOWED_PROMOTE_LIFECYCLES:
        raise ValueError(
            f"candidate {candidate_id} lifecycle is '{lifecycle}'; must be shadow or canary to promote"
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    decision_id = f"promote-{uuid.uuid4().hex[:12]}"

    if not plasticity_registry.set_alias(alias, candidate_id):
        raise ValueError("registry set_alias failed")
    if plasticity_registry.update_candidate(
        candidate_id, lifecycle=CandidateLifecycle.ACTIVE.value, promoted_at=now_iso
    ) is None:
        raise ValueError("registry update_candidate failed")
    if plasticity_registry.create_promotion_decision(
        decision_id=decision_id,
        candidate_id=candidate_id,
        from_lifecycle=lifecycle,
        to_lifecycle=CandidateLifecycle.ACTIVE.value,
        alias=alias,
        decided_by=decided_by,
    ) is None:
        raise ValueError("registry create_promotion_decision failed")

    return {
        "alias": alias,
        "candidate_id": candidate_id,
        "from_lifecycle": lifecycle,
        "to_lifecycle": CandidateLifecycle.ACTIVE.value,
        "decision_id": decision_id,
        "promoted_at": now_iso,
    }


def rollback(alias: str, decided_by: str | None = None) -> Dict[str, Any]:
    """
    Rollback alias to its current candidate's rollback_target_candidate_id.
    Sets alias -> rollback target, marks current candidate as rollback lifecycle, records decision.
    Returns summary dict or raises ValueError if alias missing or no rollback target.
    """
    resolved = plasticity_registry.resolve_alias(alias)
    if not resolved:
        raise ValueError(f"alias not found: {alias}")

    current_id = resolved.get("candidate_id")
    if not current_id:
        raise ValueError(f"alias {alias} has no candidate_id")

    current = plasticity_registry.get_candidate(current_id)
    if not current:
        raise ValueError(f"current candidate not found: {current_id}")

    rollback_target = current.get("rollback_target_candidate_id")
    if not rollback_target:
        raise ValueError(f"candidate {current_id} has no rollback_target_candidate_id; cannot rollback")

    decision_id = f"rollback-{uuid.uuid4().hex[:12]}"
    current_lifecycle = (current.get("lifecycle") or "active").lower()

    if not plasticity_registry.set_alias(alias, rollback_target):
        raise ValueError("registry set_alias failed")
    if plasticity_registry.update_candidate(
        current_id, lifecycle=CandidateLifecycle.ROLLBACK.value
    ) is None:
        raise ValueError("registry update_candidate failed")
    if plasticity_registry.create_promotion_decision(
        decision_id=decision_id,
        candidate_id=current_id,
        from_lifecycle=current_lifecycle,
        to_lifecycle=CandidateLifecycle.ROLLBACK.value,
        alias=alias,
        decided_by=decided_by,
    ) is None:
        raise ValueError("registry create_promotion_decision failed")

    return {
        "alias": alias,
        "previous_candidate_id": current_id,
        "rollback_to_candidate_id": rollback_target,
        "decision_id": decision_id,
        "to_lifecycle": CandidateLifecycle.ROLLBACK.value,
    }
