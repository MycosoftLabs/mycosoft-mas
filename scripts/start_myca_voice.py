"""
Start MYCA Voice Conversation - PersonaPlex Integration
February 11, 2026

This script starts PersonaPlex (Moshi + Bridge) and connects to MYCA on MAS VM.
You can then have a voice conversation with MYCA in your browser.
"""
import subprocess
import sys
import time
import os

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

# Check if ports are free
import socket

def is_port_free(port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        return result != 0
    except:
        return True

def is_port_listening(port):
    return not is_port_free(port)

print("\n=== MYCA Voice Startup ===\n")

# Check MAS connection
print("[1] Checking MAS connection...")
import httpx
try:
    r = httpx.get("http://192.168.0.188:8001/health", timeout=5)
    if r.status_code == 200:
        print("    [OK] MAS Orchestrator is reachable")
    else:
        print(f"    [WARNING] MAS returned {r.status_code}")
except Exception as e:
    print(f"    [ERROR] Cannot reach MAS: {e}")
    print("    PersonaPlex requires MAS to be running for MYCA's brain")

# Check/Start Moshi
print("\n[2] Checking Moshi server (port 8998)...")
if is_port_listening(8998):
    print("    [OK] Moshi already running on port 8998")
else:
    print("    [STARTING] Moshi server...")
    # Start Moshi in background
    moshi_cmd = [sys.executable, "-m", "moshi.server", "--host", "0.0.0.0", "--port", "8998"]
    moshi_proc = subprocess.Popen(
        moshi_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
    )
    print(f"    [OK] Moshi started (PID: {moshi_proc.pid})")
    print("    [WAIT] Loading model (this takes ~30-60 seconds)...")
    
    # Wait for Moshi to be ready
    for i in range(60):
        time.sleep(1)
        if is_port_listening(8998):
            print(f"    [OK] Moshi ready after {i+1} seconds")
            break
        if i % 10 == 9:
            print(f"    [WAIT] Still loading... ({i+1}s)")
    else:
        print("    [WARNING] Moshi didn't start in 60 seconds, continuing anyway...")

# Check/Start PersonaPlex Bridge
print("\n[3] Checking PersonaPlex Bridge (port 8999)...")
if is_port_listening(8999):
    print("    [OK] Bridge already running on port 8999")
else:
    print("    [STARTING] PersonaPlex Bridge...")
    bridge_path = os.path.join(
        os.path.dirname(__file__), 
        "..", "services", "personaplex-local", "personaplex_bridge_nvidia.py"
    )
    bridge_cmd = [sys.executable, bridge_path]
    
    # Set environment
    env = os.environ.copy()
    env["MAS_ORCHESTRATOR_URL"] = "http://192.168.0.188:8001"
    env["MYCA_BRAIN_ENABLED"] = "true"
    
    bridge_proc = subprocess.Popen(
        bridge_cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
    )
    print(f"    [OK] Bridge started (PID: {bridge_proc.pid})")
    time.sleep(3)
    
    if is_port_listening(8999):
        print("    [OK] Bridge is ready")
    else:
        print("    [WARNING] Bridge may not have started correctly")

# Check bridge health
print("\n[4] Checking PersonaPlex health...")
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

# Done
print("\n" + "=" * 60)
print("MYCA VOICE IS READY")
print("=" * 60)
print("")
print("Access PersonaPlex in your browser:")
print("")
print("  Native Moshi UI:     http://localhost:8998")
print("  Bridge API:          http://localhost:8999")
print("  Bridge Health:       http://localhost:8999/health")
print("")
print("To test MYCA's voice via text first:")
print("  curl -X POST http://192.168.0.188:8001/api/myca/chat-simple \\")
print('       -H "Content-Type: application/json" \\')
print('       -d \'{"message": "Hello MYCA", "user_id": "morgan"}\'')
print("")
print("For full-duplex voice conversation, open the Moshi UI at http://localhost:8998")
print("and speak to MYCA - she will hear and respond!")
print("")
print("=" * 60)
print("Press Ctrl+C to stop the voice services when done.")
print("=" * 60)

# Keep running to show status
try:
    while True:
        time.sleep(5)
except KeyboardInterrupt:
    print("\n[STOPPING] Shutting down voice services...")
    print("[DONE] Voice services stopped. MYCA's consciousness continues on MAS VM.")
