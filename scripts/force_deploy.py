#!/usr/bin/env python3
"""Force deploy: Kill stale builds and do a clean deploy"""
import requests
import urllib3
import time
urllib3.disable_warnings()

PROXMOX_HOST = "https://192.168.0.202:8006"
headers = {"Authorization": "PVEAPIToken=myca@pve!mas=ca23b6c8-5746-46c4-8e36-fc6caad5a9e5"}
VM_ID = 103
NODE = "pve"

def exec_cmd(cmd, timeout=300):
    url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/exec"
    try:
        data = {"command": "/bin/bash", "input-data": cmd}
        r = requests.post(url, headers=headers, data=data, verify=False, timeout=10)
        if not r.ok:
            return None, f"Failed: {r.status_code}"
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
                    stdout = result.get("out-data", "")
                    stderr = result.get("err-data", "")
                    return stdout + stderr, None
        return None, "Timeout"
    except Exception as e:
        return None, str(e)

print("=" * 60)
print("  FORCE DEPLOY - Clean Build")
print("=" * 60)

# Step 1: Kill any stale docker build processes
print("\n[1/5] Killing stale build processes...")
out, err = exec_cmd("pkill -f docker-buildx; pkill -f 'docker compose.*build'; echo DONE", timeout=30)
print(f"  Result: {out.strip() if out else err}")

# Step 2: Git pull
print("\n[2/5] Pulling latest code...")
out, err = exec_cmd("cd /home/mycosoft/mycosoft/website && git fetch origin && git reset --hard origin/main 2>&1 | tail -5", timeout=60)
if out:
    print(f"  {out.strip()}")
else:
    print(f"  Error: {err}")

# Step 3: Stop existing container
print("\n[3/5] Stopping existing container...")
out, err = exec_cmd("cd /home/mycosoft/mycosoft/website && docker compose -f docker-compose.always-on.yml stop mycosoft-website 2>&1 | tail -3", timeout=60)
print(f"  {out.strip() if out else err}")

# Step 4: Rebuild (this takes time)
print("\n[4/5] Building Docker image (this takes ~2-3 minutes)...")
out, err = exec_cmd("cd /home/mycosoft/mycosoft/website && docker compose -f docker-compose.always-on.yml build mycosoft-website --no-cache 2>&1 | tail -20", timeout=300)
if out:
    print(f"  {out.strip()}")
else:
    print(f"  Error/Timeout: {err}")

# Step 5: Start container
print("\n[5/5] Starting container...")
out, err = exec_cmd("cd /home/mycosoft/mycosoft/website && docker compose -f docker-compose.always-on.yml up -d mycosoft-website 2>&1", timeout=60)
if out:
    print(f"  {out.strip()}")
else:
    print(f"  Error: {err}")

# Verify
print("\n[*] Verifying deployment...")
time.sleep(5)
out, err = exec_cmd("docker ps --format '{{.Names}}: {{.Status}}' | grep website", timeout=30)
if out:
    print(f"  Container: {out.strip()}")
else:
    print(f"  Error: {err}")

print("\n" + "=" * 60)
print("  DEPLOYMENT COMPLETE")
print("=" * 60)
print("\nTest: https://sandbox.mycosoft.com/security")
