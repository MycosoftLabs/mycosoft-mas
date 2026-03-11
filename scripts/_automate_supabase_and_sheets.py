#!/usr/bin/env python3
"""
One-shot automation: Supabase backbone + Google Sheets.

1. Run _setup_supabase_vm188.py (env, creds, MAS restart, n8n sync)
2. Wait for MAS health
3. Trigger spreadsheet sync via POST /api/spreadsheet/sync
4. Report result

Run from MAS repo root:
  python scripts/_automate_supabase_and_sheets.py

Requires: .env (Supabase), .credentials.local (VM), and either
  GOOGLE_SHEETS_CREDENTIALS_JSON or a service account JSON file for Sheets.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import urllib.request

MAS_ROOT = Path(__file__).resolve().parent.parent
SETUP_SCRIPT = MAS_ROOT / "scripts" / "_setup_supabase_vm188.py"
MAS_URL = os.environ.get("MAS_API_URL", "http://192.168.0.188:8001")


def main() -> int:
    print("=== Supabase + Google Sheets Automation ===\n")

    # 1. Run setup
    if not SETUP_SCRIPT.exists():
        print(f"Setup script not found: {SETUP_SCRIPT}")
        return 1
    print("Step 1: Running Supabase backbone setup...")
    r = subprocess.run([sys.executable, str(SETUP_SCRIPT)], cwd=str(MAS_ROOT))
    if r.returncode != 0:
        print("Setup failed. Fix errors above and retry.")
        return r.returncode
    print("Setup completed.\n")

    # 2. Wait for MAS
    print("Step 2: Waiting for MAS to be healthy...")
    for i in range(12):
        try:
            req = urllib.request.Request(f"{MAS_URL}/health", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    print("MAS is healthy.")
                    break
        except Exception:
            pass
        if i < 11:
            time.sleep(5)
            print(f"  Retry {i + 2}/12...")
    else:
        print("MAS did not become healthy. Sync may fail.")
    print()

    # 3. Trigger sync
    print("Step 3: Triggering spreadsheet sync...")
    try:
        req = urllib.request.Request(
            f"{MAS_URL}/api/spreadsheet/sync",
            method="POST",
            headers={"Content-Type": "application/json"},
            data=b"{}",
        )
        with urllib.request.urlopen(req, timeout=130) as resp:
            body = resp.read().decode("utf-8")
            print("Sync response:", body[:500])
            if resp.status == 200:
                print("\nSync completed successfully.")
                return 0
            print("\nSync returned non-200.")
            return 1
    except urllib.error.HTTPError as e:
        print(f"Sync failed: HTTP {e.code}")
        try:
            body = e.read().decode("utf-8")
            print(body[:800])
        except Exception:
            pass
        return 1
    except Exception as e:
        print(f"Sync failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
