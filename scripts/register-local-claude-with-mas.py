#!/usr/bin/env python3
"""
Register local Claude Code instance with MAS orchestrator.
Allows MAS to route coding tasks to local dev machine.
"""
import requests
import socket
import os
from pathlib import Path

# Get local machine IP
def get_local_ip():
    """Get local machine's LAN IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Connect to external address (doesn't actually send data)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

# Get machine name
hostname = socket.gethostname()
local_ip = get_local_ip()

# MAS API
MAS_API = "http://192.168.0.188:8001"

# Registration payload
registration = {
    "name": f"claude-code-local-{hostname}",
    "type": "coding_executor",
    "endpoint": f"http://{local_ip}:8350",
    "capabilities": [
        "create_agent",
        "fix_bug",
        "create_endpoint",
        "create_skill",
        "refactor",
        "test",
        "deploy"
    ],
    "metadata": {
        "hostname": hostname,
        "os": os.name,
        "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}",
        "location": "local_dev_machine",
        "parallel_capacity": 3,
        "max_turns_per_task": 30,
        "budget_per_task_usd": 5.0
    }
}

print(f"Registering local Claude Code instance with MAS...")
print(f"  Hostname: {hostname}")
print(f"  Local IP: {local_ip}")
print(f"  Endpoint: http://{local_ip}:8350")
print(f"  MAS API: {MAS_API}")

try:
    # Register with MAS
    response = requests.post(
        f"{MAS_API}/api/registry/services",
        json=registration,
        timeout=10
    )
    
    if response.status_code in [200, 201]:
        print("\n✓ Successfully registered with MAS!")
        print("\nMAS can now route coding tasks to this machine.")
        print("\nNext steps:")
        print("1. Ensure API bridge is running: python scripts/claude-code-api-bridge.py")
        print("2. Start autonomous service: .\\scripts\\claude-code-service.ps1")
        print("3. Test from MAS: curl -X POST http://{local_ip}:8350/task ...")
    else:
        print(f"\n⚠ Registration returned status {response.status_code}")
        print(f"Response: {response.text}")
        
except requests.exceptions.ConnectionError:
    print(f"\n✗ Could not connect to MAS API at {MAS_API}")
    print("Ensure MAS VM (192.168.0.188:8001) is running and accessible.")
except Exception as e:
    print(f"\n✗ Registration failed: {e}")

print("\nTo verify registration:")
print(f"curl {MAS_API}/api/registry/services")
