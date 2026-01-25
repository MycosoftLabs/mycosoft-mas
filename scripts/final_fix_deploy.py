#!/usr/bin/env python3
"""Final fix: correct symlink path and rebuild"""
import requests
import urllib3
import time
urllib3.disable_warnings()

PROXMOX_HOST = "https://192.168.0.202:8006"
headers = {"Authorization": "PVEAPIToken=myca@pve!mas=ca23b6c8-5746-46c4-8e36-fc6caad5a9e5"}
VM_ID = 103
NODE = "pve"

def exec_cmd(cmd, timeout=600):
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
            time.sleep(3)
            r2 = requests.get(status_url, headers=headers, verify=False, timeout=10)
            if r2.ok:
                result = r2.json().get("data", {})
                if result.get("exited"):
                    stdout = result.get("out-data", "")
                    stderr = result.get("err-data", "")
                    return stdout + stderr, None
            elapsed = int(time.time() - start)
            if elapsed % 60 == 0:
                print(f"    ... {elapsed}s elapsed")
        return None, "Timeout"
    except Exception as e:
        return None, str(e)

print("=" * 60)
print("  FINAL FIX: CORRECT SYMLINK & REBUILD")
print("=" * 60)

# Step 1: Fix the symlink to correct location
# Compose file is at: /home/mycosoft/mycosoft/mas_old/mas/docker-compose.always-on.yml
# Build context is: ../../WEBSITE/website
# So full path is: /home/mycosoft/mycosoft/WEBSITE/website
print("\n[1/4] Creating correct symlink...")
out, err = exec_cmd("""
# Remove any existing
rm -rf /home/mycosoft/mycosoft/WEBSITE 2>/dev/null

# Create WEBSITE directory and symlink
mkdir -p /home/mycosoft/mycosoft/WEBSITE
ln -sf /home/mycosoft/mycosoft/website /home/mycosoft/mycosoft/WEBSITE/website

# Verify symlink points to correct location
echo "Symlink:"
ls -la /home/mycosoft/mycosoft/WEBSITE/website

echo ""
echo "Website repo commit:"
cd /home/mycosoft/mycosoft/WEBSITE/website && git log --oneline -1 2>/dev/null || echo "Git check failed"
""", timeout=30)
if out:
    for line in out.strip().split('\n'):
        print(f"  {line}")

# Step 2: Stop and remove container
print("\n[2/4] Stopping container...")
out, err = exec_cmd("""
cd /home/mycosoft/mycosoft/mas_old/mas
docker compose -f docker-compose.always-on.yml stop mycosoft-website 2>&1 | tail -3
docker compose -f docker-compose.always-on.yml rm -f mycosoft-website 2>&1 | tail -3
""", timeout=60)
if out:
    print(f"  {out.strip()}")

# Step 3: Build fresh
print("\n[3/4] Building (3-5 min)...")
out, err = exec_cmd("""
cd /home/mycosoft/mycosoft/mas_old/mas
docker compose -f docker-compose.always-on.yml build mycosoft-website --no-cache 2>&1 | tail -25
""", timeout=600)
if out:
    for line in out.strip().split('\n')[-15:]:
        print(f"  {line}")
else:
    print(f"  Timeout: {err}")

# Step 4: Start container
print("\n[4/4] Starting container...")
out, err = exec_cmd("""
cd /home/mycosoft/mycosoft/mas_old/mas
docker compose -f docker-compose.always-on.yml up -d mycosoft-website 2>&1 | tail -10
""", timeout=60)
if out:
    for line in out.strip().split('\n'):
        print(f"  {line}")

# Verify
print("\n[*] Waiting for healthy...")
time.sleep(20)
out, err = exec_cmd("docker ps --format '{{.Names}}: {{.Status}}' | grep website", timeout=30)
if out:
    print(f"  {out.strip()}")

print("\n" + "=" * 60)
print("  DONE - Test: https://sandbox.mycosoft.com/security")
print("=" * 60)
