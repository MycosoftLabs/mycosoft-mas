#!/usr/bin/env python3
"""Simple check for Quadruped in container."""
import requests
import urllib3
import time
import base64
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
urllib3.disable_warnings()

PROXMOX_HOST = "https://192.168.0.202:8006"
PROXMOX_TOKEN_ID = "myca@pve!mas"
PROXMOX_TOKEN_SECRET = "ca23b6c8-5746-46c4-8e36-fc6caad5a9e5"
VM_ID = 103
NODE = "pve"

headers = {"Authorization": f"PVEAPIToken={PROXMOX_TOKEN_ID}={PROXMOX_TOKEN_SECRET}"}

def exec_cmd(cmd, timeout=60):
    url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/exec"
    try:
        data = {"command": "/bin/bash", "input-data": cmd}
        r = requests.post(url, headers=headers, data=data, verify=False, timeout=15)
        if not r.ok:
            print(f"Request failed: {r.status_code}")
            return None
        pid = r.json().get("data", {}).get("pid")
        if not pid:
            print("No PID returned")
            return None
        
        status_url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/exec-status?pid={pid}"
        start = time.time()
        while time.time() - start < timeout:
            time.sleep(2)
            sr = requests.get(status_url, headers=headers, verify=False, timeout=10)
            if sr.ok:
                sd = sr.json().get("data", {})
                if sd.get("exited"):
                    out = sd.get("out-data", "")
                    try:
                        if out:
                            out = base64.b64decode(out).decode('utf-8', errors='replace')
                    except:
                        pass
                    return out
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

# Very simple test
print("Test 1 - Echo test:")
result = exec_cmd("echo 'Hello World'")
print(f"Result: '{result}'")

print("\nTest 2 - Check JS chunks in container:")
result = exec_cmd("docker exec mycosoft-website ls /app/.next/static/chunks/ 2>&1 | head -5")
print(f"Result: '{result}'")

print("\nTest 3 - Search for Quadruped in chunks:")
result = exec_cmd("docker exec mycosoft-website sh -c 'grep -l Quadruped /app/.next/static/chunks/*.js 2>/dev/null || echo NONE'")
print(f"Result: '{result}'")

print("\nTest 4 - Fetch page and count bytes:")
result = exec_cmd("curl -s http://localhost:3000/devices/mushroom-1 2>/dev/null | wc -c")
print(f"Page size (bytes): '{result}'")
