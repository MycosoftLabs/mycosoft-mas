"""
Mutation Engine v0 — narrow, reproducible operators for Plasticity Forge Phase 1.

Allowed: routing_policy, retrieval_policy, prompt_program_policy, lora_adapter,
reward_tweak, distillation, pruning, quantization.
Disallowed in Phase 1: full-weight rewrites from production traffic,
unsupervised topology edits, silent expert birth/death.

Created: March 14, 2026
"""

from __future__ import annotations

import copy
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from mycosoft_mas.schemas.plasticity_contracts import CandidateLifecycle, MutationOperator

ALLOWED_OPERATORS = {op.value for op in MutationOperator}


def validate_operator_params(operator: str, params: Optional[Dict[str, Any]] = None) -> None:
    """
    Validate that the operator is in the allowed set and params are acceptable.
    Raises ValueError if invalid. Phase 1 does not enforce strict param schemas
    per operator; we only reject unknown operators.
    """
    if operator not in ALLOWED_OPERATORS:
        raise ValueError(
            f"Operator '{operator}' is not allowed in Phase 1. "
            f"Allowed: {sorted(ALLOWED_OPERATORS)}"
        )
    if params is not None and not isinstance(params, dict):
        raise ValueError("params must be a dict or None")


def _apply_operator(
    genome: Dict[str, Any],
    operator: str,
    params: Optional[Dict[str, Any]],
) -> None:
    """
    Apply a single mutation operator to the genome in place.
    Records the operator and optional params; does not perform actual
    training or artifact production (that is the BranchTrainer's job).
    """
    applied = list(genome.get("mutation_operators_applied") or [])
    # Normalize to list of {operator, params}
    normalized = []
    for item in applied:
        if isinstance(item, dict):
            normalized.append(item)
        else:
            normalized.append({"operator": str(item), "params": {}})
    normalized.append({"operator": operator, "params": params or {}})
    genome["mutation_operators_applied"] = normalized

    # Operator-specific field hints (optional; trainer may override)
    if operator == MutationOperator.DISTILLATION.value and params:
        if params.get("teacher_candidate_id"):
            genome.setdefault("eval_summary", {})["distillation_teacher"] = params[
                "teacher_candidate_id"
            ]
    if operator == MutationOperator.QUANTIZATION.value and params:
        genome.setdefault("eval_summary", {})["quantization_bits"] = params.get("bits", 8)
    if operator == MutationOperator.LORA_ADAPTER.value and params:
        genome.setdefault("eval_summary", {})["lora_rank"] = params.get("rank")
    if operator == MutationOperator.PRUNING.value and params:
        genome.setdefault("eval_summary", {})["pruning_ratio"] = params.get("ratio")


def apply_mutations(
    parent_candidate: Dict[str, Any],
    operators: List[Dict[str, Any]],
    new_candidate_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Produce a new candidate genome from a parent by applying a sequence of
    mutation operators. Does not register the candidate; caller must POST
    to MINDEX plasticity registry.

    Each item in operators must have "operator" (str) and optionally "params" (dict).
    Validates all operators are in ALLOWED_OPERATORS.

    Returns a dict suitable for plasticity.model_candidate (and POST /api/mindex/plasticity/candidates).
    """
    parent_id = parent_candidate.get("candidate_id")
    if not parent_id:
        raise ValueError("parent_candidate must contain 'candidate_id'")

    genome = copy.deepcopy(parent_candidate)
    # New identity
    genome["candidate_id"] = new_candidate_id or f"cand_{uuid.uuid4().hex[:16]}"
    genome["created_at"] = datetime.now(timezone.utc).isoformat()
    genome["parent_candidate_ids"] = [parent_id]
    genome["mutation_operators_applied"] = list(genome.get("mutation_operators_applied") or [])
    # Normalize to list of {operator, params}
    if genome["mutation_operators_applied"] and isinstance(
        genome["mutation_operators_applied"][0], str
    ):
        genome["mutation_operators_applied"] = [
            {"operator": op, "params": {}} for op in genome["mutation_operators_applied"]
        ]

    # Reset lifecycle to shadow for new branch; clear promotion fields
    genome["lifecycle"] = CandidateLifecycle.SHADOW.value
    genome["promoted_at"] = None
    genome["alias"] = None
    genome["rollback_target_candidate_id"] = parent_id  # default rollback to parent

    for spec in operators:
        if not isinstance(spec, dict):
            raise ValueError("Each operator must be a dict with 'operator' and optional 'params'")
        op_name = spec.get("operator")
        if not op_name:
            raise ValueError("Each operator must have 'operator' key")
        params = spec.get("params")
        validate_operator_params(op_name, params)
        _apply_operator(genome, op_name, params)

    return genome
