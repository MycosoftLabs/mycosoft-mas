#!/usr/bin/env python3
"""Fix git ownership and deploy with fresh code"""
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
print("  FIX GIT & DEPLOY")
print("=" * 60)

# Step 1: Fix git safe directory
print("\n[1/6] Fixing git safe directory...")
out, err = exec_cmd("git config --global --add safe.directory /home/mycosoft/mycosoft/website && echo 'Git safe.directory configured'", timeout=30)
print(f"  {out.strip() if out else err}")

# Step 2: Git pull
print("\n[2/6] Pulling latest code...")
out, err = exec_cmd("cd /home/mycosoft/mycosoft/website && git fetch origin && git reset --hard origin/main 2>&1", timeout=60)
if out:
    lines = out.strip().split('\n')
    for line in lines[-5:]:
        print(f"  {line}")
else:
    print(f"  Error: {err}")

# Step 3: Check what changed
print("\n[3/6] Recent commits:")
out, err = exec_cmd("cd /home/mycosoft/mycosoft/website && git log --oneline -3", timeout=30)
if out:
    for line in out.strip().split('\n'):
        print(f"  {line}")

# Step 4: Stop and rebuild
print("\n[4/6] Rebuilding container (this takes ~2-3 min)...")
out, err = exec_cmd("""
cd /home/mycosoft/mycosoft/website
docker compose -f docker-compose.always-on.yml stop mycosoft-website
docker compose -f docker-compose.always-on.yml build mycosoft-website --no-cache 2>&1 | tail -10
""", timeout=300)
if out:
    for line in out.strip().split('\n')[-5:]:
        print(f"  {line}")
else:
    print(f"  Error/Timeout: {err}")

# Step 5: Start container
print("\n[5/6] Starting container...")
out, err = exec_cmd("cd /home/mycosoft/mycosoft/website && docker compose -f docker-compose.always-on.yml up -d mycosoft-website 2>&1", timeout=60)
if out:
    print(f"  {out.strip()}")
else:
    print(f"  Error: {err}")

# Step 6: Verify
print("\n[6/6] Verifying...")
time.sleep(8)
out, err = exec_cmd("docker ps --format '{{.Names}}: {{.Status}}' | grep website", timeout=30)
if out:
    print(f"  {out.strip()}")
else:
    print(f"  Error: {err}")

# Check memory
print("\n[*] Memory status:")
out, err = exec_cmd("free -h | head -2", timeout=30)
if out:
    print(out.strip())

print("\n" + "=" * 60)
print("  DONE - Test: https://sandbox.mycosoft.com/security")
print("=" * 60)
