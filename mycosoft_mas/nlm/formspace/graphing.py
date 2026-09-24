"""FormSpace graphing: export real series from engine jobs for UI charts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence
from uuid import uuid4

from .dynamics import compute_trajectory, resolve_series_for_chart


def build_graph_payload(
    *,
    chart_id: str,
    series: Optional[Sequence[float]] = None,
    use_demo_fixture: bool = False,
    graph_kind: str = "trajectory",
    dt: float = 0.1,
    a: float = -0.5,
    b: float = 1.0,
) -> Dict[str, Any]:
    """Build graph series from FormSpace engine (never fabricated metrics)."""
    resolved = resolve_series_for_chart(
        chart_id, series=series, use_demo_fixture=use_demo_fixture
    )
    input_series = resolved.get("series") or []
    if not input_series:
        return {
            "ok": False,
            "status": "no_data",
            "graph_id": f"graph-{uuid4().hex[:12]}",
            "chart_id": chart_id,
            "kind": graph_kind,
            "points": [],
            "message": (
                "No series available. Provide observations or request "
                "demo fixture replay for a catalog chart."
            ),
            "p": None,
            "live": False,
        }

    traj = compute_trajectory(
        input_series,
        chart_id=chart_id,
        dt=dt,
        a=a,
        b=b,
        origin=str(resolved.get("origin") or "UNKNOWN"),
    )
    trajectory = traj.get("trajectory") or []
    points: List[Dict[str, Any]] = []
    for i, (raw, state) in enumerate(zip(input_series, trajectory)):
        points.append(
            {
                "t": i,
                "input": float(raw),
                "state": float(state),
            }
        )

    return {
        "ok": True,
        "status": "computed",
        "graph_id": f"graph-{uuid4().hex[:12]}",
        "chart_id": chart_id,
        "kind": graph_kind,
        "origin": resolved.get("origin"),
        "source": resolved.get("source"),
        "label": resolved.get("label"),
        "provenance": resolved.get("provenance"),
        "points": points,
        "final_state": traj.get("final_state"),
        "params": traj.get("params"),
        "p": None,
        "live": resolved.get("origin") == "MEASURED_OR_PROVIDED",
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "note": "Series from FormSpace engine native scan. Not mock UI filler.",
    }
