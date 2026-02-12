#!/usr/bin/env python3
"""
Full MYCA Consciousness Integration Test
Run against MAS VM (192.168.0.188:8001) or local (http://localhost:8001).
Usage: python scripts/test_myca_consciousness_full.py [--base-url http://192.168.0.188:8001]
Created: February 10, 2026
"""

import argparse
import asyncio
import json
import sys
from typing import Any, Dict, Optional

try:
    import httpx
except ImportError:
    print("Install httpx: pip install httpx")
    sys.exit(1)

DEFAULT_BASE = "http://192.168.0.188:8001"


async def get(client: httpx.AsyncClient, base: str, path: str) -> Dict[str, Any]:
    """GET and return JSON or error dict."""
    try:
        r = await client.get(f"{base}{path}", timeout=15.0)
        return {"status": r.status_code, "body": r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text}
    except Exception as e:
        return {"status": -1, "error": str(e)}


async def post(client: httpx.AsyncClient, base: str, path: str, json_body: Optional[Dict] = None) -> Dict[str, Any]:
    """POST and return JSON or error dict."""
    try:
        r = await client.post(f"{base}{path}", json=json_body or {}, timeout=30.0)
        return {"status": r.status_code, "body": r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text}
    except Exception as e:
        return {"status": -1, "error": str(e)}


def ok(res: Dict[str, Any], status_ok: int = 200) -> bool:
    return res.get("status") == status_ok


def run_test(name: str, passed: bool, detail: str = "") -> None:
    symbol = "PASS" if passed else "FAIL"
    print(f"  [{symbol}] {name}" + (f" - {detail}" if detail else ""))


async def main(base_url: str) -> int:
    base = base_url.rstrip("/")
    print("=" * 60)
    print("MYCA CONSCIOUSNESS FULL INTEGRATION TEST")
    print(f"Base URL: {base}")
    print("=" * 60)

    failures = 0
    async with httpx.AsyncClient() as client:
        # 1. MAS health
        res = await get(client, base, "/health")
        run_test("MAS /health", ok(res), str(res.get("body", res.get("error")))[:80])
        if not ok(res):
            failures += 1
            print("  Cannot continue without MAS health. Is the VM reachable?")
            return failures

        # 2. MYCA consciousness health
        res = await get(client, base, "/api/myca/health")
        run_test("MYCA /api/myca/health", ok(res), str(res.get("body", res.get("error")))[:80])
        if not ok(res):
            failures += 1

        # 3. MYCA status (awake/sleeping)
        res = await get(client, base, "/api/myca/status")
        run_test("MYCA /api/myca/status", ok(res), str(res.get("body", res.get("error")))[:80])
        if not ok(res):
            failures += 1
        else:
            body = res.get("body") or {}
            if isinstance(body, dict):
                print(f"      status={body.get('status')}, is_conscious={body.get('is_conscious')}")

        # 4. Awaken (idempotent)
        res = await post(client, base, "/api/myca/awaken")
        run_test("MYCA /api/myca/awaken", ok(res), str(res.get("body", res.get("error")))[:80])
        if not ok(res):
            failures += 1

        # 5. Identity
        res = await get(client, base, "/api/myca/identity")
        run_test("MYCA /api/myca/identity", ok(res), "")
        if ok(res) and isinstance(res.get("body"), dict):
            name = (res["body"].get("name") or res["body"].get("identity", {}).get("name")) or "?"
            print(f"      name={name}")
        elif not ok(res):
            failures += 1

        # 6. Soul summary
        res = await get(client, base, "/api/myca/soul")
        run_test("MYCA /api/myca/soul", ok(res), "")
        if not ok(res):
            failures += 1

        # 7. Chat (non-streaming)
        res = await post(client, base, "/api/myca/chat", json_body={"message": "Hello MYCA, say your name in one short sentence.", "session_id": "test-session-1"})
        run_test("MYCA /api/myca/chat", ok(res), "")
        if ok(res) and isinstance(res.get("body"), dict):
            msg = (res["body"].get("message") or "")[:120]
            print(f"      reply: {msg}...")
        elif not ok(res):
            failures += 1
            print(f"      error: {res.get('body') or res.get('error')}")

        # 8. World state (may be empty if sensors not connected)
        res = await get(client, base, "/api/myca/world")
        run_test("MYCA /api/myca/world", ok(res), "")
        if not ok(res):
            failures += 1

        # 9. Emotions
        res = await get(client, base, "/api/myca/emotions")
        run_test("MYCA /api/myca/emotions", ok(res), "")
        if not ok(res):
            failures += 1
    print("=" * 60)
    print(f"Result: {failures} failure(s)")
    return failures


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Full MYCA consciousness test")
    p.add_argument("--base-url", default=DEFAULT_BASE, help="MAS base URL")
    args = p.parse_args()
    exit_code = asyncio.run(main(args.base_url))
    sys.exit(min(exit_code, 255))
