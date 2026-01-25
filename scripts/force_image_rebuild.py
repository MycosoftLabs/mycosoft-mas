#!/usr/bin/env python3
"""Force delete old image and rebuild"""
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
print("  FORCE IMAGE REBUILD")
print("=" * 60)

# Step 1: Stop container and remove it
print("\n[1/4] Stopping and removing container...")
out, err = exec_cmd("""
cd /home/mycosoft/mycosoft/mas_old/mas
docker compose -f docker-compose.always-on.yml stop mycosoft-website 2>&1
docker compose -f docker-compose.always-on.yml rm -f mycosoft-website 2>&1
""", timeout=60)
if out:
    for line in out.strip().split('\n')[-5:]:
        print(f"  {line}")

# Step 2: Delete all website images
print("\n[2/4] Deleting old images...")
out, err = exec_cmd("""
# Find and delete website images
docker images | grep -i website
docker images | grep -i website | awk '{print $3}' | xargs docker rmi -f 2>/dev/null || true
docker images | grep -i mycosoft-always-on | awk '{print $3}' | xargs docker rmi -f 2>/dev/null || true
echo "Images after cleanup:"
docker images | grep -E "(website|mycosoft)" | head -5 || echo "No website images"
""", timeout=60)
if out:
    for line in out.strip().split('\n'):
        print(f"  {line}")

# Step 3: Build fresh image
print("\n[3/4] Building fresh image (3-5 min)...")
out, err = exec_cmd("""
cd /home/mycosoft/mycosoft/mas_old/mas
docker compose -f docker-compose.always-on.yml build mycosoft-website --no-cache 2>&1 | tail -30
""", timeout=600)
if out:
    for line in out.strip().split('\n')[-15:]:
        print(f"  {line}")
else:
    print(f"  Timeout or error: {err}")

# Step 4: Start container
print("\n[4/4] Starting container...")
out, err = exec_cmd("""
cd /home/mycosoft/mycosoft/mas_old/mas
docker compose -f docker-compose.always-on.yml up -d mycosoft-website 2>&1
""", timeout=60)
if out:
    for line in out.strip().split('\n')[-10:]:
        print(f"  {line}")

# Verify
print("\n[*] Waiting for container to be healthy...")
time.sleep(15)
out, err = exec_cmd("docker ps --format '{{.Names}}: {{.Status}}' | grep website", timeout=30)
if out:
    print(f"  {out.strip()}")

print("\n" + "=" * 60)
print("  DONE - Test: https://sandbox.mycosoft.com/security")
print("=" * 60)
