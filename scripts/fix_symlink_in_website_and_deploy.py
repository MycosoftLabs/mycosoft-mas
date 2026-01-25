#!/usr/bin/env python3
"""
Fix the bad symlink INSIDE the website directory and rebuild.
The symlink /home/mycosoft/mycosoft/website/website is causing Docker to copy it,
which creates /app/website in the container, breaking the Next.js build.
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
print("  FIX BAD SYMLINK AND REBUILD")
print("=" * 60)

# Step 1: Check and remove the bad symlink
log("STEP 1: Checking bad symlink inside website directory...")
code, out = exec_cmd("ls -la /home/mycosoft/mycosoft/website/website 2>&1")
print(f"    Current: {out.strip() if out else 'Not found'}")

log("STEP 2: Removing bad symlink...")
code, out = exec_cmd("rm -f /home/mycosoft/mycosoft/website/website && echo 'Removed' || echo 'Not found'")
print(f"    {out.strip() if out else 'Done'}")

# Verify removal
code, out = exec_cmd("ls -la /home/mycosoft/mycosoft/website/website 2>&1")
print(f"    After removal: {out.strip() if out else 'Successfully removed'}")

# Step 3: Clean Docker build cache completely
log("STEP 3: Cleaning ALL Docker build cache...")
code, out = exec_cmd("docker builder prune -a -f 2>&1 | tail -3")
print(f"    {out.strip() if out else 'Done'}")

# Step 4: Build
log("STEP 4: Building Docker image (2-5 minutes)...")
code, out = exec_cmd(
    "cd /home/mycosoft/mycosoft/mas && docker compose -f docker-compose.always-on.yml build mycosoft-website --no-cache 2>&1",
    timeout=600
)
if code == 0:
    log("    BUILD SUCCESS!")
    # Show last few lines
    lines = (out or "").strip().split('\n')
    for line in lines[-5:]:
        print(f"    {line}")
else:
    log(f"    BUILD RESULT (code={code}):")
    lines = (out or "").strip().split('\n')
    for line in lines[-20:]:
        print(f"    {line}")

# Step 5: Start container
log("STEP 5: Starting container...")
code, out = exec_cmd(
    "cd /home/mycosoft/mycosoft/mas && docker compose -f docker-compose.always-on.yml up -d --force-recreate mycosoft-website 2>&1",
    timeout=120
)
lines = (out or "").strip().split('\n')
for line in lines[-3:]:
    print(f"    {line}")

# Step 6: Verify
log("STEP 6: Verifying container...")
time.sleep(15)
code, out = exec_cmd("docker ps --format 'table {{.Names}}\t{{.Status}}' | grep website")
print(f"    {out.strip() if out else 'Container not found'}")

# Step 7: Health check
log("STEP 7: Health check...")
code, out = exec_cmd("curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/")
http_code = out.strip() if out else "No response"
print(f"    HTTP Response: {http_code}")

if "200" in http_code:
    print("\n" + "=" * 60)
    print("  SUCCESS! Website is running.")
    print("  Now purge Cloudflare cache at dash.cloudflare.com")
    print("=" * 60)
else:
    print("\n" + "=" * 60)
    print("  Container may still be starting. Check logs.")
    print("=" * 60)
