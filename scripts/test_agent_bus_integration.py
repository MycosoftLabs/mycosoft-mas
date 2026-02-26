#!/usr/bin/env python3
"""
Agent Bus Integration Test - February 9, 2026

Verifies Agent Bus WebSocket and related endpoints when MAS and Redis are available.
Run with: poetry run python scripts/test_agent_bus_integration.py

Requires:
- MAS at http://192.168.0.188:8001 (or MAS_API_URL)
- MYCA_AGENT_BUS_ENABLED=true for WebSocket test
"""

import asyncio
import json
import os
import sys
from typing import Optional

MAS_URL = os.getenv("MAS_API_URL", "http://192.168.0.188:8001")
WS_URL = MAS_URL.replace("http://", "ws://").replace("https://", "wss://") + "/ws/agent-bus"


async def test_health() -> bool:
    """Verify MAS health."""
    try:
        import aiohttp
        async with aiohttp.ClientSession() as sess:
            async with sess.get(f"{MAS_URL}/health") as r:
                if r.status == 200:
                    print("[OK] MAS health")
                    return True
    except ImportError:
        print("[SKIP] aiohttp not installed")
        return False
    except Exception as e:
        print(f"[FAIL] MAS health: {e}")
        return False
    return False


async def test_agent_bus_ws() -> bool:
    """Verify Agent Bus WebSocket when enabled."""
    try:
        import websockets
    except ImportError:
        print("[SKIP] websockets not installed")
        return False

    try:
        async with websockets.connect(WS_URL) as ws:
            await ws.send(json.dumps({
                "agent_id": "integration-test",
                "channels": ["agents:status", "agents:tasks", "agents:tool_calls"],
            }))
            raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(raw)
            if data.get("type") == "connected":
                print("[OK] Agent Bus WebSocket connected")
                return True
            if data.get("type") == "error":
                print(f"[FAIL] Agent Bus: {data.get('payload', {}).get('message', data)}")
                return False
    except Exception as e:
        err = str(e)
        if "4003" in err or "disabled" in err.lower():
            print("[SKIP] Agent Bus disabled (MYCA_AGENT_BUS_ENABLED)")
        elif "refused" in err.lower() or "connect" in err.lower():
            print(f"[SKIP] Cannot connect to {WS_URL}: {e}")
        else:
            print(f"[FAIL] Agent Bus: {e}")
        return False
    return False


async def main() -> int:
    print("Agent Bus Integration Test")
    print(f"MAS URL: {MAS_URL}")
    print("-" * 40)

    ok = 0
    if await test_health():
        ok += 1
    if await test_agent_bus_ws():
        ok += 1

    print("-" * 40)
    print(f"Passed: {ok}/2")
    return 0 if ok >= 1 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
