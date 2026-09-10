"""NLM → MYCA/AVANI → task proposals. Advisory only. p stays null."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .reference_runtime import load_reference_runtime


def _task(
    task_id: str,
    title: str,
    status: str,
    reason: str,
    endpoint: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "id": task_id,
        "title": title,
        "status": status,
        "reason": reason,
        "endpoint": endpoint,
        "p": None,
        "live": False,
        "executable": status == "PROPOSED",
    }


def _existing_task_endpoints() -> Dict[str, Optional[str]]:
    return {
        "earth_sim": "/api/itdx/situation-assessment",
        "droids": None,
        "mission": "/api/itdx/task8",
        "follow_data": "/api/nlm/observations",
        "assumptions": "/api/nlm/decision-path",
        "theories": "/api/nlm/decision-path",
    }


async def run_decision_path(inputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    runtime = load_reference_runtime()
    replay = runtime.replay()
    endpoints = _existing_task_endpoints()
    tasks: List[Dict[str, Any]] = [
        _task(
            "earth-sim-refresh",
            "Refresh Earth Sim situation assessment",
            "PROPOSED" if endpoints["earth_sim"] else "NOT_SUPPLIED",
            "Existing ITDX situation-assessment. Advisory, live=false.",
            endpoints["earth_sim"],
        ),
        _task(
            "droid-tasking",
            "Task droids / field devices",
            "NOT_SUPPLIED",
            "No live droid/mission execution API bound for this AO.",
            endpoints["droids"],
        ),
        _task(
            "mission-task8",
            "MYCA/AVANI Task 8 COA review",
            "PROPOSED" if endpoints["mission"] else "NOT_SUPPLIED",
            "Existing /api/itdx/task8. Not command authority.",
            endpoints["mission"],
        ),
        _task(
            "follow-data",
            "Follow cited observations",
            "PROPOSED",
            "Use existing NLM observation ledger. Empty/unqualified is allowed.",
            endpoints["follow_data"],
        ),
        _task(
            "assumption",
            "Record assumption: archived checkpoint is SYNTHETIC_TEST",
            "PROPOSED",
            "START_HERE: labels synthetic. Not a six-spectrum foundation model.",
            endpoints["assumptions"],
        ),
        _task(
            "theory",
            "Theory remains unqualified until calibrated forecast weights exist",
            "PROPOSED",
            "Do not treat native replay as Fusarium ecology p.",
            endpoints["theories"],
        ),
    ]
    return {
        "schema": "nlm-decision-path/sep10-2026",
        "summary": "Reference replay produced an advisory decision path. Fusarium p is null.",
        "live": False,
        "synthetic": True,
        "p": None,
        "forecast_qualified": False,
        "training_origin": "SYNTHETIC_TEST",
        "runtime": runtime.runtime_status(),
        "replay": {k: replay.get(k) for k in ("ok", "p", "native_a", "fusion_mean", "chunk_abs_error", "weights_sha256")},
        "myca": {"role": "propose_tasks", "status": "advisory"},
        "avani": {"role": "gate", "path": "/api/avani/status", "command_authority": False},
        "tasks": tasks,
        "inputs": inputs or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
