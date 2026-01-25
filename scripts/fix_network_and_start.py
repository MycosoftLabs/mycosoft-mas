#!/usr/bin/env python3
"""
Create the missing network and start the container.
"""
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

def log(msg):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

def exec_cmd(cmd, timeout=120):
    url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/exec"
    try:
        data = {"command": "/bin/bash", "input-data": cmd}
        r = requests.post(url, headers=headers, data=data, verify=False, timeout=10)
        if not r.ok:
            return None, f"Exec failed: {r.status_code}"
        pid = r.json().get("data", {}).get("pid")
        if not pid:
            return None, "No PID"
        
        status_url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/exec-status?pid={pid}"
        start = time.time()
        while time.time() - start < timeout:
            time.sleep(2)
            r2 = requests.get(status_url, headers=headers, verify=False, timeout=10)
            if r2.ok:
                result = r2.json().get("data", {})
                if result.get("exited"):
                    out_b64 = result.get("out-data", "")
                    err_b64 = result.get("err-data", "")
                    try:
                        out = base64.b64decode(out_b64).decode() if out_b64 else ""
                    except:
                        out = out_b64
                    try:
                        err = base64.b64decode(err_b64).decode() if err_b64 else ""
                    except:
                        err = err_b64
                    return result.get("exitcode", 0), out + err
        return None, "Timeout"
    except Exception as e:
        return None, str(e)

print("=" * 60)
print("  FIX NETWORK AND START CONTAINER")
print("=" * 60)

# Step 1: Create the missing network
log("STEP 1: Creating missing Docker network...")
code, out = exec_cmd("docker network create mycosoft-mas_mas-network 2>&1 || echo 'Network already exists or created'")
print(f"    {out.strip() if out else 'Done'}")

# Step 2: Also try the always-on network
log("STEP 2: Creating always-on network if needed...")
code, out = exec_cmd("docker network create mycosoft-always-on_default 2>&1 || echo 'Already exists'")
print(f"    {out.strip() if out else 'Done'}")

# Step 3: Start the container
log("STEP 3: Starting website container...")
code, out = exec_cmd(
    "cd /home/mycosoft/mycosoft/mas && docker compose -f docker-compose.always-on.yml up -d mycosoft-website 2>&1",
    timeout=60
)
lines = (out or "").strip().split('\n')
for line in lines[-5:]:
    print(f"    {line}")

# Step 4: Verify
log("STEP 4: Verifying container...")
time.sleep(10)
code, out = exec_cmd("docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -E 'website|NAMES'")
print(f"    {out.strip() if out else 'Container not found'}")

# Step 5: Health check
log("STEP 5: Health check...")
time.sleep(5)
code, out = exec_cmd("curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/")
http_code = out.strip() if out else "000"
print(f"    HTTP Response: {http_code}")

# Step 6: Show logs if not healthy
if "200" not in http_code:
    log("STEP 6: Showing container logs...")
    code, out = exec_cmd("docker logs mycosoft-always-on-mycosoft-website-1 --tail 20 2>&1")
    print(f"    {out if out else 'No logs'}")
else:
    print("\n" + "=" * 60)
    print("  SUCCESS! Website is running on port 3000.")
    print("  Now purge Cloudflare cache!")
    print("=" * 60)
