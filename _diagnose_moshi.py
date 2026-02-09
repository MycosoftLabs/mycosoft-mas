#!/usr/bin/env python3
"""
Diagnose Moshi Server Issues - February 4, 2026
"""
import asyncio
import sys
import socket
import subprocess
import time

print("=" * 60)
print("MOSHI SERVER DIAGNOSTIC")
print("February 4, 2026")
print("=" * 60)

MOSHI_PORT = 8998
BRIDGE_PORT = 8999

def check_port(port: int) -> bool:
    """Check if port is listening."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def check_gpu():
    """Check GPU status."""
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.used,memory.total,utilization.gpu', '--format=csv,noheader'],
                                capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"GPU Status: {result.stdout.strip()}")
            return True
        else:
            print(f"GPU Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"GPU Check Failed: {e}")
        return False

def check_python_processes():
    """Check running Python processes."""
    try:
        result = subprocess.run(['powershell', '-Command', 
                                 'Get-Process python* | Select-Object Id,ProcessName,WorkingSet64 | Format-Table'],
                                capture_output=True, text=True, timeout=10)
        print("\nPython Processes:")
        print(result.stdout)
        return True
    except Exception as e:
        print(f"Process Check Failed: {e}")
        return False

async def check_moshi_websocket():
    """Test WebSocket connection to Moshi."""
    import aiohttp
    
    print("\n--- Testing Moshi WebSocket ---")
    
    try:
        async with aiohttp.ClientSession() as session:
            url = f"ws://localhost:{MOSHI_PORT}/api/chat"
            print(f"Connecting to: {url}")
            
            start = time.time()
            async with session.ws_connect(url, timeout=aiohttp.ClientTimeout(total=10)) as ws:
                print(f"  Connected! Waiting for handshake...")
                
                try:
                    msg = await asyncio.wait_for(ws.receive(), timeout=5)
                    elapsed = time.time() - start
                    
                    if msg.type == aiohttp.WSMsgType.BINARY:
                        if msg.data == b"\x00":
                            print(f"  HANDSHAKE OK in {elapsed:.2f}s")
                            return True
                        else:
                            print(f"  Unexpected data: {msg.data[:20]}")
                    else:
                        print(f"  Unexpected message type: {msg.type}")
                        
                except asyncio.TimeoutError:
                    print(f"  TIMEOUT waiting for handshake (5s)")
                    print("  DIAGNOSIS: Moshi connected but not responding")
                    print("  LIKELY CAUSE: Model still loading or CUDA graphs issue")
                    return False
                    
    except aiohttp.ClientError as e:
        print(f"  Connection error: {e}")
        return False
    except Exception as e:
        print(f"  Error: {e}")
        return False

async def check_bridge():
    """Check bridge status."""
    import aiohttp
    
    print("\n--- Testing PersonaPlex Bridge ---")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://localhost:{BRIDGE_PORT}/health", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                data = await resp.json()
                print(f"  Bridge Status: {data.get('status')}")
                print(f"  Moshi Available: {data.get('moshi_available')}")
                print(f"  Temperature: {data.get('temperature')}")
                return data.get('status') == 'healthy'
    except Exception as e:
        print(f"  Bridge Error: {e}")
        return False

def restart_moshi():
    """Provide restart instructions."""
    print("\n" + "=" * 60)
    print("RECOMMENDED ACTIONS:")
    print("=" * 60)
    print("""
1. RESTART MOSHI SERVER:
   - Open Task Manager (Ctrl+Shift+Esc)
   - Find Python processes using ~23GB memory
   - End those processes
   - Run: python start_personaplex.py

2. CHECK GPU MEMORY:
   - Run: nvidia-smi
   - Ensure GPU has enough free memory (~24GB)

3. RESTART BRIDGE (after Moshi is up):
   - Kill the bridge process
   - Run: python services/personaplex-local/personaplex_bridge_nvidia.py

4. TEST DIRECTLY:
   - Open http://localhost:8998 in browser
   - This is the native Moshi UI (bypasses bridge)
""")

async def main():
    # Basic port checks
    print("\n--- Port Status ---")
    moshi_up = check_port(MOSHI_PORT)
    bridge_up = check_port(BRIDGE_PORT)
    print(f"Moshi (8998): {'LISTENING' if moshi_up else 'NOT LISTENING'}")
    print(f"Bridge (8999): {'LISTENING' if bridge_up else 'NOT LISTENING'}")
    
    # GPU check
    print("\n--- GPU Status ---")
    check_gpu()
    
    # Process check
    check_python_processes()
    
    if not moshi_up:
        print("\n*** MOSHI SERVER IS NOT RUNNING ***")
        print("Run: python start_personaplex.py")
        return
    
    # WebSocket test
    moshi_ok = await check_moshi_websocket()
    
    if bridge_up:
        await check_bridge()
    
    if not moshi_ok:
        restart_moshi()
    else:
        print("\n" + "=" * 60)
        print("MOSHI IS WORKING!")
        print("=" * 60)
        print("The WebSocket handshake succeeded.")
        print("If voice still doesn't work, check the browser client.")

if __name__ == "__main__":
    try:
        import aiohttp
    except ImportError:
        print("Installing aiohttp...")
        subprocess.run([sys.executable, "-m", "pip", "install", "aiohttp"])
        import aiohttp
    
    asyncio.run(main())
