"""
Proactive error scanner for MYCA Autonomous Self-Healing.

Periodically scans for errors in agent work cycles, MAS health, and known
log locations. Dispatches auto-fixable errors to ErrorTriageService.

Usage:
  python scripts/proactive_error_scanner.py           # one-shot scan
  python scripts/proactive_error_scanner.py --watch   # background loop (every 5 min)

Optional env:
  MAS_API_URL                 default http://192.168.0.188:8001
  N8N_AUTONOMOUS_FIX_WEBHOOK  for dispatch (or triage will skip dispatch)
  PROACTIVE_SCAN_INTERVAL     seconds between scans in watch mode (default 300)
  PROACTIVE_SCAN_DATA_DIR     path to data/agent_work (default data/agent_work)

Author: MYCA / Autonomous Self-Healing Plan
Created: February 2026
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure MAS package is importable
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

MAS_URL = os.environ.get("MAS_API_URL", "http://192.168.0.188:8001").rstrip("/")
SCAN_INTERVAL = int(os.environ.get("PROACTIVE_SCAN_INTERVAL", "300"))
_data_dir = os.environ.get("PROACTIVE_SCAN_DATA_DIR", "")
DATA_DIR = Path(_data_dir) if _data_dir else REPO_ROOT / "data" / "agent_work" / "cycles"
if not DATA_DIR.is_absolute():
    DATA_DIR = (REPO_ROOT / DATA_DIR).resolve()

# Patterns that indicate an error in cycle JSON
ERROR_PATTERNS = [
    (re.compile(r"'dict' object has no attribute '\w+'"), "AttributeError"),
    (re.compile(r"AttributeError"), "AttributeError"),
    (re.compile(r"ModuleNotFoundError"), "ModuleNotFoundError"),
    (re.compile(r"TypeError"), "TypeError"),
    (re.compile(r"KeyError"), "KeyError"),
    (re.compile(r"connection refused|ECONNREFUSED"), "ConnectionError"),
]


def _find_errors_in_cycles(cycles_dir: Path, max_age_hours: int = 24) -> List[Dict[str, Any]]:
    """Scan agent work cycle JSON files for error strings."""
    found: List[Dict[str, Any]] = []
    if not cycles_dir.exists():
        return found

    cutoff = time.time() - (max_age_hours * 3600)
    for f in sorted(cycles_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        if f.stat().st_mtime < cutoff:
            break
        try:
            data = json.loads(f.read_text(encoding="utf-8", errors="replace"))
            text = json.dumps(data)
            for pat, err_type in ERROR_PATTERNS:
                m = pat.search(text)
                if m:
                    found.append({
                        "file": str(f),
                        "error_type": err_type,
                        "snippet": m.group(0)[:200],
                        "mtime": f.stat().st_mtime,
                    })
                    break
        except Exception as e:
            logger.debug("Could not parse %s: %s", f, e)
    return found


async def _check_mas_health() -> Optional[str]:
    """Check MAS health endpoint; return error string if unhealthy."""
    try:
        import httpx

        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{MAS_URL}/health")
            if r.status_code != 200:
                return f"MAS health returned {r.status_code}: {r.text[:200]}"
            j = r.json()
            if isinstance(j, dict) and j.get("status") != "healthy":
                return f"MAS unhealthy: {json.dumps(j)[:200]}"
            return None
    except Exception as e:
        return str(e)[:200]


async def _run_scan() -> int:
    """Run one scan cycle; return count of errors dispatched."""
    from mycosoft_mas.services.error_triage_service import get_error_triage_service

    triage = get_error_triage_service()
    dispatched = 0

    # 1. Scan agent work cycles
    cycles = _find_errors_in_cycles(DATA_DIR)
    for c in cycles[:10]:  # Limit to avoid flood
        msg = f"{c['error_type']}: {c['snippet']}"
        result = await triage.triage(
            msg,
            source="proactive_scanner",
            context={"file": c["file"], "snippet": c["snippet"]},
        )
        if result.feasibility.value == "auto_fixable":
            dispatched += 1
            logger.info("Dispatched auto-fix for: %s", c["snippet"][:80])

    # 2. MAS health
    health_err = await _check_mas_health()
    if health_err:
        result = await triage.triage(
            health_err,
            source="proactive_scanner",
            context={"check": "mas_health"},
        )
        if result.feasibility.value == "auto_fixable":
            dispatched += 1

    return dispatched


async def _watch_loop() -> None:
    """Run scan in a loop."""
    logger.info("Proactive error scanner started (interval=%ds)", SCAN_INTERVAL)
    while True:
        try:
            n = await _run_scan()
            if n:
                logger.info("Dispatched %d auto-fix requests this cycle", n)
        except Exception as e:
            logger.exception("Scan failed: %s", e)
        await asyncio.sleep(SCAN_INTERVAL)


def main() -> int:
    parser = argparse.ArgumentParser(description="Proactive error scanner for MYCA")
    parser.add_argument("--watch", action="store_true", help="Run in background loop")
    args = parser.parse_args()

    if args.watch:
        asyncio.run(_watch_loop())
        return 0

    n = asyncio.run(_run_scan())
    logger.info("One-shot scan complete; dispatched %d auto-fix requests", n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
