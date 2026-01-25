#!/usr/bin/env python3
"""
Fix the /app/website build error and deploy.
The error is coming from a stale .next cache. We need to clean it.
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

def exec_cmd(cmd, timeout=300):
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
            time.sleep(3)
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
            elapsed = int(time.time() - start)
            if elapsed > 0 and elapsed % 30 == 0:
                print(f"    ... {elapsed}s elapsed ...")
        return None, "Timeout"
    except Exception as e:
        return None, str(e)

print("=" * 60)
print("  FIX BUILD ERROR AND DEPLOY")
print("=" * 60)

# Step 1: Clean .next cache on VM
log("STEP 1: Cleaning .next cache on VM...")
code, out = exec_cmd("cd /home/mycosoft/mycosoft/website && rm -rf .next node_modules/.cache 2>&1 && echo 'Cache cleaned'")
print(f"    {out.strip() if out else 'Done'}")

# Step 2: Clean all Docker build cache
log("STEP 2: Cleaning Docker build cache completely...")
code, out = exec_cmd("docker builder prune -a -f 2>&1 | tail -3")
print(f"    {out.strip() if out else 'Done'}")

# Step 3: Remove old website images
log("STEP 3: Removing old website Docker images...")
code, out = exec_cmd("docker images | grep -E 'mycosoft.*website|always-on.*website' | awk '{print $3}' | xargs -r docker rmi -f 2>&1 | tail -5")
print(f"    {out.strip() if out else 'No images to remove'}")

# Step 4: Fresh git pull
log("STEP 4: Fresh git pull...")
code, out = exec_cmd("export HOME=/root && cd /home/mycosoft/mycosoft/website && git fetch origin && git reset --hard origin/main && git log --oneline -1")
print(f"    {out.strip() if out else 'Done'}")

# Step 5: Build with no cache
log("STEP 5: Building Docker image (this takes 2-5 minutes)...")
code, out = exec_cmd(
    "cd /home/mycosoft/mycosoft/mas && docker compose -f docker-compose.always-on.yml build mycosoft-website --no-cache 2>&1",
    timeout=600
)
if code == 0:
    log("    BUILD SUCCESS!")
else:
    log(f"    BUILD RESULT (code={code}):")
    # Show last 30 lines
    lines = (out or "").strip().split('\n')
    for line in lines[-30:]:
        print(f"    {line}")

# Step 6: Start container
log("STEP 6: Starting container...")
code, out = exec_cmd(
    "cd /home/mycosoft/mycosoft/mas && docker compose -f docker-compose.always-on.yml up -d --force-recreate mycosoft-website 2>&1",
    timeout=120
)
print(f"    {out.strip()[:200] if out else 'Done'}")

# Step 7: Verify
log("STEP 7: Verifying container...")
time.sleep(10)
code, out = exec_cmd("docker ps --format 'table {{.Names}}\t{{.Status}}' | grep website")
print(f"    {out.strip() if out else 'Container not found'}")

# Step 8: Health check
log("STEP 8: Health check...")
code, out = exec_cmd("curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/")
print(f"    HTTP Response: {out.strip() if out else 'No response'}")

print("\n" + "=" * 60)
print("  DEPLOYMENT COMPLETE")
print("  Remember to purge Cloudflare cache!")
print("=" * 60)
