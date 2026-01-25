#!/usr/bin/env python3
"""Fix container startup by starting all services in compose."""
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

def exec_cmd(cmd, timeout=180):
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
            time.sleep(3)
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

print("="*60)
print("FIXING CONTAINER STARTUP")
print("="*60)

# First check current state
print("\n[1] Checking current container state...")
out = exec_cmd("docker ps -a | head -10")
print(out or "No output")

# Start ALL services in compose (this creates the network)
print("\n[2] Starting ALL services in docker-compose.always-on.yml...")
out = exec_cmd("""
cd /home/mycosoft/mycosoft/mas &&
docker compose -f docker-compose.always-on.yml up -d 2>&1
""", timeout=300)
print(out or "No output")

# Wait for startup
print("\n[3] Waiting 30 seconds for containers to start...")
time.sleep(30)

# Check containers
print("\n[4] Checking container status...")
out = exec_cmd("docker ps --format 'table {{.Names}}\t{{.Status}}'")
print(out or "No output")

# Check website specifically
print("\n[5] Testing website locally...")
out = exec_cmd("curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/ 2>/dev/null")
print(f"HTTP Response: {out or 'FAIL'}")

if out and "200" in out:
    print("\n" + "="*60)
    print("[SUCCESS] Website container is running!")
    print("="*60)
    print("\nPlease purge Cloudflare cache and check sandbox.mycosoft.com")
else:
    print("\n[6] Checking website logs...")
    out = exec_cmd("docker logs $(docker ps -a | grep website | awk '{print $1}' | head -1) --tail 30 2>&1")
    print(out or "No logs")
