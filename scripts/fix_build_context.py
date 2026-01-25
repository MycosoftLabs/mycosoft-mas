#!/usr/bin/env python3
"""Fix the build context to use correct website repo"""
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
            if elapsed % 30 == 0:
                print(f"    ... {elapsed}s elapsed")
        return None, "Timeout"
    except Exception as e:
        return None, str(e)

print("=" * 60)
print("  FIX BUILD CONTEXT")
print("=" * 60)

# Step 1: Check current compose file content
print("\n[1/5] Current compose file location and website service...")
out, err = exec_cmd("grep -A 20 'mycosoft-website:' /home/mycosoft/mycosoft/mas_old/mas/docker-compose.always-on.yml 2>/dev/null | head -25", timeout=30)
if out:
    for line in out.strip().split('\n'):
        print(f"  {line}")

# Step 2: Check if there's a symlink or can create one
print("\n[2/5] Creating symlink for website code...")
out, err = exec_cmd("""
# Remove old symlink if exists
rm -f /home/mycosoft/WEBSITE/website 2>/dev/null

# Create symlink pointing to actual website repo  
mkdir -p /home/mycosoft/WEBSITE
ln -sf /home/mycosoft/mycosoft/website /home/mycosoft/WEBSITE/website

# Verify
ls -la /home/mycosoft/WEBSITE/website | head -3
""", timeout=30)
if out:
    print(f"  {out.strip()}")

# Step 3: Check the website repo has latest code
print("\n[3/5] Verify website repo has latest code...")
out, err = exec_cmd("""
export HOME=/root
git config --global --add safe.directory /home/mycosoft/mycosoft/website
cd /home/mycosoft/mycosoft/website && git log --oneline -3
""", timeout=30)
if out:
    for line in out.strip().split('\n'):
        print(f"  {line}")

# Step 4: Rebuild from the MAS compose (which should now use symlink)
print("\n[4/5] Rebuilding (3-5 min)...")
out, err = exec_cmd("""
cd /home/mycosoft/mycosoft/mas_old/mas
docker compose -f docker-compose.always-on.yml stop mycosoft-website
docker rmi $(docker images -q mycosoft-website) 2>/dev/null || true
docker compose -f docker-compose.always-on.yml build mycosoft-website --no-cache 2>&1 | grep -E "(Step|FROM|Successfully|DONE|error)" | tail -15
""", timeout=600)
if out:
    for line in out.strip().split('\n')[-10:]:
        print(f"  {line}")
else:
    print(f"  Timeout: {err}")

# Step 5: Start container
print("\n[5/5] Starting container...")
out, err = exec_cmd("cd /home/mycosoft/mycosoft/mas_old/mas && docker compose -f docker-compose.always-on.yml up -d mycosoft-website 2>&1 | tail -10", timeout=60)
if out:
    for line in out.strip().split('\n'):
        print(f"  {line}")

# Verify
print("\n[*] Verification...")
time.sleep(15)
out, err = exec_cmd("docker ps --format '{{.Names}}: {{.Status}}' | grep website", timeout=30)
if out:
    print(f"  Container: {out.strip()}")

print("\n" + "=" * 60)
print("  DONE")
print("=" * 60)
