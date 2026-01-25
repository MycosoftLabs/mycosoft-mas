#!/usr/bin/env python3
"""Fix docker-compose location - website should build from website repo"""
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
print("  FIX COMPOSE LOCATION & REBUILD")
print("=" * 60)

# Step 1: Check where website code is
print("\n[1/6] Finding website locations...")
out, err = exec_cmd("find /home -type d -name 'website' 2>/dev/null | head -5", timeout=30)
if out:
    for line in out.strip().split('\n'):
        print(f"  {line}")

# Step 2: Check if website repo has docker-compose
print("\n[2/6] Checking website repo for compose files...")
out, err = exec_cmd("ls -la /home/mycosoft/mycosoft/website/docker*.yml /home/mycosoft/mycosoft/website/docker-compose*.yml 2>/dev/null | head -5", timeout=30)
if out:
    for line in out.strip().split('\n'):
        print(f"  {line}")
else:
    print(f"  No compose files found in website repo")

# Step 3: Check where current compose is running from
print("\n[3/6] Current compose project info...")
out, err = exec_cmd("docker inspect mycosoft-always-on-mycosoft-website-1 --format '{{.Config.Labels}}' 2>/dev/null | tr ',' '\\n' | grep -E '(project|config)' | head -5", timeout=30)
if out:
    for line in out.strip().split('\n'):
        print(f"  {line}")

# Step 4: Get the commit in the WEBSITE repo
print("\n[4/6] Website repo git status...")
out, err = exec_cmd("cd /home/mycosoft/mycosoft/website && git config --global --add safe.directory /home/mycosoft/mycosoft/website && git log --oneline -1 2>&1", timeout=30)
if out:
    print(f"  {out.strip()}")

# Step 5: Stop old container, use website repo's compose
print("\n[5/6] Rebuilding from WEBSITE repo...")
out, err = exec_cmd("""
cd /home/mycosoft/mycosoft/website

# Stop old containers if running
docker compose -f docker-compose.always-on.yml down 2>/dev/null || true

# Check if compose file exists
if [ -f docker-compose.always-on.yml ]; then
    echo "Found docker-compose.always-on.yml"
    docker compose -f docker-compose.always-on.yml build mycosoft-website --no-cache 2>&1 | tail -10
    docker compose -f docker-compose.always-on.yml up -d mycosoft-website 2>&1
else
    echo "ERROR: No docker-compose.always-on.yml in website repo"
    echo "Need to copy from MAS or create one"
fi
""", timeout=600)
if out:
    for line in out.strip().split('\n'):
        print(f"  {line}")
else:
    print(f"  Error: {err}")

# Step 6: Verify
print("\n[6/6] Verification...")
time.sleep(10)
out, err = exec_cmd("docker ps --format '{{.Names}}: {{.Status}}' | grep -i website", timeout=30)
if out:
    print(f"  Container: {out.strip()}")

print("\n" + "=" * 60)
print("  DONE")
print("=" * 60)
