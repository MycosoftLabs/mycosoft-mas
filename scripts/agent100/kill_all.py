"""
Agent100 kill switch — MAY03_2026.

Sets data/agent100/STATE.json → halted; SIGTERM PIDs in data/agent100/pids.json (Unix).
On Windows, uses taskkill /PID for listed PIDs.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_DATA = Path(os.environ.get("AGENT100_DATA_DIR", str(_REPO / "data" / "agent100")))
_STATE = _DATA / "STATE.json"
_PIDS = _DATA / "pids.json"


def main() -> int:
    _DATA.mkdir(parents=True, exist_ok=True)
    state = {"halted": True, "reason": "kill_all", "by": os.environ.get("USER", os.environ.get("USERNAME", "unknown"))}
    _STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(f"Wrote halted state: {_STATE}")

    if not _PIDS.exists():
        print("No pids.json — nothing to terminate.")
        return 0

    try:
        pids = json.loads(_PIDS.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Could not read pids.json: {e}", file=sys.stderr)
        return 1

    raw = pids.get("pids") if isinstance(pids, dict) else pids
    if not isinstance(raw, list):
        print("pids.json format invalid", file=sys.stderr)
        return 1

    for pid in raw:
        try:
            p = int(pid)
        except (TypeError, ValueError):
            continue
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/PID", str(p), "/T", "/F"],
                capture_output=True,
                text=True,
                check=False,
            )
        else:
            try:
                os.kill(p, signal.SIGTERM)
            except ProcessLookupError:
                pass
            except PermissionError as e:
                print(f"PID {p}: {e}", file=sys.stderr)
        print(f"Signaled PID {p}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
