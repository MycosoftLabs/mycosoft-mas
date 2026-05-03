"""
Append-only JSONL for agent activity (May 02, 2026).

Used by MYCA Alive Phase 1D: visibility when agents run (non-zero activity).
File: myca/event_ledger/agent_activity.jsonl (rotated by size in future).
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_LEDGER: Optional[Path] = None


def _ledger_path() -> Path:
    global _LEDGER
    if _LEDGER is None:
        _LEDGER = Path(__file__).parent / "agent_activity.jsonl"
    return _LEDGER


def log_agent_activity(
    agent_id: str,
    action: str,
    *,
    source: str = "mas",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Append one activity line. Returns the logged record."""
    record = {
        "ts": int(time.time()),
        "ts_iso": datetime.now(timezone.utc).isoformat(),
        "agent_id": agent_id,
        "action": action,
        "source": source,
        "metadata": metadata or {},
    }
    path = _ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")
    return record


def read_recent_lines(max_lines: int = 200) -> List[Dict[str, Any]]:
    """Read up to the last N JSONL records (best-effort)."""
    path = _ledger_path()
    if not path.exists():
        return []
    lines: List[str] = []
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return []
    out: List[Dict[str, Any]] = []
    for line in lines[-max_lines:]:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out
