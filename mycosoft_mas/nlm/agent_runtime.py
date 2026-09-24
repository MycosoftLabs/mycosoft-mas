"""
NLM agent runtime — task hooks for FormSpace/NLM UI AgentControlCenter.

Dispatches real MAS domain tasks when available; otherwise records durable
task events (empty completion when agents offline). No mock metrics.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from mycosoft_mas.nlm.training_store import _append, _read_jsonl, changelog

logger = logging.getLogger(__name__)

ALLOWED_TASK_TYPES = {
    "ingest_refresh",
    "train_status",
    "attest_artifact",
    "formspace_eval",
    "security_scan",
    "grounding_check",
    "device_map",
}


def list_tasks(*, limit: int = 50) -> Dict[str, Any]:
    from mycosoft_mas.nlm.training_store import _ensure

    root = _ensure()
    path = root / "agent_tasks.jsonl"
    if not path.exists():
        path.write_text("", encoding="utf-8")
    rows = _read_jsonl("agent_tasks.jsonl", limit=limit)
    return {
        "status": "ok",
        "empty": len(rows) == 0,
        "count": len(rows),
        "tasks": rows,
        "allowed_task_types": sorted(ALLOWED_TASK_TYPES),
        "message": None if rows else "No agent tasks yet.",
        "model_kind": "nature_learning_model",
    }


async def submit_task(
    *,
    task_type: str,
    payload: Optional[Dict[str, Any]] = None,
    requested_by: Optional[str] = None,
) -> Dict[str, Any]:
    if task_type not in ALLOWED_TASK_TYPES:
        raise ValueError(f"unsupported_task_type:{task_type}")

    task_id = f"nlm_task_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    task: Dict[str, Any] = {
        "task_id": task_id,
        "task_type": task_type,
        "status": "accepted",
        "requested_by": requested_by or "nlm-ui",
        "payload": payload or {},
        "created_at": now,
        "updated_at": now,
        "result": None,
        "model_kind": "nature_learning_model",
        "bound_to_ollama": False,
    }

    # Execute lightweight real hooks inline; heavy work stays async via domain hooks
    result: Dict[str, Any] = {}
    try:
        if task_type == "ingest_refresh":
            from mycosoft_mas.nlm.device_ingest import build_live_ingest

            result = await build_live_ingest(fetch_telemetry=True)
            task["status"] = "completed"
        elif task_type == "train_status":
            from mycosoft_mas.nlm.training_store import latest_run

            result = latest_run()
            task["status"] = "completed"
        elif task_type == "security_scan":
            from mycosoft_mas.nlm.security_hooks import scan_nlm_security

            result = scan_nlm_security()
            task["status"] = "completed"
        elif task_type == "device_map":
            from mycosoft_mas.nlm.device_ingest import build_device_protocol_map

            result = await build_device_protocol_map()
            task["status"] = "completed"
        elif task_type == "grounding_check":
            from mycosoft_mas.nlm.training_store import list_grounding

            result = list_grounding(limit=20)
            task["status"] = "completed"
        elif task_type == "attest_artifact":
            from mycosoft_mas.nlm.training_store import persist_grounding

            result = await persist_grounding(payload or {"type": "agent_attest", "ts": now})
            task["status"] = "completed"
        elif task_type == "formspace_eval":
            from mycosoft_mas.nlm.formspace.engine import get_formspace_engine

            result = get_formspace_engine().health()
            task["status"] = "completed"
        else:
            task["status"] = "accepted"
            try:
                from mycosoft_mas.deep_agents.domain_hooks import schedule_domain_task

                schedule_domain_task(
                    domain="nlm",
                    task_type=task_type,
                    payload={"task_id": task_id, **(payload or {})},
                )
                task["status"] = "queued"
            except Exception as exc:
                logger.debug("domain hook unavailable: %s", exc)
                task["status"] = "accepted_no_worker"
                result = {"note": "Task recorded; no domain worker claimed it yet."}
    except Exception as exc:
        logger.exception("NLM agent task failed")
        task["status"] = "error"
        result = {"error": str(exc)}

    task["result"] = result
    task["updated_at"] = datetime.now(timezone.utc).isoformat()
    _append("agent_tasks.jsonl", task)
    changelog(
        entity_type="agent_task",
        entity_id=task_id,
        action=task["status"],
        detail={"task_type": task_type},
    )
    return {"ok": True, "task": task}


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    for row in list_tasks(limit=500).get("tasks") or []:
        if row.get("task_id") == task_id:
            return row
    return None
