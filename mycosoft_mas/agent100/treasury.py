"""In-process treasury ledger for Agent100 (JSONL append-only)."""

from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path
from typing import Any

from mycosoft_mas.agent100.constants import AGENT100_DATA_DIR, global_cap_cents, per_agent_cap_cents

_lock = threading.Lock()
_log = logging.getLogger("mycosoft_mas.agent100.treasury")
_warned_thresholds: set[float] = set()


def _ledger_path() -> Path:
    AGENT100_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return AGENT100_DATA_DIR / "treasury_ledger.jsonl"


def spent_global_cents() -> int:
    p = _ledger_path()
    if not p.exists():
        return 0
    total = 0
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
                if ev.get("type") == "debit" and isinstance(ev.get("amount_cents"), int):
                    total += int(ev["amount_cents"])
            except Exception:
                continue
    return total


def spent_agent_cents(agent_id: str) -> int:
    p = _ledger_path()
    if not p.exists():
        return 0
    total = 0
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
                if ev.get("type") == "debit" and ev.get("agent_id") == agent_id:
                    total += int(ev.get("amount_cents") or 0)
            except Exception:
                continue
    return total


def can_debit(agent_id: str, amount_cents: int) -> tuple[bool, str]:
    if amount_cents <= 0:
        return True, "ok"
    g = global_cap_cents()
    a = per_agent_cap_cents()
    if spent_global_cents() + amount_cents > g:
        return False, "global_cap"
    if spent_agent_cents(agent_id) + amount_cents > a:
        return False, "per_agent_cap"
    return True, "ok"


def debit(agent_id: str, amount_cents: int, ref: str, meta: dict[str, Any] | None = None) -> bool:
    ok, reason = can_debit(agent_id, amount_cents)
    if not ok:
        append_event(
            {
                "type": "reject",
                "reason": reason,
                "agent_id": agent_id,
                "amount_cents": amount_cents,
                "ref": ref,
                "ts": time.time(),
            }
        )
        return False
    append_event(
        {
            "type": "debit",
            "agent_id": agent_id,
            "amount_cents": amount_cents,
            "ref": ref,
            "meta": meta or {},
            "ts": time.time(),
        }
    )
    return True


def append_event(event: dict[str, Any]) -> None:
    with _lock:
        p = _ledger_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, default=str) + "\n")
    if event.get("type") == "debit":
        cap = global_cap_cents()
        if cap > 0:
            ratio = spent_global_cents() / cap
            for threshold, label in ((0.5, "50%"), (0.8, "80%"), (0.95, "95%")):
                if ratio >= threshold and threshold not in _warned_thresholds:
                    _warned_thresholds.add(threshold)
                    _log.warning(
                        "Agent100 treasury crossed %s of global cap (spent=%s cap=%s)",
                        label,
                        spent_global_cents(),
                        cap,
                    )
