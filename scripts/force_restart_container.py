#!/usr/bin/env python3
"""Force restart the container with the new image."""
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
VM_MEDIA_PATH = "/opt/mycosoft/media/website/assets"

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
                    try:
                        if out:
                            out = base64.b64decode(out).decode('utf-8', errors='replace')
                    except:
                        pass
                    if out:
                        print(out)
                    return out
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

print("="*60)
print("FORCE RESTARTING CONTAINER WITH NEW IMAGE")
print("="*60)

# Step 1: Stop and remove existing container
print("\n[1] Stopping and removing existing container...")
exec_cmd("docker stop mycosoft-website 2>/dev/null || true")
exec_cmd("docker rm mycosoft-website 2>/dev/null || true")

# Step 2: Start with new image and NAS mount
print("\n[2] Starting container with new image and NAS mount...")
exec_cmd(f"""
docker run -d --name mycosoft-website \
  -p 3000:3000 \
  --restart unless-stopped \
  -v {VM_MEDIA_PATH}:/app/public/assets:ro \
  mycosoft-always-on-mycosoft-website:latest 2>&1
""")

# Wait for startup
print("\n[3] Waiting for container to start (20s)...")
time.sleep(20)

# Step 4: Verify container
print("\n[4] Checking container status...")
exec_cmd("docker ps | grep website")

# Step 5: Test endpoints
print("\n[5] Testing endpoints...")
exec_cmd("curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/ 2>/dev/null || echo 'FAIL'")
exec_cmd("curl -s -o /dev/null -w '%{http_code}' 'http://localhost:3000/assets/mushroom1/close%201.mp4' 2>/dev/null || echo 'FAIL'")

# Step 6: Verify Quadruped text
print("\n[6] Checking for 'Quadruped' in page...")
exec_cmd("curl -s http://localhost:3000/devices/mushroom-1 2>/dev/null | grep -o 'Quadruped' | head -1 || echo 'NOT FOUND - CHECK CACHE'")

print("\n" + "="*60)
print("DONE")
print("="*60)
