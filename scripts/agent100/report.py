"""
Aggregate calls.jsonl + treasury_ledger.jsonl — MAY03_2026.

Writes data/agent100/summary.json
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from mycosoft_mas.agent100.constants import AGENT100_DATA_DIR


def main() -> int:
    calls_path = AGENT100_DATA_DIR / "calls.jsonl"
    ledger_path = AGENT100_DATA_DIR / "treasury_ledger.jsonl"
    by_agent: Counter[str] = Counter()
    by_status: Counter[str] = Counter()
    latencies: list[int] = []
    if calls_path.exists():
        for line in calls_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                o = json.loads(line)
            except Exception:
                continue
            by_agent[o.get("agent_id", "?")] += 1
            sc = o.get("status_code")
            by_status[str(sc)] += 1
            if isinstance(o.get("latency_ms"), int):
                latencies.append(o["latency_ms"])
    debits = 0
    if ledger_path.exists():
        for line in ledger_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                ev = json.loads(line)
            except Exception:
                continue
            if ev.get("type") == "debit":
                debits += int(ev.get("amount_cents") or 0)
    summary = {
        "calls_total": sum(by_agent.values()),
        "by_agent_top": dict(by_agent.most_common(15)),
        "by_status": dict(by_status),
        "latency_ms_p50": sorted(latencies)[len(latencies) // 2] if latencies else None,
        "treasury_debits_cents": debits,
    }
    out = AGENT100_DATA_DIR / "summary.json"
    AGENT100_DATA_DIR.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(out.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
