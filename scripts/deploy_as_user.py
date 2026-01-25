#!/usr/bin/env python3
"""Deploy as mycosoft user to fix git ownership issues"""
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
print("  DEPLOY AS MYCOSOFT USER")
print("=" * 60)

# Step 1: Fix git ownership by setting safe.directory globally for all users
print("\n[1/5] Fixing git ownership...")
cmd = '''
# Add safe directory for all users
echo '[safe]' >> /etc/gitconfig
echo '    directory = /home/mycosoft/mycosoft/website' >> /etc/gitconfig
echo '    directory = /home/mycosoft/mycosoft/mas' >> /etc/gitconfig
echo '    directory = /home/mycosoft/WEBSITE/website' >> /etc/gitconfig
cat /etc/gitconfig | tail -6
'''
out, err = exec_cmd(cmd, timeout=30)
print(f"  {out.strip() if out else err}")

# Step 2: Git pull as mycosoft user
print("\n[2/5] Pulling latest code as mycosoft user...")
cmd = '''
cd /home/mycosoft/mycosoft/website
sudo -u mycosoft git fetch origin 2>&1
sudo -u mycosoft git reset --hard origin/main 2>&1 | tail -3
'''
out, err = exec_cmd(cmd, timeout=60)
if out:
    for line in out.strip().split('\n')[-5:]:
        print(f"  {line}")
else:
    print(f"  Error: {err}")

# Step 3: Show recent commits to verify new code
print("\n[3/5] Verifying code is updated...")
cmd = '''
cd /home/mycosoft/mycosoft/website
sudo -u mycosoft git log --oneline -3
'''
out, err = exec_cmd(cmd, timeout=30)
if out:
    for line in out.strip().split('\n'):
        print(f"  {line}")

# Step 4: Rebuild container
print("\n[4/5] Rebuilding container (2-3 min)...")
cmd = '''
cd /home/mycosoft/mycosoft/website
docker compose -f docker-compose.always-on.yml build mycosoft-website --no-cache 2>&1 | grep -E "(Step|Successfully|DONE)" | tail -10
'''
out, err = exec_cmd(cmd, timeout=300)
if out:
    for line in out.strip().split('\n')[-5:]:
        print(f"  {line}")
else:
    print(f"  Build in progress or timeout: {err}")

# Step 5: Restart container  
print("\n[5/5] Restarting container...")
cmd = '''
cd /home/mycosoft/mycosoft/website
docker compose -f docker-compose.always-on.yml up -d mycosoft-website 2>&1
'''
out, err = exec_cmd(cmd, timeout=60)
if out:
    print(f"  {out.strip()}")
else:
    print(f"  Error: {err}")

# Verify
print("\n[*] Verification...")
time.sleep(8)
out, err = exec_cmd("docker ps --format '{{.Names}}: {{.Status}}' | grep website", timeout=30)
if out:
    print(f"  Container: {out.strip()}")

print("\n" + "=" * 60)
print("  DONE")
print("=" * 60)
print("\nTest URLs:")
print("  - https://sandbox.mycosoft.com/security")
print("  - https://sandbox.mycosoft.com/security/compliance")
