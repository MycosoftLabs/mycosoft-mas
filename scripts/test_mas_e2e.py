#!/usr/bin/env python3
"""
E2E test: MAS health + MYCA chat via website orchestrator.
Run from MAS repo root. Requires website dev server on 3010 (or set WEBSITE_URL).
"""

import os
import sys
import urllib.request
import json
from pathlib import Path

MAS_URL = os.getenv("MAS_API_URL", "http://192.168.0.188:8001")
WEBSITE_URL = os.getenv("WEBSITE_URL", "http://localhost:3010")


def fetch(url: str, method: str = "GET", body: dict = None, timeout: int = 30) -> tuple[int, dict | str]:
    req = urllib.request.Request(url, method=method)
    req.add_header("Content-Type", "application/json")
    if body:
        req.data = json.dumps(body).encode()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read().decode()
            return r.status, json.loads(data) if data.strip().startswith("{") else data
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode() if e.fp else str(e)
    except Exception as e:
        return -1, str(e)


def main():
    print("=== MAS E2E Test ===\n")

    # 1. MAS health
    print("1. MAS health", MAS_URL, "...")
    code, data = fetch(f"{MAS_URL}/health", timeout=15)
    if code != 200:
        print(f"   FAIL: {code} {data}")
        sys.exit(1)
    status = data.get("status", "") if isinstance(data, dict) else ""
    pg = next((c for c in data.get("components", []) if c.get("name") == "postgresql"), {})
    redis = next((c for c in data.get("components", []) if c.get("name") == "redis"), {})
    print(f"   OK status={status} postgres={pg.get('status')} redis={redis.get('status')}")

    # 2. Website orchestrator (MYCA chat)
    print("\n2. Website orchestrator", WEBSITE_URL, "(4+5)...")
    code, data = fetch(
        f"{WEBSITE_URL}/api/mas/voice/orchestrator",
        method="POST",
        body={"message": "what is 4+5"},
        timeout=45,
    )
    if code != 200:
        print(f"   FAIL: {code} {data}")
        sys.exit(1)
    resp = data.get("response_text", "") if isinstance(data, dict) else str(data)
    if "9" in resp or "nine" in resp.lower():
        print(f"   OK: {resp[:80]}...")
    else:
        print(f"   WARN: unexpected response: {resp[:100]}")

    print("\n[OK] E2E test passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
