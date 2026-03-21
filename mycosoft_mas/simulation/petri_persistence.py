"""
Petri simulation persistence - February 20, 2026

Saves/loads Petri simulation state to file and optionally MINDEX.
Provides NLM outcome notification for learning workflows.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_STORAGE_PATH = Path(__file__).resolve().parents[2] / "data" / "petri_simulations.json"


def _serialize_obj(obj: Any) -> Any:
    """Convert objects to JSON-serializable form."""
    if obj is None:
        return None
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, (list, tuple)):
        return [_serialize_obj(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _serialize_obj(v) for k, v in obj.items()}
    if hasattr(obj, "__dataclass_fields__"):
        return _serialize_obj({f: getattr(obj, f) for f in obj.__dataclass_fields__})
    if hasattr(obj, "value"):
        return str(obj.value) if hasattr(obj, "value") else str(obj)
    if isinstance(obj, (str, int, float, bool)):
        return obj
    try:
        return str(obj)
    except Exception:
        return None


def save_simulation_state(
    simulations: Dict[str, Any],
    parameters: Dict[str, Any],
    path: Optional[Path] = None,
    mindex_url: Optional[str] = None,
) -> bool:
    """
    Save simulation state to file and optionally to MINDEX.
    Returns True if file save succeeded.
    """
    path = path or DEFAULT_STORAGE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "simulations": {k: _serialize_obj(v) for k, v in simulations.items()},
        "parameters": {k: _serialize_obj(v) for k, v in parameters.items()},
        "saved_at": datetime.utcnow().isoformat(),
    }

    try:
        with open(path, "w") as f:
            json.dump(payload, f, indent=2)
        logger.debug("Saved Petri simulation state to %s", path)
    except Exception as e:
        logger.error("Failed to save Petri state: %s", e)
        return False

    if mindex_url:
        try:
            import httpx

            r = httpx.post(
                f"{mindex_url.rstrip('/')}/api/simulations/petri/save",
                json=payload,
                timeout=10.0,
            )
            if r.status_code != 200:
                logger.warning("MINDEX petri save returned %s", r.status_code)
        except Exception as e:
            logger.debug("MINDEX petri save not available: %s", e)

    return True


def load_simulation_state(
    path: Optional[Path] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Load simulation state from file.
    Returns (simulations_dict, parameters_dict).
    Values are raw dicts; agent reconstructs objects as needed.
    """
    path = path or DEFAULT_STORAGE_PATH
    if not path.exists():
        return {}, {}

    try:
        with open(path) as f:
            data = json.load(f)
        sims = data.get("simulations", {})
        params = data.get("parameters", {})
        return sims, params
    except Exception as e:
        logger.error("Failed to load Petri state: %s", e)
        return {}, {}


# --- Audit trail for autonomous/agent actions ---
_audit_log: List[Dict[str, Any]] = []
MAX_AUDIT_ENTRIES = 500


def log_petri_agent_action(
    action: str,
    source: str,
    params: Dict[str, Any],
    result: Optional[Dict[str, Any]] = None,
) -> None:
    """Append an audit entry for MYCA/agent-driven Petri actions."""
    entry = {
        "ts": datetime.utcnow().isoformat(),
        "action": action,
        "source": source,
        "params": params,
        "result_summary": {
            k: v for k, v in (result or {}).items() if k in ("status", "error", "iterations")
        }
        or None,
    }
    _audit_log.append(entry)
    if len(_audit_log) > MAX_AUDIT_ENTRIES:
        _audit_log.pop(0)
    logger.info("Petri agent action: %s from %s", action, source)


def get_petri_audit_trail(limit: int = 50) -> List[Dict[str, Any]]:
    """Return recent audit entries (newest first)."""
    return list(reversed(_audit_log[-limit:]))


async def notify_nlm_petri_outcome(
    session_id: str,
    outcome_type: str,
    summary: Dict[str, Any],
    metrics: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Notify NLM workflow bridge of a Petri simulation outcome for learning.
    outcome_type: 'simulation_complete' | 'calibration_complete' | 'batch_complete'
    """
    try:
        from mycosoft_mas.nlm.workflow_bridge import trigger_workflow_from_nlm

        result = await trigger_workflow_from_nlm(
            "petri_outcome_ingest",
            {
                "session_id": session_id,
                "outcome_type": outcome_type,
                "summary": summary,
                "metrics": metrics or {},
            },
        )
        return result
    except Exception as e:
        logger.warning("NLM petri outcome notify failed: %s", e)
        return {"status": "error", "message": str(e)}
