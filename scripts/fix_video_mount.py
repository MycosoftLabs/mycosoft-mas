#!/usr/bin/env python3
"""Fix video mount - restart container with proper volume mounts."""
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

def exec_cmd(cmd, timeout=180):
    url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/exec"
    try:
        data = {"command": "/bin/bash", "input-data": cmd}
        r = requests.post(url, headers=headers, data=data, verify=False, timeout=15)
        if not r.ok:
            print(f"Request failed: {r.status_code}")
            return None
        pid = r.json().get("data", {}).get("pid")
        if not pid:
            return None
        
        status_url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/exec-status?pid={pid}"
        start = time.time()
        while time.time() - start < timeout:
            time.sleep(3)
            sr = requests.get(status_url, headers=headers, verify=False, timeout=10)
            if sr.ok:
                sd = sr.json().get("data", {})
                if sd.get("exited"):
                    out = sd.get("out-data", "")
                    err = sd.get("err-data", "")
                    try:
                        if out:
                            out = base64.b64decode(out).decode('utf-8', errors='replace')
                        if err:
                            err = base64.b64decode(err).decode('utf-8', errors='replace')
                    except:
                        pass
                    if out:
                        print(out)
                    if err:
                        print(f"STDERR: {err}")
                    return out
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

print("="*60)
print("FIXING VIDEO MOUNT")
print("="*60)

# Step 1: Stop and remove the test container
print("\n[1] Stopping website-test container...")
exec_cmd("docker stop website-test 2>/dev/null && docker rm website-test 2>/dev/null || echo 'No test container'")

# Step 2: Check if NAS is mounted
print("\n[2] Checking NAS mount...")
exec_cmd("ls -la /opt/mycosoft/media/website/assets/ | head -10 || echo 'NAS NOT MOUNTED'")

# Step 3: Check for mushroom1 videos
print("\n[3] Checking for mushroom1 videos...")
exec_cmd("ls -la /opt/mycosoft/media/website/assets/mushroom1/ 2>/dev/null | head -15 || echo 'NO MUSHROOM1 FOLDER'")

# Step 4: Start container with proper volume mount
print("\n[4] Starting container with NAS volume mount...")
exec_cmd("""
docker run -d --name mycosoft-website \
  -p 3000:3000 \
  --restart unless-stopped \
  -v /opt/mycosoft/media/website/assets:/app/public/assets:ro \
  mycosoft-always-on-mycosoft-website:latest 2>&1
""")

# Wait for startup
print("\n[5] Waiting for container to start (15s)...")
time.sleep(15)

# Step 6: Verify container is running
print("\n[6] Checking container status...")
exec_cmd("docker ps | grep website")

# Step 7: Test video endpoint
print("\n[7] Testing video endpoint...")
exec_cmd("curl -s -o /dev/null -w '%{http_code}' 'http://localhost:3000/assets/mushroom1/close%201.mp4' 2>/dev/null || echo 'FAIL'")

# Step 8: List what's in the container's assets folder
print("\n[8] Checking assets inside container...")
exec_cmd("docker exec mycosoft-website ls -la /app/public/assets/mushroom1/ 2>/dev/null | head -10 || echo 'Cannot list'")

print("\n" + "="*60)
print("DONE - Check sandbox.mycosoft.com")
print("="*60)
