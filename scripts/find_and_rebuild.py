#!/usr/bin/env python3
"""Find docker-compose location and rebuild"""
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
print("  FIND AND REBUILD")
print("=" * 60)

# Step 1: Find docker-compose.always-on.yml
print("\n[1/4] Finding docker-compose files...")
out, err = exec_cmd("find /home -name 'docker-compose*.yml' 2>/dev/null | head -10", timeout=30)
if out:
    for line in out.strip().split('\n'):
        print(f"  {line}")

# Step 2: Check where the website compose file is
print("\n[2/4] Finding website compose context...")
out, err = exec_cmd("docker inspect mycosoft-always-on-mycosoft-website-1 --format '{{.Config.Labels}}' 2>/dev/null | tr ',' '\n' | grep -i project", timeout=30)
if out:
    print(f"  {out.strip()}")

# Check the working directory for the compose project
out, err = exec_cmd("docker inspect mycosoft-always-on-mycosoft-website-1 --format '{{index .Config.Labels \"com.docker.compose.project.working_dir\"}}' 2>/dev/null", timeout=30)
if out:
    print(f"  Compose working dir: {out.strip()}")
    compose_dir = out.strip()
else:
    compose_dir = "/home/mycosoft/WEBSITE/website"

# Step 3: Rebuild from correct location
print(f"\n[3/4] Rebuilding from {compose_dir}...")
cmd = f'''
cd {compose_dir}
docker compose -f docker-compose.always-on.yml build mycosoft-website --no-cache 2>&1 | grep -E "(Step|Successfully|DONE|error)" | tail -10
'''
out, err = exec_cmd(cmd, timeout=300)
if out:
    for line in out.strip().split('\n')[-5:]:
        print(f"  {line}")
else:
    print(f"  Building or timeout: {err}")

# Step 4: Restart container
print(f"\n[4/4] Restarting container...")
cmd = f'''
cd {compose_dir}
docker compose -f docker-compose.always-on.yml up -d mycosoft-website 2>&1
'''
out, err = exec_cmd(cmd, timeout=60)
if out:
    print(f"  {out.strip()}")
else:
    print(f"  Error: {err}")

# Verify
print("\n[*] Final status...")
time.sleep(10)
out, err = exec_cmd("docker ps --format '{{.Names}}: {{.Status}}' | grep website", timeout=30)
if out:
    print(f"  Container: {out.strip()}")

print("\n" + "=" * 60)
print("  DONE - Test: https://sandbox.mycosoft.com/security")
print("=" * 60)
