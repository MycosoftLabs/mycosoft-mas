#!/usr/bin/env python3
"""
Start entire voice system – single script (Feb 2026)

This is the one script to run to start the full MYCA voice stack:
  - Moshi TTS/STT (port 8998), if not already running
  - PersonaPlex Bridge (port 8999), if not already running
  - Connects to MAS (192.168.0.188:8001) for MYCA brain

Run from MAS repo root or scripts/:
  python scripts/start_voice_system.py

For test-voice in the browser, also start the website dev server (port 3010)
in a separate terminal; then open http://localhost:3010/test-voice.
"""
import os
import socket
import subprocess
import sys
import time

# Check GPU
try:
    import torch
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1024**3
        print(f"[GPU] {gpu_name} with {gpu_mem:.1f}GB VRAM")
    else:
        print("[WARNING] CUDA not available - PersonaPlex requires GPU")
        sys.exit(1)
except ImportError:
    print("[WARNING] PyTorch not installed")

def is_port_free(port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        return result != 0
    except Exception:
        return True

def is_port_listening(port):
    return not is_port_free(port)

print("\n=== Voice system startup (single script) ===\n")

# Check MAS connection
print("[1] Checking MAS connection...")
try:
    import httpx
except ImportError:
    httpx = None
if httpx:
    try:
        r = httpx.get("http://192.168.0.188:8001/health", timeout=5)
        if r.status_code == 200:
            print("    [OK] MAS Orchestrator is reachable")
        else:
            print(f"    [WARNING] MAS returned {r.status_code}")
    except Exception as e:
        print(f"    [ERROR] Cannot reach MAS: {e}")
        print("    PersonaPlex requires MAS to be running for MYCA's brain")
else:
    print("    [SKIP] httpx not installed")

# Check/Start Moshi (skip if Moshi is remote, e.g. GPU node)
moshi_host = os.environ.get("MOSHI_HOST", "localhost").strip().lower()
if moshi_host not in ("", "localhost", "127.0.0.1"):
    print("\n[2] Moshi is remote ({}) – skipping local Moshi start".format(os.environ.get("MOSHI_HOST", "")))
else:
    print("\n[2] Checking Moshi server (port 8998)...")
    if is_port_listening(8998):
        print("    [OK] Moshi already running on port 8998")
    else:
        print("    [STARTING] Moshi server...")
        
        # RTX 5090 GPU Mode 0 workaround: disable Torch compile and CUDA graphs
        # PyTorch doesn't support sm_120 (Blackwell) yet, so we must disable compilation.
        # See docs/RTX_5090_PYTORCH_SUPPORT_FEB12_2026.md
        moshi_env = os.environ.copy()
        moshi_env["NO_TORCH_COMPILE"] = "1"
        moshi_env["NO_CUDA_GRAPH"] = "1"
        moshi_env["TORCHDYNAMO_DISABLE"] = "1"
        moshi_env["TORCH_COMPILE_DISABLE"] = "1"
        print("    [GPU] RTX 5090 mode: TORCH_COMPILE and CUDA_GRAPH disabled")
        
        moshi_cmd = [sys.executable, "-m", "moshi.server", "--host", "0.0.0.0", "--port", "8998"]
        moshi_proc = subprocess.Popen(
            moshi_cmd,
            env=moshi_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0,
        )
        print(f"    [OK] Moshi started (PID: {moshi_proc.pid})")
        print("    [WAIT] Loading model (this takes ~30-60 seconds)...")
        for i in range(90):  # Extended to 90 seconds for slower startup without CUDA graphs
            time.sleep(1)
            if is_port_listening(8998):
                print(f"    [OK] Moshi ready after {i+1} seconds")
                break
            if i % 10 == 9:
                print(f"    [WAIT] Still loading... ({i+1}s)")
        else:
            print("    [WARNING] Moshi didn't start in 90 seconds, continuing anyway...")

# Check/Start PersonaPlex Bridge (always run when script is used)
print("\n[3] Checking PersonaPlex Bridge (port 8999)...")
if is_port_listening(8999):
    print("    [OK] Bridge already running on port 8999")
else:
    print("    [STARTING] PersonaPlex Bridge...")
    bridge_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "services", "personaplex-local", "personaplex_bridge_nvidia.py",
    )
    bridge_path = os.path.normpath(bridge_path)
    bridge_cmd = [sys.executable, bridge_path]
    env = os.environ.copy()
    env["MAS_ORCHESTRATOR_URL"] = "http://192.168.0.188:8001"
    env["MYCA_BRAIN_ENABLED"] = "true"
    bridge_proc = subprocess.Popen(
        bridge_cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0,
    )
    print(f"    [OK] Bridge started (PID: {bridge_proc.pid})")
    time.sleep(3)
    if is_port_listening(8999):
        print("    [OK] Bridge is ready")
    else:
        print("    [WARNING] Bridge may not have started correctly")

# Check bridge health
print("\n[4] Checking PersonaPlex health...")
if httpx:
    try:
        r = httpx.get("http://localhost:8999/health", timeout=5)
        if r.status_code == 200:
            data = r.json()
            print(f"    [OK] Bridge version: {data.get('version', 'unknown')}")
            print(f"    [OK] Moshi available: {data.get('moshi_available', False)}")
            print(f"    [OK] MAS URL: {data.get('mas_orchestrator', 'not set')}")
        else:
            print(f"    [WARNING] Bridge health returned {r.status_code}")
    except Exception as e:
        print(f"    [WARNING] Bridge health check failed: {e}")

print("\n" + "=" * 60)
print("VOICE SYSTEM READY")
print("=" * 60)
print("")
print("  Moshi:        http://localhost:8998")
print("  Bridge:       http://localhost:8999")
print("  Bridge health: http://localhost:8999/health")
print("")
print("  Test-voice page: start website dev (port 3010), then open")
print("  http://localhost:3010/test-voice")
print("")
print("=" * 60)
print("Press Ctrl+C to exit this script (Moshi and Bridge keep running in their windows).")
print("=" * 60)

try:
    while True:
        time.sleep(5)
except KeyboardInterrupt:
    print("\n[DONE] Exiting. Moshi and Bridge continue in their own windows.")
    print("       Stop them from those windows or with dev-machine-cleanup.ps1 -KillStaleGPU.")
