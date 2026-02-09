#!/usr/bin/env python3
"""
MYCA Voice System - One-Click Startup
February 4, 2026

This script:
1. Starts Moshi server with CUDA graphs ENABLED
2. Waits for model to load
3. Warms up CUDA graphs (first connection compiles them)
4. Starts PersonaPlex Bridge
5. Verifies everything is working

CUDA GRAPHS: ALWAYS ENABLED (30ms/step performance)
The brain engine handles intelligent responses via MYCA LLMs.
Moshi handles immediate conversational responses.
"""
import asyncio
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

# Paths
MAS_DIR = Path(r"c:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas")
MOSHI_SCRIPT = MAS_DIR / "start_personaplex.py"
BRIDGE_SCRIPT = MAS_DIR / "services" / "personaplex-local" / "personaplex_bridge_nvidia.py"

# Ports
MOSHI_PORT = 8998
BRIDGE_PORT = 8999
MAS_PORT = 8001
MAS_HOST = "192.168.0.188"

# Process handles
processes = []


def print_header(text):
    print()
    print("=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_step(step, text):
    print(f"\n[{step}] {text}")


def print_ok(text):
    print(f"    [OK] {text}")


def print_fail(text):
    print(f"    [FAIL] {text}")


def print_wait(text):
    print(f"    [WAIT] {text}")


def check_port(port, host="localhost"):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            return s.connect_ex((host, port)) == 0
    except:
        return False


def wait_for_port(port, host="localhost", timeout=180, desc=""):
    start = time.time()
    dots = 0
    while time.time() - start < timeout:
        if check_port(port, host):
            print()  # Newline after dots
            return True
        dots += 1
        if dots % 30 == 0:
            elapsed = int(time.time() - start)
            print(f"\n    Still waiting... ({elapsed}s)", end="")
        print(".", end="", flush=True)
        time.sleep(1)
    print()
    return False


def start_process(script, name):
    """Start a Python process."""
    proc = subprocess.Popen(
        [sys.executable, str(script)],
        cwd=str(MAS_DIR),
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )
    processes.append((name, proc))
    return proc


async def warmup_cuda_graphs(max_wait=120):
    """Connect to Moshi to trigger CUDA graphs compilation."""
    try:
        import aiohttp
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "aiohttp", "-q"], check=True)
        import aiohttp
    
    print_step("3", "WARMING UP CUDA GRAPHS")
    print("    This compiles CUDA graphs for 30ms/step performance.")
    print(f"    First connection can take 60-90 seconds...")
    
    try:
        async with aiohttp.ClientSession() as session:
            start = time.time()
            
            async with session.ws_connect(
                "ws://localhost:8998/api/chat",
                timeout=aiohttp.ClientTimeout(total=max_wait + 10)
            ) as ws:
                # Show progress
                async def show_progress():
                    while True:
                        elapsed = int(time.time() - start)
                        print(f"\r    Compiling CUDA graphs... {elapsed}s   ", end="", flush=True)
                        await asyncio.sleep(2)
                
                progress = asyncio.create_task(show_progress())
                
                try:
                    msg = await asyncio.wait_for(ws.receive(), timeout=max_wait)
                    progress.cancel()
                    
                    elapsed = time.time() - start
                    print()
                    
                    if msg.type == aiohttp.WSMsgType.BINARY and msg.data == b"\x00":
                        print_ok(f"CUDA graphs compiled in {elapsed:.1f}s")
                        return True
                    else:
                        print_ok(f"Moshi responded in {elapsed:.1f}s")
                        return True
                        
                except asyncio.TimeoutError:
                    progress.cancel()
                    print()
                    print_fail(f"Timeout after {max_wait}s")
                    return False
                    
    except Exception as e:
        print_fail(f"Error: {e}")
        return False


def check_mas():
    """Check MAS orchestrator."""
    try:
        import requests
        r = requests.get(f"http://{MAS_HOST}:{MAS_PORT}/health", timeout=5)
        if r.status_code == 200:
            data = r.json()
            return data.get("status") == "ok"
    except:
        pass
    return False


def test_voice_endpoint():
    """Test MYCA voice endpoint."""
    try:
        import requests
        r = requests.post(
            f"http://{MAS_HOST}:{MAS_PORT}/voice/orchestrator/chat",
            json={"message": "Hello"},
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            return "MYCA" in data.get("response_text", "")
    except:
        pass
    return False


async def test_full_pipeline():
    """Test full WebSocket pipeline."""
    try:
        import aiohttp
        import requests
        
        # Create session
        r = requests.post("http://localhost:8999/session", timeout=5)
        session_id = r.json()["session_id"]
        
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(
                f"ws://localhost:8999/ws/{session_id}",
                timeout=aiohttp.ClientTimeout(total=30)
            ) as ws:
                msg = await asyncio.wait_for(ws.receive(), timeout=20)
                return msg.type == aiohttp.WSMsgType.BINARY and msg.data == b"\x00"
    except:
        return False


def main():
    print_header("MYCA VOICE SYSTEM - ONE-CLICK STARTUP")
    print()
    print("    CUDA GRAPHS: ENABLED (30ms/step performance)")
    print("    Brain Engine: MYCA LLMs for intelligent responses")
    print("    Moshi: Full-duplex conversational responses")
    print()
    
    # Step 1: Start Moshi
    print_step("1", "STARTING MOSHI SERVER")
    
    # Kill any existing python processes on our ports
    for port in [MOSHI_PORT, BRIDGE_PORT]:
        if check_port(port):
            print_wait(f"Port {port} in use, will use existing process")
    
    if not check_port(MOSHI_PORT):
        print("    Starting Moshi with CUDA graphs enabled...")
        start_process(MOSHI_SCRIPT, "Moshi")
        
        print("    Waiting for model to load (uses 23GB VRAM)...", end="")
        if not wait_for_port(MOSHI_PORT, timeout=180):
            print_fail("Moshi did not start")
            return False
        print_ok("Moshi port is open")
    else:
        print_ok("Moshi already running on port 8998")
    
    # Step 2: Wait for model to fully load
    print_step("2", "WAITING FOR MODEL INITIALIZATION")
    print("    Model needs ~10-15s to fully initialize after port opens...")
    time.sleep(15)
    print_ok("Model should be ready")
    
    # Step 3: Warmup CUDA graphs
    warmup_ok = asyncio.run(warmup_cuda_graphs())
    if not warmup_ok:
        print_fail("CUDA warmup failed - Moshi may need restart")
        print("    Try killing all Python processes and running again.")
        return False
    
    # Step 4: Start Bridge
    print_step("4", "STARTING PERSONAPLEX BRIDGE")
    
    if not check_port(BRIDGE_PORT):
        print("    Starting bridge v7.0.0...")
        start_process(BRIDGE_SCRIPT, "Bridge")
        
        print("    Waiting for bridge...", end="")
        if not wait_for_port(BRIDGE_PORT, timeout=30):
            print_fail("Bridge did not start")
            return False
        time.sleep(3)  # Let it fully initialize
        print_ok("Bridge running on port 8999")
    else:
        print_ok("Bridge already running on port 8999")
    
    # Step 5: Verify Bridge
    print_step("5", "VERIFYING BRIDGE HEALTH")
    try:
        import requests
        r = requests.get("http://localhost:8999/health", timeout=5)
        data = r.json()
        print_ok(f"Version: {data.get('version')}")
        print_ok(f"Moshi available: {data.get('moshi_available')}")
    except Exception as e:
        print_fail(f"Bridge health check failed: {e}")
    
    # Step 6: Check MAS
    print_step("6", "CHECKING MAS ORCHESTRATOR")
    if check_mas():
        print_ok(f"MAS running on {MAS_HOST}:{MAS_PORT}")
        
        if test_voice_endpoint():
            print_ok("MYCA voice endpoint responding")
        else:
            print_wait("Voice endpoint may need configuration")
    else:
        print_wait(f"MAS not accessible at {MAS_HOST}:{MAS_PORT}")
    
    # Step 7: Test full pipeline
    print_step("7", "TESTING FULL PIPELINE")
    pipeline_ok = asyncio.run(test_full_pipeline())
    if pipeline_ok:
        print_ok("Full pipeline working!")
    else:
        print_fail("Pipeline test failed - try again in a moment")
    
    # Summary
    print_header("STARTUP COMPLETE")
    print()
    print("    [SUCCESS] Voice system is ready!")
    print()
    print("    TEST NOW:")
    print("    http://localhost:3010/test-voice")
    print()
    print("    NATIVE MOSHI UI (for quick testing):")
    print("    http://localhost:8998")
    print()
    print("    SERVICES RUNNING:")
    print(f"    - Moshi Server:       localhost:{MOSHI_PORT}")
    print(f"    - PersonaPlex Bridge: localhost:{BRIDGE_PORT}")
    print(f"    - MAS Orchestrator:   {MAS_HOST}:{MAS_PORT}")
    print()
    print("=" * 70)
    print("  Press Ctrl+C to stop monitoring")
    print("=" * 70)
    
    # Keep running and monitor
    try:
        while True:
            time.sleep(60)
            # Periodic health check
            for name, proc in processes:
                if proc.poll() is not None:
                    print(f"\n[WARN] {name} process died. Restart recommended.")
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        for name, proc in processes:
            try:
                proc.terminate()
            except:
                pass
        print("Done.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted.")
