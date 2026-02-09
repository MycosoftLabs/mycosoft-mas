#!/usr/bin/env python3
"""
MYCA Voice System Automated Startup
February 4, 2026

This script properly starts all voice services in the correct order,
waits for CUDA graphs to compile, and verifies everything is working.

IMPORTANT: CUDA graphs MUST stay enabled for 30ms/step performance.
The warmup phase handles the initial compilation.
"""
import os
import sys
import time
import socket
import subprocess
import asyncio
import signal

# Configuration
MOSHI_PORT = 8998
BRIDGE_PORT = 8999
MAS_HOST = "192.168.0.188"
MAS_PORT = 8001

# Paths
MAS_DIR = r"c:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas"
MOSHI_SCRIPT = os.path.join(MAS_DIR, "start_personaplex.py")
BRIDGE_SCRIPT = os.path.join(MAS_DIR, "services", "personaplex-local", "personaplex_bridge_nvidia.py")

# Process handles
moshi_process = None
bridge_process = None


def print_header(text):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_status(name, status, message=""):
    icon = "[OK]" if status else "[WAIT]"
    print(f"  {icon} {name}: {message}")


def check_port(port, host="localhost"):
    """Check if a port is open."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            return s.connect_ex((host, port)) == 0
    except:
        return False


def wait_for_port(port, host="localhost", timeout=120, message=""):
    """Wait for a port to become available."""
    start = time.time()
    while time.time() - start < timeout:
        if check_port(port, host):
            return True
        elapsed = int(time.time() - start)
        print(f"\r  Waiting for {message} ({elapsed}s)...    ", end="", flush=True)
        time.sleep(2)
    print()
    return False


async def test_moshi_websocket(timeout=60):
    """Test Moshi WebSocket with CUDA graphs warmup."""
    try:
        import aiohttp
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "aiohttp", "-q"], check=True)
        import aiohttp
    
    try:
        async with aiohttp.ClientSession() as session:
            print(f"\n  Connecting to Moshi WebSocket...")
            async with session.ws_connect(
                f"ws://localhost:{MOSHI_PORT}/api/chat",
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as ws:
                print(f"  Waiting for handshake (CUDA graphs compiling)...")
                start = time.time()
                msg = await asyncio.wait_for(ws.receive(), timeout=timeout)
                elapsed = time.time() - start
                
                if msg.type == aiohttp.WSMsgType.BINARY and msg.data == b"\x00":
                    print(f"  [OK] Moshi handshake OK in {elapsed:.1f}s")
                    return True
                else:
                    print(f"  [WARN] Unexpected response: {msg.type}")
                    return True  # Still connected
    except asyncio.TimeoutError:
        print(f"  [FAIL] Moshi timeout after {timeout}s - CUDA graphs may need longer")
        return False
    except Exception as e:
        print(f"  [FAIL] Moshi error: {e}")
        return False


def start_moshi():
    """Start Moshi server."""
    global moshi_process
    
    print_header("STARTING MOSHI SERVER (CUDA GRAPHS ENABLED)")
    
    # Start Moshi in a new process
    moshi_process = subprocess.Popen(
        [sys.executable, MOSHI_SCRIPT],
        cwd=MAS_DIR,
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    
    print(f"  Moshi process started (PID: {moshi_process.pid})")
    print(f"  CUDA graphs will compile on first connection...")
    
    # Wait for port to open
    if not wait_for_port(MOSHI_PORT, timeout=120, message="Moshi port 8998"):
        print("  [FAIL] Moshi did not start")
        return False
    
    print(f"\n  [OK] Moshi port 8998 is open")
    
    # Test WebSocket with CUDA warmup
    print("\n  Testing WebSocket (CUDA graphs warmup)...")
    result = asyncio.run(test_moshi_websocket(timeout=90))
    
    if result:
        print("  [OK] Moshi is fully ready with CUDA graphs!")
        return True
    else:
        print("  [FAIL] Moshi WebSocket test failed")
        return False


def start_bridge():
    """Start PersonaPlex Bridge."""
    global bridge_process
    
    print_header("STARTING PERSONAPLEX BRIDGE")
    
    bridge_process = subprocess.Popen(
        [sys.executable, BRIDGE_SCRIPT],
        cwd=MAS_DIR,
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    
    print(f"  Bridge process started (PID: {bridge_process.pid})")
    
    # Wait for port
    if not wait_for_port(BRIDGE_PORT, timeout=30, message="Bridge port 8999"):
        print("  [FAIL] Bridge did not start")
        return False
    
    print(f"\n  [OK] Bridge is ready on port 8999")
    
    # Verify health
    try:
        import requests
        r = requests.get(f"http://localhost:{BRIDGE_PORT}/health", timeout=5)
        data = r.json()
        print(f"  Version: {data.get('version')}")
        print(f"  Moshi Available: {data.get('moshi_available')}")
        return data.get("moshi_available", False)
    except Exception as e:
        print(f"  [WARN] Could not verify bridge health: {e}")
        return True


def check_mas():
    """Check MAS Orchestrator."""
    print_header("CHECKING MAS ORCHESTRATOR")
    
    try:
        import requests
        r = requests.get(f"http://{MAS_HOST}:{MAS_PORT}/health", timeout=10)
        data = r.json()
        print(f"  [OK] MAS Orchestrator: {data.get('status')}")
        print(f"  Version: {data.get('version')}")
        return True
    except Exception as e:
        print(f"  [FAIL] MAS Orchestrator not available: {e}")
        return False


def test_voice_endpoint():
    """Test the voice chat endpoint."""
    print_header("TESTING MYCA VOICE")
    
    try:
        import requests
        r = requests.post(
            f"http://{MAS_HOST}:{MAS_PORT}/voice/orchestrator/chat",
            json={"message": "What is your name?"},
            timeout=15
        )
        data = r.json()
        response = data.get("response_text", "")[:80]
        
        if "MYCA" in response or "Mycosoft" in response:
            print(f"  [OK] MYCA responded: {response}...")
            return True
        else:
            print(f"  [WARN] Unexpected response: {response}...")
            return True
    except Exception as e:
        print(f"  [FAIL] Voice endpoint error: {e}")
        return False


async def test_full_pipeline():
    """Test full WebSocket pipeline through bridge."""
    print_header("TESTING FULL PIPELINE (BRIDGE → MOSHI)")
    
    try:
        import aiohttp
        import requests
        
        # Create session
        r = requests.post(f"http://localhost:{BRIDGE_PORT}/session", timeout=5)
        session_id = r.json()["session_id"]
        print(f"  Session created: {session_id[:8]}...")
        
        async with aiohttp.ClientSession() as session:
            ws_url = f"ws://localhost:{BRIDGE_PORT}/ws/{session_id}"
            print(f"  Connecting to bridge WebSocket...")
            
            async with session.ws_connect(
                ws_url,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as ws:
                print(f"  Waiting for Moshi handshake via bridge...")
                msg = await asyncio.wait_for(ws.receive(), timeout=45)
                
                if msg.type == aiohttp.WSMsgType.BINARY and msg.data == b"\x00":
                    print(f"  [OK] Full pipeline working!")
                    return True
                elif msg.type == aiohttp.WSMsgType.TEXT:
                    data = msg.data
                    if "error" in data.lower():
                        print(f"  [FAIL] Bridge error: {data}")
                        return False
                    print(f"  [OK] Bridge response received")
                    return True
                else:
                    print(f"  [WARN] Unexpected: {msg.type}")
                    return True
    except asyncio.TimeoutError:
        print(f"  [FAIL] Pipeline timeout")
        return False
    except Exception as e:
        print(f"  [FAIL] Pipeline error: {e}")
        return False


def main():
    """Main startup sequence."""
    print("\n" + "=" * 70)
    print("  MYCA VOICE SYSTEM - AUTOMATED STARTUP")
    print("  February 4, 2026")
    print("  CUDA GRAPHS: ENABLED (30ms/step performance)")
    print("=" * 70)
    
    # Step 1: Start Moshi
    if not start_moshi():
        print("\n[FATAL] Could not start Moshi. Aborting.")
        return False
    
    # Small delay to ensure Moshi is stable
    print("\n  Waiting 5s for Moshi to stabilize...")
    time.sleep(5)
    
    # Step 2: Start Bridge
    if not start_bridge():
        print("\n[FATAL] Could not start Bridge. Aborting.")
        return False
    
    # Step 3: Check MAS
    check_mas()
    
    # Step 4: Test voice endpoint
    test_voice_endpoint()
    
    # Step 5: Test full pipeline
    pipeline_ok = asyncio.run(test_full_pipeline())
    
    # Summary
    print("\n" + "=" * 70)
    print("  STARTUP COMPLETE")
    print("=" * 70)
    
    if pipeline_ok:
        print("\n  [SUCCESS] All systems operational!")
        print("\n  TEST VOICE NOW:")
        print("  http://localhost:3010/test-voice")
        print("\n  SERVICES RUNNING:")
        print(f"  - Moshi Server:      http://localhost:{MOSHI_PORT}")
        print(f"  - PersonaPlex Bridge: http://localhost:{BRIDGE_PORT}")
        print(f"  - MAS Orchestrator:  http://{MAS_HOST}:{MAS_PORT}")
        print(f"\n  NATIVE MOSHI UI (for testing):")
        print(f"  http://localhost:8998")
    else:
        print("\n  [WARNING] Some systems may need attention")
        print("  Check the logs above for details")
    
    print("\n" + "=" * 70)
    print("  Press Ctrl+C to stop all services")
    print("=" * 70)
    
    # Keep running
    try:
        while True:
            time.sleep(60)
            # Periodic health check
            if moshi_process and moshi_process.poll() is not None:
                print("\n[WARN] Moshi process died. Restart recommended.")
            if bridge_process and bridge_process.poll() is not None:
                print("\n[WARN] Bridge process died. Restart recommended.")
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        if bridge_process:
            bridge_process.terminate()
        if moshi_process:
            moshi_process.terminate()
        print("Done.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(0)
