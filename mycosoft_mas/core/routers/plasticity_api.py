"""
Plasticity Forge Phase 1 — mutation and branch API (Mar 14, 2026).

Exposes branch creation via mutation engine and MINDEX registry.
No mock data. Uses plasticity_registry and plasticity.mutation_engine.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mycosoft_mas.integrations import plasticity_registry
from mycosoft_mas.plasticity.fitness_policy import evaluate_fitness, passes_hard_gates
from mycosoft_mas.plasticity.mutation_engine import apply_mutations
from mycosoft_mas.plasticity.promotion_controller import promote_to_active, rollback
from mycosoft_mas.plasticity.security_governance_sandbox import run_sandbox_check, sandbox_check_required

logger = logging.getLogger(__name__)

plasticity_router = APIRouter(prefix="/api/plasticity", tags=["plasticity"])


class PromoteRequest(BaseModel):
    """Request to promote a shadow/canary candidate to active for an alias."""
    alias: str = Field(..., description="Runtime alias (e.g. myca_core, myca_edge)")
    candidate_id: str = Field(..., description="Candidate to promote")
    decided_by: Optional[str] = Field(None, description="Optional identity for audit")


class RollbackRequest(BaseModel):
    """Request to rollback an alias to its candidate's rollback target."""
    alias: str = Field(..., description="Runtime alias to rollback")
    decided_by: Optional[str] = Field(None, description="Optional identity for audit")


class BranchRequest(BaseModel):
    """Request to branch a candidate by applying mutation operators."""
    parent_candidate_id: str = Field(..., description="Existing candidate to branch from")
    operators: List[Dict[str, Any]] = Field(
        ...,
        description="Sequence of {operator, params?}; operator must be in Phase 1 allowed set",
    )
    new_candidate_id: Optional[str] = Field(None, description="Optional ID for the new candidate; else auto-generated")


@plasticity_router.post("/branch")
def branch_candidate(body: BranchRequest) -> Dict[str, Any]:
    """
    Create a new candidate by applying mutation operators to a parent.
    Uses the mutation engine (narrow operators only) and registers the
    new genome in MINDEX plasticity registry. New candidate lifecycle is shadow.
    """
    parent = plasticity_registry.get_candidate(body.parent_candidate_id)
    if not parent:
        raise HTTPException(status_code=404, detail=f"parent_candidate_id not found: {body.parent_candidate_id}")

    try:
        genome = apply_mutations(
            parent_candidate=parent,
            operators=body.operators,
            new_candidate_id=body.new_candidate_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Build MINDEX payload: same keys as ModelCandidateCreate; drop created_at, promoted_at
    payload = {k: v for k, v in genome.items() if k not in ("created_at", "promoted_at")}
    for key in ("parent_candidate_ids", "eval_suite_ids"):
        if key in payload and payload[key] is None:
            payload[key] = []
    if payload.get("mutation_operators_applied") is None:
        payload["mutation_operators_applied"] = []

    result = plasticity_registry.create_candidate(payload)
    if not result:
        raise HTTPException(status_code=502, detail="MINDEX plasticity registry create_candidate failed")

    # Return full candidate from registry
    out = plasticity_registry.get_candidate(genome["candidate_id"])
    if not out:
        out = {"candidate_id": genome["candidate_id"], "created_at": result.get("created_at"), **genome}
    return out


def _require_fitness_gates() -> bool:
    """True if promotion must pass fitness hard gates (env PLASTICITY_REQUIRE_FITNESS_GATES=1)."""
    return os.getenv("PLASTICITY_REQUIRE_FITNESS_GATES", "").strip() in ("1", "true", "yes")


@plasticity_router.post("/promote")
def promote(body: PromoteRequest) -> Dict[str, Any]:
    """
    Promote a shadow or canary candidate to active for the given alias.
    Updates registry alias, candidate lifecycle, and records a promotion decision.
    If PLASTICITY_REQUIRE_FITNESS_GATES=1, candidate must pass all fitness hard gates.
    """
    candidate = plasticity_registry.get_candidate(body.candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail=f"candidate_id not found: {body.candidate_id}")

    if _require_fitness_gates():
        profile = evaluate_fitness(candidate, candidate.get("eval_summary"))
        if not passes_hard_gates(profile):
            raise HTTPException(
                status_code=400,
                detail="Candidate does not pass fitness hard gates; set PLASTICITY_REQUIRE_FITNESS_GATES=0 to skip",
            )

    if sandbox_check_required():
        sandbox_result = run_sandbox_check(candidate)
        if not sandbox_result.passed:
            raise HTTPException(
                status_code=400,
                detail=f"Sandbox check failed: {sandbox_result.failures}; set PLASTICITY_SANDBOX_CHECK=0 to skip",
            )

    try:
        return promote_to_active(
            alias=body.alias,
            candidate_id=body.candidate_id,
            decided_by=body.decided_by,
        )
    except ValueError as e:
        msg = str(e)
        if "not found" in msg.lower():
            raise HTTPException(status_code=404, detail=msg) from e
        raise HTTPException(status_code=400, detail=msg) from e


@plasticity_router.post("/rollback")
def rollback_alias(body: RollbackRequest) -> Dict[str, Any]:
    """
    Rollback an alias to its current candidate's rollback target.
    Fails if alias is missing or current candidate has no rollback_target_candidate_id.
    """
    try:
        return rollback(alias=body.alias, decided_by=body.decided_by)
    except ValueError as e:
        msg = str(e)
        if "not found" in msg.lower() or "alias not found" in msg.lower():
            raise HTTPException(status_code=404, detail=msg) from e
        raise HTTPException(status_code=400, detail=msg) from e
