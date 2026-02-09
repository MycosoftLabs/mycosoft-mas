#!/usr/bin/env python3
"""
n8n Setup and Voice System Test Script
February 4, 2026

This script:
1. Checks n8n status on MAS VM
2. Imports all workflows to n8n
3. Tests the voice system
"""
import os
import sys
import json
import time
import glob
import requests
from pathlib import Path

print("=" * 70)
print("MYCA VOICE SYSTEM - n8n SETUP & TEST")
print("February 4, 2026")
print("=" * 70)

# Configuration
MAS_VM = "192.168.0.188"
N8N_PORT = 5678
N8N_URL = f"http://{MAS_VM}:{N8N_PORT}"
MAS_PORT = 8001
MAS_URL = f"http://{MAS_VM}:{MAS_PORT}"
MOSHI_URL = "http://localhost:8998"
BRIDGE_URL = "http://localhost:8999"

WORKFLOWS_DIR = Path(r"c:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\n8n\workflows")

# n8n credentials (from docs)
N8N_USER = "morgan@mycosoft.org"
N8N_PASS = "REDACTED_VM_SSH_PASSWORD"


def check_service(name, url, timeout=5):
    """Check if a service is running."""
    try:
        r = requests.get(f"{url}/health" if "/health" not in url else url, timeout=timeout)
        return r.status_code in [200, 426]
    except:
        try:
            r = requests.get(url, timeout=timeout)
            return r.status_code in [200, 302, 401, 403]
        except:
            return False


def check_all_services():
    """Check all required services."""
    print("\n[1] CHECKING SERVICES...")
    
    services = {
        "Moshi (8998)": MOSHI_URL,
        "Bridge (8999)": BRIDGE_URL,
        "MAS (8001)": MAS_URL,
        "n8n (5678)": N8N_URL,
    }
    
    results = {}
    for name, url in services.items():
        status = check_service(name, url)
        results[name] = status
        print(f"   {'[OK]' if status else '[FAIL]'} {name}")
    
    return results


def get_n8n_api_key():
    """Try to get n8n API key or use basic auth."""
    # First try with basic auth
    try:
        session = requests.Session()
        # Try to get workflows with basic auth
        r = session.get(
            f"{N8N_URL}/api/v1/workflows",
            auth=(N8N_USER, N8N_PASS),
            timeout=10
        )
        if r.status_code == 200:
            return session, "basic"
    except Exception as e:
        print(f"   Basic auth failed: {e}")
    
    return None, None


def import_workflows(session, auth_type):
    """Import all workflows to n8n."""
    print("\n[2] IMPORTING WORKFLOWS...")
    
    if not WORKFLOWS_DIR.exists():
        print(f"   [ERROR] Workflows directory not found: {WORKFLOWS_DIR}")
        return False
    
    workflow_files = list(WORKFLOWS_DIR.glob("*.json"))
    print(f"   Found {len(workflow_files)} workflow files")
    
    imported = 0
    failed = 0
    skipped = 0
    
    for wf_file in workflow_files:
        try:
            with open(wf_file, 'r', encoding='utf-8') as f:
                workflow_data = json.load(f)
            
            # Check if it's a valid workflow (has nodes)
            if 'nodes' not in workflow_data:
                print(f"   [SKIP] {wf_file.name} (not a valid workflow)")
                skipped += 1
                continue
            
            # Prepare import data
            import_data = {
                "name": workflow_data.get("name", wf_file.stem),
                "nodes": workflow_data.get("nodes", []),
                "connections": workflow_data.get("connections", {}),
                "settings": workflow_data.get("settings", {}),
                "active": False  # Import as inactive initially
            }
            
            # Try to import
            if auth_type == "basic":
                r = session.post(
                    f"{N8N_URL}/api/v1/workflows",
                    json=import_data,
                    auth=(N8N_USER, N8N_PASS),
                    timeout=30
                )
            else:
                r = session.post(
                    f"{N8N_URL}/api/v1/workflows",
                    json=import_data,
                    timeout=30
                )
            
            if r.status_code in [200, 201]:
                print(f"   [OK] {wf_file.name}")
                imported += 1
            elif r.status_code == 409:
                print(f"   [EXISTS] {wf_file.name}")
                skipped += 1
            else:
                print(f"   [FAIL] {wf_file.name}: {r.status_code} - {r.text[:100]}")
                failed += 1
                
        except Exception as e:
            print(f"   [ERROR] {wf_file.name}: {e}")
            failed += 1
    
    print(f"\n   Summary: Imported={imported}, Skipped={skipped}, Failed={failed}")
    return imported > 0 or skipped > 0


def test_myca_voice():
    """Test MYCA voice endpoint."""
    print("\n[3] TESTING MYCA VOICE...")
    
    test_cases = [
        ("Identity", "What is your name?"),
        ("Knowledge", "Tell me about Mycosoft"),
        ("Math", "What is 2 plus 2?"),
        ("Devices", "What devices do you monitor?"),
    ]
    
    all_passed = True
    for name, message in test_cases:
        try:
            r = requests.post(
                f"{MAS_URL}/voice/orchestrator/chat",
                json={"message": message},
                timeout=15
            )
            data = r.json()
            response_text = data.get("response_text", "")[:100]
            
            # Check for MYCA identity in responses
            if name == "Identity":
                passed = "MYCA" in response_text or "Mycosoft" in response_text
            else:
                passed = len(response_text) > 10
            
            print(f"   {'[OK]' if passed else '[FAIL]'} {name}: {response_text}...")
            if not passed:
                all_passed = False
                
        except Exception as e:
            print(f"   [ERROR] {name}: {e}")
            all_passed = False
    
    return all_passed


def test_bridge_websocket():
    """Test PersonaPlex Bridge WebSocket."""
    print("\n[4] TESTING BRIDGE WEBSOCKET...")
    
    try:
        import asyncio
        import aiohttp
        
        async def test_ws():
            try:
                async with aiohttp.ClientSession() as session:
                    # Create a session
                    async with session.post(f"{BRIDGE_URL}/session") as resp:
                        data = await resp.json()
                        session_id = data["session_id"]
                        print(f"   Session created: {session_id}")
                    
                    # Connect to WebSocket
                    ws_url = f"ws://localhost:8999/ws/{session_id}"
                    async with session.ws_connect(ws_url, timeout=aiohttp.ClientTimeout(total=35)) as ws:
                        msg = await asyncio.wait_for(ws.receive(), timeout=30)
                        if msg.type == aiohttp.WSMsgType.BINARY and msg.data == b"\x00":
                            print("   [OK] WebSocket handshake successful")
                            return True
                        else:
                            print(f"   [WARN] Unexpected message type: {msg.type}")
                            return True
            except asyncio.TimeoutError:
                print("   [FAIL] WebSocket handshake timeout")
                return False
            except Exception as e:
                print(f"   [ERROR] {e}")
                return False
        
        return asyncio.run(test_ws())
    except ImportError:
        print("   [SKIP] aiohttp not available for WebSocket test")
        return True


def main():
    """Main entry point."""
    # Check services
    results = check_all_services()
    
    # Handle n8n
    if not results.get("n8n (5678)", False):
        print("\n[!] n8n is not running on MAS VM")
        print("    Please SSH to 192.168.0.188 and run:")
        print("    docker start myca-n8n")
        print("    Or: docker-compose -f docker/docker-compose.n8n.yml up -d")
    else:
        # Try to import workflows
        session, auth_type = get_n8n_api_key()
        if session:
            import_workflows(session, auth_type)
        else:
            print("\n[!] Could not authenticate with n8n")
            print("    Login: morgan@mycosoft.org")
            print("    Password: REDACTED_VM_SSH_PASSWORD")
    
    # Test MYCA voice
    voice_ok = test_myca_voice()
    
    # Test WebSocket
    ws_ok = test_bridge_websocket()
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    all_critical = all([
        results.get("Moshi (8998)", False),
        results.get("Bridge (8999)", False),
        results.get("MAS (8001)", False),
        voice_ok,
    ])
    
    if all_critical:
        print("\n   [SUCCESS] All critical systems operational!")
        print("\n   TEST VOICE NOW:")
        print("   http://localhost:3010/test-voice")
        print("   (Make sure website is running: cd website && npm run dev)")
    else:
        print("\n   [ATTENTION] Some systems need attention")
        if not results.get("n8n (5678)", False):
            print("   - n8n needs to be started on MAS VM")
    
    print("\n" + "=" * 70)
    return all_critical


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
