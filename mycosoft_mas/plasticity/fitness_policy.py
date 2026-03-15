"""
Plasticity Forge Phase 1 — fitness policy: hard gates and Pareto selection.

Hard gates: safety, provenance, reproducibility, regression cap,
hardware envelope, retention. A candidate is rejected if any gate fails.

Soft objectives: task_success, groundedness, calibration, latency, memory,
watts, retention, compression_ratio, edge_fitness. Selection uses Pareto
dominance; joint MYCA+AVANI score included where available.

Created: March 14, 2026
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from mycosoft_mas.schemas.plasticity_contracts import FitnessProfile


# Default thresholds for hard gates (configurable via env or registry later)
DEFAULT_REGRESSION_CAP_PCT = 5.0
DEFAULT_RETENTION_MIN = 0.7
DEFAULT_LATENCY_P99_MS_MAX = 5000.0
DEFAULT_MEMORY_MB_MAX = 32 * 1024
DEFAULT_SAFETY_VERDICT_PASS = "pass"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def evaluate_fitness(
    candidate: Dict[str, Any],
    eval_results: Optional[Dict[str, Any]] = None,
    *,
    regression_cap_pct: float = DEFAULT_REGRESSION_CAP_PCT,
    retention_min: float = DEFAULT_RETENTION_MIN,
    latency_p99_max_ms: float = DEFAULT_LATENCY_P99_MS_MAX,
    memory_mb_max: float = DEFAULT_MEMORY_MB_MAX,
) -> FitnessProfile:
    """
    Build a FitnessProfile from a candidate genome and optional eval results.
    Fills hard gates from candidate + eval; fills soft objectives from eval_results
    when present, else defaults to 0.0 / False.
    """
    cid = candidate.get("candidate_id") or ""
    ev = eval_results or {}

    # Hard gates from candidate + eval
    safety_verdict = (candidate.get("safety_verdict") or ev.get("safety_verdict") or "").lower()
    safety_ok = safety_verdict == "pass" or safety_verdict == "pending"

    provenance_complete = bool(
        candidate.get("base_model_id")
        and (candidate.get("data_curriculum_hash") or candidate.get("training_code_hash"))
    )
    if ev.get("provenance_complete") is not None:
        provenance_complete = bool(ev["provenance_complete"])

    reproducible = bool(candidate.get("training_code_hash") and candidate.get("data_curriculum_hash"))
    if ev.get("reproducible") is not None:
        reproducible = bool(ev["reproducible"])

    regress_pct = ev.get("regression_pct") or 0.0
    regression_within_cap = regress_pct <= regression_cap_pct

    latency_p99 = candidate.get("latency_p99_ms") or ev.get("latency_p99_ms") or 0.0
    memory_mb = candidate.get("memory_mb") or ev.get("memory_mb") or 0.0
    hardware_envelope_ok = (
        latency_p99 <= latency_p99_max_ms
        and memory_mb <= memory_mb_max
    )
    if ev.get("hardware_envelope_ok") is not None:
        hardware_envelope_ok = bool(ev["hardware_envelope_ok"])

    retention = ev.get("retention_score") or ev.get("retention") or 0.0
    retention_above_threshold = retention >= retention_min
    if ev.get("retention_above_threshold") is not None:
        retention_above_threshold = bool(ev["retention_above_threshold"])

    # Soft objectives (0.0–1.0 or raw scores; normalize in Pareto if needed)
    task_success = float(ev.get("task_success", 0.0))
    groundedness = float(ev.get("groundedness", 0.0))
    calibration = float(ev.get("calibration", 0.0))
    latency_score = float(ev.get("latency_score", 0.0))
    memory_score = float(ev.get("memory_score", 0.0))
    watts_score = float(ev.get("watts_score", 0.0))
    retention_score = float(ev.get("retention_score", retention))
    compression_ratio = float(ev.get("compression_ratio", 0.0))
    edge_fitness = float(ev.get("edge_fitness", 0.0))
    if candidate.get("jetson_compatible"):
        edge_fitness = max(edge_fitness, 0.5)

    myca_only = ev.get("myca_only_score")
    avani_only = ev.get("avani_only_score")
    joint_score = ev.get("joint_score")

    return FitnessProfile(
        candidate_id=cid,
        evaluated_at=ev.get("evaluated_at") or _now_iso(),
        safety_ok=safety_ok,
        provenance_complete=provenance_complete,
        reproducible=reproducible,
        regression_within_cap=regression_within_cap,
        hardware_envelope_ok=hardware_envelope_ok,
        retention_above_threshold=retention_above_threshold,
        task_success=task_success,
        groundedness=groundedness,
        calibration=calibration,
        latency_score=latency_score,
        memory_score=memory_score,
        watts_score=watts_score,
        retention_score=retention_score,
        compression_ratio=compression_ratio,
        edge_fitness=edge_fitness,
        myca_only_score=float(myca_only) if myca_only is not None else None,
        avani_only_score=float(avani_only) if avani_only is not None else None,
        joint_score=float(joint_score) if joint_score is not None else None,
    )


def passes_hard_gates(profile: FitnessProfile) -> bool:
    """Return True iff all hard gates pass (candidate is eligible for promotion)."""
    return (
        profile.safety_ok
        and profile.provenance_complete
        and profile.reproducible
        and profile.regression_within_cap
        and profile.hardware_envelope_ok
        and profile.retention_above_threshold
    )


def _dominates(a: FitnessProfile, b: FitnessProfile, objectives: List[str]) -> bool:
    """True if a Pareto-dominates b (a >= b on all objectives and strictly > on at least one)."""
    at_least_one_strict = False
    for key in objectives:
        va = getattr(a, key, 0.0) or 0.0
        vb = getattr(b, key, 0.0) or 0.0
        if va < vb:
            return False
        if va > vb:
            at_least_one_strict = True
    return at_least_one_strict


SOFT_OBJECTIVES = [
    "task_success", "groundedness", "calibration", "latency_score", "memory_score",
    "watts_score", "retention_score", "compression_ratio", "edge_fitness",
]


def pareto_rank(
    candidates_with_profiles: List[Tuple[Dict[str, Any], FitnessProfile]],
    use_joint_score: bool = True,
) -> List[Tuple[Dict[str, Any], FitnessProfile, int]]:
    """
    Rank candidates by Pareto dominance. Returns list of (candidate, profile, rank).
    Rank 1 = non-dominated (Pareto front), rank 2 = dominated only by rank 1, etc.
    When use_joint_score is True and joint_score is present, include it in objectives.
    """
    objectives = list(SOFT_OBJECTIVES)
    if use_joint_score:
        objectives = ["joint_score"] + objectives  # prefer joint when available

    # Filter to valid profiles
    valid = [(c, p) for c, p in candidates_with_profiles if p is not None]
    if not valid:
        return []

    # Compute dominance: for each i, count how many j dominate i
    n = len(valid)
    dominated_count = [0] * n
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            if _dominates(valid[j][1], valid[i][1], objectives):
                dominated_count[i] += 1

    # Rank = 1 + number of candidates that dominate this one
    result = []
    for idx, (c, p) in enumerate(valid):
        rank = dominated_count[idx] + 1
        result.append((c, p, rank))
    result.sort(key=lambda x: x[2])
    return result


def fitness_profile_to_dict(profile: FitnessProfile) -> Dict[str, Any]:
    """Serialize FitnessProfile for registry/API."""
    d = asdict(profile)
    return d
