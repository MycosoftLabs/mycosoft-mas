"""FormSpace dynamics: trajectory, recovery, and perturbation jobs.

Uses native SSM scan arithmetic from the FormSpace family.
Does not invent Fusarium ecology probabilities or confidence scores.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence
from uuid import uuid4

from .atlas import get_atlas
from .native_ssm import inverse_variance_fusion, native_scan


def compute_trajectory(
    series: Sequence[float],
    *,
    chart_id: str,
    chart_version: str = "v1",
    dt: float = 0.1,
    a: float = -0.5,
    b: float = 1.0,
    h0: float = 0.0,
    origin: str = "CATALOG_FIXTURE",
) -> Dict[str, Any]:
    """Project an input series through FormSpace native SSM scan."""
    if not series:
        return {
            "ok": False,
            "status": "no_data",
            "chart_id": chart_id,
            "chart_version": chart_version,
            "trajectory": [],
            "final_state": None,
            "message": "No observation series provided. Live panels abstain.",
            "p": None,
        }
    trajectory, final_state = native_scan(list(series), dt=dt, a=a, b=b, h=h0)
    return {
        "ok": True,
        "status": "computed",
        "job_id": f"traj-{uuid4().hex[:12]}",
        "chart_id": chart_id,
        "chart_version": chart_version,
        "origin": origin,
        "params": {"dt": dt, "a": a, "b": b, "h0": h0},
        "input_series": list(series),
        "trajectory": trajectory,
        "final_state": final_state,
        "p": None,
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "note": "Native FormSpace SSM scan. Not an LLM. No invented ecology p.",
    }


def run_recovery_experiment(
    *,
    chart_id: str,
    baseline: Sequence[float],
    perturbation_index: int,
    perturbation_delta: float = 0.3,
    dt: float = 0.1,
    a: float = -0.5,
    b: float = 1.0,
    origin: str = "EXPERIMENT",
) -> Dict[str, Any]:
    """Perturb a series mid-horizon and measure return toward baseline path."""
    if not baseline:
        return {
            "ok": False,
            "status": "no_data",
            "chart_id": chart_id,
            "message": "Recovery experiment requires a nonempty baseline series.",
            "p": None,
        }
    series = list(baseline)
    idx = max(0, min(perturbation_index, len(series) - 1))
    perturbed = list(series)
    perturbed[idx] = perturbed[idx] + perturbation_delta

    base_traj = compute_trajectory(
        series, chart_id=chart_id, dt=dt, a=a, b=b, origin=origin
    )
    pert_traj = compute_trajectory(
        perturbed, chart_id=chart_id, dt=dt, a=a, b=b, origin=origin
    )
    base_path = base_traj.get("trajectory") or []
    pert_path = pert_traj.get("trajectory") or []
    residuals: List[float] = []
    for i, (bv, pv) in enumerate(zip(base_path, pert_path)):
        if i >= idx:
            residuals.append(abs(float(pv) - float(bv)))

    recovered = False
    recovery_step: Optional[int] = None
    threshold = 0.05
    for offset, residual in enumerate(residuals):
        if residual <= threshold:
            recovered = True
            recovery_step = idx + offset
            break

    return {
        "ok": True,
        "status": "computed",
        "experiment_id": f"exp-{uuid4().hex[:12]}",
        "chart_id": chart_id,
        "kind": "recovery_after_perturbation",
        "perturbation": {
            "index": idx,
            "delta": perturbation_delta,
        },
        "baseline_trajectory": base_path,
        "perturbed_trajectory": pert_path,
        "residuals_after_perturbation": residuals,
        "recovered": recovered,
        "recovery_step": recovery_step,
        "threshold": threshold,
        "p": None,
        "origin": origin,
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "note": (
            "Deterministic recovery test via FormSpace native scan. "
            "Does not claim attractor proof without live measured evidence."
        ),
    }


def resolve_series_for_chart(
    chart_id: str,
    *,
    series: Optional[Sequence[float]] = None,
    use_demo_fixture: bool = False,
) -> Dict[str, Any]:
    """Resolve input series: explicit observations, demo fixture, or empty."""
    if series is not None and len(list(series)) > 0:
        return {
            "series": list(series),
            "origin": "MEASURED_OR_PROVIDED",
            "source": "request",
        }
    if use_demo_fixture:
        chart = get_atlas().get_chart(chart_id)
        if chart and chart.get("fixture_series"):
            return {
                "series": list(chart["fixture_series"]),
                "origin": "CATALOG_FIXTURE",
                "source": "demo_catalog",
                "provenance": chart.get("provenance"),
                "label": "Demo / catalog",
            }
    return {
        "series": [],
        "origin": "NONE",
        "source": "empty",
        "message": "No live observations and demo fixture not requested.",
    }


def fuse_modality_means(
    means: Sequence[float],
    variances: Sequence[float],
) -> Dict[str, Any]:
    """Inverse-variance fusion for multimodal FormSpace coordinates."""
    if not means or not variances:
        return {
            "ok": False,
            "status": "no_data",
            "fused_mean": None,
            "fused_variance": None,
            "p": None,
        }
    fused_mean, fused_var = inverse_variance_fusion(means, variances)
    return {
        "ok": True,
        "status": "computed",
        "fused_mean": fused_mean,
        "fused_variance": fused_var,
        "p": None,
    }
