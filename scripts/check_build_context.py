#!/usr/bin/env python3
"""Check build context and Dockerfile paths"""
import requests
import urllib3
import time
urllib3.disable_warnings()

PROXMOX_HOST = "https://192.168.0.202:8006"
headers = {"Authorization": "PVEAPIToken=myca@pve!mas=ca23b6c8-5746-46c4-8e36-fc6caad5a9e5"}

def exec_cmd(cmd, timeout=30):
    url = f"{PROXMOX_HOST}/api2/json/nodes/pve/qemu/103/agent/exec"
    data = {"command": "/bin/bash", "input-data": cmd}
    r = requests.post(url, headers=headers, data=data, verify=False, timeout=10)
    if not r.ok:
        return f"FAILED: {r.status_code}"
    pid = r.json().get("data", {}).get("pid")
    
    status_url = f"{PROXMOX_HOST}/api2/json/nodes/pve/qemu/103/agent/exec-status?pid={pid}"
    start = time.time()
    while time.time() - start < timeout:
        time.sleep(1)
        r2 = requests.get(status_url, headers=headers, verify=False, timeout=10)
        if r2.ok:
            result = r2.json().get("data", {})
            if result.get("exited"):
                return result.get("out-data", "") + result.get("err-data", "")
    return "TIMEOUT"

print("="*60)
print("  CHECKING BUILD CONTEXT")
print("="*60)

print("\n[1] Compose file contents (mycosoft-website section):")
print(exec_cmd("""
cd /home/mycosoft/mycosoft/mas
grep -A 20 'mycosoft-website:' docker-compose.always-on.yml | head -25
"""))

print("\n[2] Does the build context path exist?")
print(exec_cmd("""
cd /home/mycosoft/mycosoft/mas
# Extract build context from compose file
CONTEXT=$(grep -A 5 'mycosoft-website:' docker-compose.always-on.yml | grep 'context:' | awk '{print $2}')
echo "Build context in compose: $CONTEXT"

# Resolve the actual path
FULL_PATH=$(cd /home/mycosoft/mycosoft/mas && realpath "$CONTEXT" 2>/dev/null || echo "NOT FOUND")
echo "Resolved path: $FULL_PATH"

if [ -d "$FULL_PATH" ]; then
    echo "Directory EXISTS"
    ls -la "$FULL_PATH" | head -5
else
    echo "Directory DOES NOT EXIST"
fi
"""))

print("\n[3] Does the website repo have tour components?")
print(exec_cmd("""
cd /home/mycosoft/mycosoft/website
find components -name '*tour*' -type f 2>/dev/null | head -5
ls -la components/security/tour/ 2>/dev/null | head -5
"""))

print("\n[4] What Dockerfile is being used?")
print(exec_cmd("""
cd /home/mycosoft/mycosoft/mas
grep -A 5 'mycosoft-website:' docker-compose.always-on.yml | grep dockerfile
ls -la /home/mycosoft/mycosoft/website/Dockerfile.container 2>/dev/null
"""))

print("\n[5] Check image history:")
print(exec_cmd("docker history mycosoft-always-on-mycosoft-website --no-trunc 2>/dev/null | head -10"))
