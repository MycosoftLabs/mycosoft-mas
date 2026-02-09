#!/usr/bin/env python3
"""
Moshi CUDA Graphs Warmup Script
February 4, 2026

This script warms up Moshi's CUDA graphs by making a test connection.
After warmup, subsequent connections will be fast.

IMPORTANT: Run this BEFORE using the test-voice page!
"""
import asyncio
import sys
import time

async def warmup_moshi(max_wait=120):
    """Connect to Moshi and wait for CUDA graphs to compile."""
    try:
        import aiohttp
    except ImportError:
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "aiohttp", "-q"], check=True)
        import aiohttp
    
    print("=" * 60)
    print("MOSHI CUDA GRAPHS WARMUP")
    print("=" * 60)
    print()
    print("This will trigger CUDA graphs compilation.")
    print(f"Max wait time: {max_wait} seconds")
    print()
    
    moshi_url = "ws://localhost:8998/api/chat"
    
    try:
        async with aiohttp.ClientSession() as session:
            print("Connecting to Moshi...")
            start = time.time()
            
            async with session.ws_connect(
                moshi_url,
                timeout=aiohttp.ClientTimeout(total=max_wait + 10)
            ) as ws:
                print("Waiting for handshake (CUDA graphs compiling)...")
                print()
                
                # Show progress
                async def show_progress():
                    while True:
                        elapsed = int(time.time() - start)
                        print(f"\r  Elapsed: {elapsed}s (this can take 60-90s on first run)   ", end="", flush=True)
                        await asyncio.sleep(1)
                
                progress_task = asyncio.create_task(show_progress())
                
                try:
                    msg = await asyncio.wait_for(ws.receive(), timeout=max_wait)
                    progress_task.cancel()
                    
                    elapsed = time.time() - start
                    print()
                    print()
                    
                    if msg.type == aiohttp.WSMsgType.BINARY and msg.data == b"\x00":
                        print(f"[SUCCESS] Moshi warmed up in {elapsed:.1f} seconds!")
                        print()
                        print("CUDA graphs are now compiled.")
                        print("Subsequent connections will be fast (~2s).")
                        print()
                        print("You can now use: http://localhost:3010/test-voice")
                        return True
                    else:
                        print(f"[WARN] Unexpected response: {msg.type}")
                        return True  # Still connected
                        
                except asyncio.TimeoutError:
                    progress_task.cancel()
                    print()
                    print()
                    print(f"[FAIL] Timeout after {max_wait}s")
                    print("CUDA graphs may need more time or there's an issue.")
                    return False
                    
    except Exception as e:
        print()
        print(f"[ERROR] {e}")
        print()
        print("Make sure Moshi server is running:")
        print("  python start_personaplex.py")
        return False
    
    print("=" * 60)


def main():
    """Main entry point."""
    import socket
    
    # Check if Moshi is running
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            if s.connect_ex(("localhost", 8998)) != 0:
                print("[ERROR] Moshi server not running on port 8998")
                print("Start it with: python start_personaplex.py")
                return False
    except:
        pass
    
    return asyncio.run(warmup_moshi())


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
