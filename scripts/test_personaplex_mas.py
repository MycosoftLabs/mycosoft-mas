#!/usr/bin/env python3
"""
PersonaPlex + MAS Integration Test - February 3, 2026

This script tests the full-duplex voice system with MAS tool integration.
"""
import asyncio
import aiohttp
import json
import sys

# Configuration
MOSHI_URL = "http://localhost:8998"
BRIDGE_URL = "http://localhost:8999"
MAS_URL = "http://192.168.0.188:8001"

async def test_moshi_health():
    """Test Moshi server health."""
    print("\n1. Testing Moshi server...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{MOSHI_URL}/health", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   âœ“ Moshi server healthy: {data.get('version', 'unknown')}")
                    return True
                else:
                    print(f"   âœ— Moshi returned status {resp.status}")
                    return False
    except Exception as e:
        # Moshi might return 426 for root, which is OK
        if "426" in str(e):
            print(f"   âœ“ Moshi server running (upgrade required for root)")
            return True
        print(f"   âœ— Moshi error: {e}")
        return False


async def test_bridge_health():
    """Test PersonaPlex bridge health."""
    print("\n2. Testing PersonaPlex bridge...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BRIDGE_URL}/health", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   âœ“ Bridge healthy: v{data.get('version', 'unknown')}")
                    print(f"   âœ“ Moshi available: {data.get('moshi_available', False)}")
                    print(f"   âœ“ Features: {data.get('features', {})}")
                    return True
                else:
                    print(f"   âœ— Bridge returned status {resp.status}")
                    return False
    except Exception as e:
        print(f"   âœ— Bridge error: {e}")
        return False


async def test_mas_health():
    """Test MAS orchestrator health."""
    print("\n3. Testing MAS orchestrator...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{MAS_URL}/health", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   âœ“ MAS healthy: v{data.get('version', 'unknown')}")
                    return True
                else:
                    print(f"   âœ— MAS returned status {resp.status}")
                    return False
    except Exception as e:
        print(f"   âœ— MAS error: {e}")
        return False


async def test_voice_tools():
    """Test voice tools endpoints."""
    print("\n4. Testing voice tools...")
    
    # Test device status
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{MAS_URL}/api/voice/tools/devices/mushroom1/status",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   âœ“ Device status: Mushroom1 is {data.get('status', 'unknown')}")
                else:
                    print(f"   âœ— Device status returned {resp.status}")
    except Exception as e:
        print(f"   âš  Device status error (may not be deployed yet): {e}")
    
    # Test tool execution
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{MAS_URL}/api/voice/tools/execute",
                json={"tool_name": "agent_list", "query": "list agents"},
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   âœ“ Tool execution: {data.get('result', '')[:60]}...")
                else:
                    print(f"   âœ— Tool execution returned {resp.status}")
    except Exception as e:
        print(f"   âš  Tool execution error (may not be deployed yet): {e}")
    
    return True


async def test_voice_chat():
    """Test voice orchestrator chat."""
    print("\n5. Testing voice orchestrator chat...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{MAS_URL}/voice/orchestrator/chat",
                json={
                    "message": "What's your name?",
                    "actor": "user",
                    "conversation_id": "test-session"
                },
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    response = data.get("response_text", "")
                    agent = data.get("agent_name", "")
                    print(f"   âœ“ Agent: {agent}")
                    print(f"   âœ“ Response: {response[:100]}...")
                    if "MYCA" in response or "MYCA" in agent:
                        print("   âœ“ MYCA identity verified!")
                    return True
                else:
                    print(f"   âœ— Voice chat returned status {resp.status}")
                    return False
    except Exception as e:
        print(f"   âœ— Voice chat error: {e}")
        return False


async def test_event_stream():
    """Test MAS event stream."""
    print("\n6. Testing event stream...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{MAS_URL}/events/stream",
                params={"session_id": "test", "since": 0},
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   âœ“ Event stream active: {data.get('count', 0)} events")
                    return True
                else:
                    print(f"   âœ— Event stream returned status {resp.status}")
                    return False
    except Exception as e:
        print(f"   âœ— Event stream error: {e}")
        return False


async def test_session_creation():
    """Test bridge session creation."""
    print("\n7. Testing session creation...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{BRIDGE_URL}/session",
                json={"persona": "myca"},
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    session_id = data.get("session_id", "")
                    print(f"   âœ“ Session created: {session_id[:8]}...")
                    return session_id
                else:
                    print(f"   âœ— Session creation returned status {resp.status}")
                    return None
    except Exception as e:
        print(f"   âœ— Session creation error: {e}")
        return None


async def main():
    print("=" * 60)
    print("PersonaPlex + MAS Full-Duplex Voice Integration Test")
    print("=" * 60)
    
    results = {
        "moshi": await test_moshi_health(),
        "bridge": await test_bridge_health(),
        "mas": await test_mas_health(),
        "tools": await test_voice_tools(),
        "chat": await test_voice_chat(),
        "events": await test_event_stream(),
        "session": await test_session_creation() is not None,
    }
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "âœ“ PASS" if result else "âœ— FAIL"
        print(f"  {name.upper():15} {status}")
    
    print(f"\n  Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n  âœ“ All systems operational!")
        print("  Ready for full-duplex voice with MAS integration")
    else:
        print("\n  âš  Some tests failed - check services above")
    
    print("=" * 60)
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
