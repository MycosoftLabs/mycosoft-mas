#!/usr/bin/env python3
"""Force rebuild website container with new code"""
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
print("  REBUILD WEBSITE WITH NEW CODE")
print("=" * 60)

# Step 1: Find docker-compose location
print("\n[1/5] Finding docker-compose location...")
out, err = exec_cmd("find /home -name 'docker-compose.always-on.yml' 2>/dev/null", timeout=30)
if out:
    compose_path = out.strip().split('\n')[0]
    compose_dir = '/'.join(compose_path.split('/')[:-1])
    print(f"  Found: {compose_path}")
    print(f"  Dir: {compose_dir}")
else:
    compose_dir = "/home/mycosoft/WEBSITE/website"
    print(f"  Using default: {compose_dir}")

# Step 2: Verify latest code is there
print("\n[2/5] Checking latest code...")
out, err = exec_cmd(f"cd {compose_dir} && git log --oneline -1", timeout=30)
if out:
    print(f"  Commit: {out.strip()}")
else:
    print(f"  Error: {err}")

# Step 3: Stop existing container
print("\n[3/5] Stopping container...")
out, err = exec_cmd(f"cd {compose_dir} && docker compose -f docker-compose.always-on.yml stop mycosoft-website 2>&1", timeout=60)
if out:
    print(f"  {out.strip()}")

# Step 4: Remove old image to force rebuild
print("\n[4/5] Removing old image and rebuilding (this takes 2-4 min)...")
out, err = exec_cmd(f"""
cd {compose_dir}
docker rmi mycosoft-website:latest 2>/dev/null || true
docker compose -f docker-compose.always-on.yml build mycosoft-website --no-cache 2>&1 | grep -E "(Step|Successfully|DONE|FROM|error|Error)" | tail -15
""", timeout=600)
if out:
    for line in out.strip().split('\n')[-10:]:
        print(f"  {line}")
else:
    print(f"  Timeout or error: {err}")

# Step 5: Start container
print("\n[5/5] Starting container...")
out, err = exec_cmd(f"cd {compose_dir} && docker compose -f docker-compose.always-on.yml up -d mycosoft-website 2>&1", timeout=60)
if out:
    print(f"  {out.strip()}")

# Verify
print("\n[*] Verification...")
time.sleep(10)
out, err = exec_cmd("docker ps --format '{{.Names}}: {{.Status}}' | grep website", timeout=30)
if out:
    print(f"  Container: {out.strip()}")

print("\n" + "=" * 60)
print("  DONE - Test: https://sandbox.mycosoft.com/security")
print("=" * 60)
