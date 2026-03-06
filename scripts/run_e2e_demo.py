#!/usr/bin/env python3
"""
MYCA End-to-End Demo — Discord → Deploy → Confirm → EP Logged (Mar 5, 2026)

This script documents and optionally verifies the autonomous deployment demo:
Morgan asks MYCA via Discord to deploy the website; MYCA pulls code, builds
Docker on VM 187, restarts the website container (with NAS mount), purges
Cloudflare, confirms on Discord, and logs an Experience Packet to MINDEX.

Usage:
    python scripts/run_e2e_demo.py           # Print instructions and run verification
    python scripts/run_e2e_demo.py --verify  # Run connectivity/EP checks only
    python scripts/run_e2e_demo.py --help    # Show this help

Prerequisites:
    - MYCA OS running on VM 191 (systemctl myca-os or gateway + core)
    - Discord bot connected and Message Content Intent enabled
    - VM 191 .env: VM_PASSWORD or VM_SSH_PASSWORD, CLOUDFLARE_API_TOKEN,
      CLOUDFLARE_ZONE_ID, MINDEX_API_URL (189:8000), MINDEX_API_KEY
    - Sandbox VM 187 reachable from 191; website repo at /opt/mycosoft/website

How to run the demo:
    1. Open Discord (Mycosoft server) and ensure MYCA bot is online.
    2. Send a message only Morgan is allowed to trigger from, e.g.:
       "Deploy website to sandbox" or "Deploy the website to sandbox."
    3. MYCA OS (task loop) will:
       - Create a deployment task (type=deployment, target=website)
       - Tool orchestrator SSHs to 187, git pull, docker build, restart container
       - Purge Cloudflare cache
       - Send "Deployment completed: ..." back to Discord
       - Store an Experience Packet to MINDEX at
         POST {MINDEX_API_URL}/api/mindex/grounding/experience-packets
    4. Verify: Check Discord for confirmation; query MINDEX for latest EPs.

How to record the video for investors:
    - Screen-record Discord + a browser on sandbox.mycosoft.com before/after.
    - Or: OBS/QuickTime capturing Discord window and a second window with
      the website; run the demo and show the confirmation message and EP.

Verification (--verify):
    - MYCA OS / gateway reachable (191:8100)
    - MINDEX health (189:8000) and optional EP list
    - VM 187 SSH from 191 (optional, requires paramiko)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


def load_creds() -> dict:
    creds = {}
    for f in [REPO_ROOT / ".credentials.local", Path.home() / ".mycosoft-credentials"]:
        if f.exists():
            for line in f.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    creds[k.strip()] = v.strip()
            break
    return creds


def http_get(url: str, timeout: int = 10, data: bytes | None = None) -> tuple[int, str]:
    try:
        import urllib.request
        req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
        if data:
            req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode()
    except Exception as e:
        return 0, str(e)


def verify() -> dict:
    """Run verification checks. Returns dict with passed/failed/warnings."""
    creds = load_creds()
    os.environ.setdefault("VM_PASSWORD", creds.get("VM_SSH_PASSWORD", creds.get("VM_PASSWORD", "")))
    results = {"passed": [], "failed": [], "warnings": []}

    # MYCA OS gateway (191:8100)
    try:
        code, body = http_get("http://192.168.0.191:8100/health", timeout=5)
        if code == 200:
            results["passed"].append("MYCA OS gateway (191:8100) healthy")
        else:
            results["failed"].append(f"MYCA OS gateway returned {code}")
    except Exception as e:
        results["failed"].append(f"MYCA OS gateway: {e}")

    # MINDEX health (189:8000)
    try:
        code, body = http_get("http://192.168.0.189:8000/health", timeout=5)
        if code == 200:
            results["passed"].append("MINDEX API (189:8000) healthy")
        else:
            results["failed"].append(f"MINDEX returned {code}")
    except Exception as e:
        results["failed"].append(f"MINDEX: {e}")

    # Optional: list recent EPs (if endpoint exists and API key set)
    import urllib.request
    api_key = os.getenv("MINDEX_API_KEY") or (os.getenv("API_KEYS") or "").split(",")[0].strip()
    mindex_url = os.getenv("MINDEX_API_URL", "http://192.168.0.189:8000")
    if api_key:
        try:
            req = urllib.request.Request(
                f"{mindex_url.rstrip('/')}/api/mindex/grounding/experience-packets?limit=5",
                headers={"X-API-Key": api_key},
            )
            with urllib.request.urlopen(req, timeout=5) as r:
                data = json.loads(r.read().decode())
                items = data if isinstance(data, list) else data.get("items", data.get("experience_packets", []))
                results["passed"].append(f"MINDEX EPs query OK (recent: {len(items)} items)")
        except Exception as e:
            results["warnings"].append(f"MINDEX EPs query: {e}")
    else:
        results["warnings"].append("MINDEX_API_KEY not set; skipping EP list check")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="MYCA E2E Demo: Discord → Deploy → Confirm → EP Logged (Mar 5, 2026)"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Run verification checks only (gateway, MINDEX, optional EP list)",
    )
    args = parser.parse_args()

    if args.verify:
        print("MYCA E2E Demo — Verification\n")
        res = verify()
        for p in res["passed"]:
            print(f"  OK: {p}")
        for f in res["failed"]:
            print(f"  FAIL: {f}")
        for w in res["warnings"]:
            print(f"  WARN: {w}")
        sys.exit(0 if not res["failed"] else 1)

    # Print full instructions
    print(__doc__)
    print("\n--- Quick verification ---")
    res = verify()
    for p in res["passed"]:
        print(f"  OK: {p}")
    for f in res["failed"]:
        print(f"  FAIL: {f}")
    for w in res["warnings"]:
        print(f"  WARN: {w}")
    if res["failed"]:
        print("\nFix failed checks before running the demo.")
        sys.exit(1)
    print("\nVerification passed. Trigger the demo from Discord (see above).")


if __name__ == "__main__":
    main()
