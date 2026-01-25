#!/usr/bin/env python3
"""Check the actual page content for Quadruped vs Tripod."""
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
            return None
        pid = r.json().get("data", {}).get("pid")
        if not pid:
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
                    if out:
                        print(out)
                    return out
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

print("="*60)
print("CHECKING PAGE CONTENT")
print("="*60)

# Check for both Tripod and Quadruped in the page
print("\n[1] Searching for 'Tripod' in page HTML...")
exec_cmd("curl -s http://localhost:3000/devices/mushroom-1 2>/dev/null | grep -c 'Tripod' || echo '0'")

print("\n[2] Searching for 'Quadruped' in page HTML...")
exec_cmd("curl -s http://localhost:3000/devices/mushroom-1 2>/dev/null | grep -c 'Quadruped' || echo '0'")

print("\n[3] Getting context around 'Legs' in page HTML...")
exec_cmd("curl -s http://localhost:3000/devices/mushroom-1 2>/dev/null | grep -o '.{0,20}Legs.{0,20}' | head -3")

print("\n[4] Check if Next.js is caching the page - checking .next folder...")
exec_cmd("ls -la /home/mycosoft/mycosoft/website/.next/server/pages/devices/ 2>/dev/null | head -5 || echo 'No prerendered pages'")

print("\n[5] Check if build includes Quadruped in bundled JS...")
exec_cmd("docker exec mycosoft-website grep -r 'Quadruped' /app/.next/static/chunks/*.js 2>/dev/null | head -2 || echo 'Not found in JS'")

print("\n[6] Check container's source files...")
exec_cmd("docker exec mycosoft-website cat /app/components/devices/mushroom1-details.tsx 2>/dev/null | grep -A2 'id: \"legs\"' | head -5 || echo 'Cannot read file'")

print("\n" + "="*60)
