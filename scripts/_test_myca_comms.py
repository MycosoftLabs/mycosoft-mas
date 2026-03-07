#!/usr/bin/env python3
"""
MYCA Communication Verification — Tests all channels and MYCA OS on VM 191.

Verifies:
- MYCA Gateway health (port 8100)
- Channel status (Slack, Asana, Discord, Signal, WhatsApp)
- Message send (POST /message) — optional
- MAS/MINDEX connectivity

Usage:
    python scripts/_test_myca_comms.py
    python scripts/_test_myca_comms.py --gateway http://192.168.0.191:8100

Date: 2026-03-06
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


async def test_gateway_health(base_url: str) -> dict:
    """Test GET /health."""
    import aiohttp
    url = f"{base_url.rstrip('/')}/health"
    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                data = await r.json()
                healthy = data.get("healthy", False) or data.get("status") in ("ok", "healthy")
                return {
                    "pass": r.status == 200 and healthy,
                    "status": r.status,
                    "data": data,
                    "error": None,
                }
    except Exception as e:
        return {"pass": False, "status": 0, "data": {}, "error": str(e)}


async def test_channels(base_url: str) -> dict:
    """Test GET /channels."""
    import aiohttp
    url = f"{base_url.rstrip('/')}/channels"
    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.get(url, timeout=aiohttp.ClientTimeout(total=15)) as r:
                data = await r.json()
                channels = data.get("channels") or {}
                passed = sum(1 for c in channels.values() if c.get("connected") or c.get("status") == "connected")
                return {
                    "pass": r.status == 200,
                    "status": r.status,
                    "data": data,
                    "connected_count": passed,
                    "total": len(channels),
                    "error": None,
                }
    except Exception as e:
        return {"pass": False, "status": 0, "data": {}, "connected_count": 0, "total": 0, "error": str(e)}


async def test_message(base_url: str, api_key: str | None) -> dict:
    """Test POST /message (optional, requires gateway API key if set)."""
    import aiohttp
    url = f"{base_url.rstrip('/')}/message"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        headers["X-API-Key"] = api_key
    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.post(
                url,
                json={"content": "Comms verification test. Ignore.", "source": "test"},
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as r:
                # 200 or 202 accepted
                ok = r.status in (200, 202)
                try:
                    data = await r.json()
                except Exception:
                    data = {"raw": await r.text()}
                return {"pass": ok, "status": r.status, "data": data, "error": None}
    except Exception as e:
        return {"pass": False, "status": 0, "data": {}, "error": str(e)}


async def test_mas() -> dict:
    """Test MAS health."""
    import aiohttp
    url = os.getenv("MAS_API_URL", "http://192.168.0.188:8001") + "/health"
    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.get(url, timeout=aiohttp.ClientTimeout(total=5)) as r:
                data = await r.json() if r.content_type == "application/json" else {}
                return {"pass": r.status == 200, "status": r.status, "error": None}
    except Exception as e:
        return {"pass": False, "status": 0, "error": str(e)}


async def test_mindex() -> dict:
    """Test MINDEX health."""
    import aiohttp
    url = os.getenv("MINDEX_API_URL", "http://192.168.0.189:8000") + "/health"
    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.get(url, timeout=aiohttp.ClientTimeout(total=5)) as r:
                return {"pass": r.status == 200, "status": r.status, "error": None}
    except Exception as e:
        return {"pass": False, "status": 0, "error": str(e)}


async def main():
    parser = argparse.ArgumentParser(description="MYCA Comms Verification")
    parser.add_argument("--gateway", default="http://192.168.0.191:8100", help="MYCA Gateway URL")
    parser.add_argument("--skip-message", action="store_true", help="Skip POST /message test")
    parser.add_argument("-q", "--quiet", action="store_true", help="Minimal output")
    args = parser.parse_args()

    base = args.gateway
    api_key = os.getenv("MYCA_GATEWAY_API_KEY", "")

    results = {}
    print("MYCA Communication Verification")
    print("=" * 50)

    # 1. Gateway health
    r = await test_gateway_health(base)
    results["gateway_health"] = r
    status = "PASS" if r["pass"] else "FAIL"
    print(f"  Gateway /health: {status} (HTTP {r['status']})")
    if r.get("data", {}).get("services"):
        for ch, connected in r["data"]["services"].items():
            print(f"    - {ch}: {'connected' if connected else 'not connected'}")
    if r.get("error"):
        print(f"    Error: {r['error']}")

    # 2. Channels
    r = await test_channels(base)
    results["channels"] = r
    status = "PASS" if r["pass"] else "FAIL"
    print(f"  Gateway /channels: {status} ({r.get('connected_count', 0)}/{r.get('total', 0)} connected)")
    if r.get("data", {}).get("channels"):
        for ch, info in r["data"]["channels"].items():
            s = info.get("status", "?")
            msg = info.get("message", "")
            print(f"    - {ch}: {s} {f'({msg[:40]})' if msg else ''}")
    if r.get("error"):
        print(f"    Error: {r['error']}")

    # 3. Message (optional)
    if not args.skip_message:
        r = await test_message(base, api_key or None)
        results["message"] = r
        status = "PASS" if r["pass"] else "FAIL"
        print(f"  Gateway POST /message: {status} (HTTP {r['status']})")
        if r.get("error"):
            print(f"    Error: {r['error']}")

    # 4. MAS
    r = await test_mas()
    results["mas"] = r
    status = "PASS" if r["pass"] else "FAIL"
    print(f"  MAS health: {status}")

    # 5. MINDEX
    r = await test_mindex()
    results["mindex"] = r
    status = "PASS" if r["pass"] else "FAIL"
    print(f"  MINDEX health: {status}")

    print("=" * 50)
    passed = sum(1 for v in results.values() if isinstance(v, dict) and v.get("pass"))
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")

    if passed < total:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
