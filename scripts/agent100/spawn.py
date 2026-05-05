"""
Run Agent100 harness cycles — MAY03_2026.

Examples:
  python scripts/agent100/spawn.py --wave1 --mode health
  python scripts/agent100/spawn.py --limit 3 --mode health
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from mycosoft_mas.agent100.archetypes import build_agent
from mycosoft_mas.agent100.config_loader import load_agents, save_stub_matrix
from mycosoft_mas.agent100.constants import AGENT100_DATA_DIR
from mycosoft_mas.agent100.persistence import persist_calls
from mycosoft_mas.agent100.supervisor import Agent100Supervisor


def _halted() -> bool:
    state_path = AGENT100_DATA_DIR / "STATE.json"
    if not state_path.exists():
        return False
    try:
        st = json.loads(state_path.read_text(encoding="utf-8"))
        return bool(st.get("halted"))
    except Exception:
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="health", help="singular|multi|grouped|all_bundle|health|...")
    ap.add_argument("--wave1", action="store_true", help="First 10 agents only")
    ap.add_argument("--wave2", action="store_true", help="First 50 agents")
    ap.add_argument("--wave3", action="store_true", help="All agents")
    ap.add_argument("--limit", type=int, default=0, help="Max agents (0 = no extra cap)")
    args = ap.parse_args()

    if _halted():
        print("Agent100 halted (data/agent100/STATE.json). Clear halted or run kill_all reset manually.", file=sys.stderr)
        return 2

    save_stub_matrix()
    agents = load_agents()
    if not agents:
        print("No agents in matrix.", file=sys.stderr)
        return 1

    if args.wave1:
        agents = agents[:10]
    elif args.wave2:
        agents = agents[:50]
    elif args.wave3:
        pass
    if args.limit and args.limit > 0:
        agents = agents[: args.limit]

    AGENT100_DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = AGENT100_DATA_DIR / "calls.jsonl"
    sup = Agent100Supervisor()
    total = 0
    for row in agents:
        if not sup.acquire_request_slot(row.id, timeout_s=180.0):
            print(f"Rate limit timeout for fleet/agent {row.id}", file=sys.stderr)
            continue
        agent = build_agent(row)
        try:
            recs = agent.run_cycle(args.mode)
        finally:
            agent.close()
        for r in recs:
            line = json.dumps(asdict(r), default=str)
            with out_path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        persist_calls(recs)
        total += len(recs)
    print(f"Recorded {total} call rows -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
