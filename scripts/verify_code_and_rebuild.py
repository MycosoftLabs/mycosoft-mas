#!/usr/bin/env python3
"""Verify the code has Quadruped and rebuild the image."""
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
VM_WEBSITE_PATH = "/home/mycosoft/mycosoft/website"
VM_MAS_PATH = "/home/mycosoft/mycosoft/mas"
VM_MEDIA_PATH = "/opt/mycosoft/media/website/assets"

headers = {"Authorization": f"PVEAPIToken={PROXMOX_TOKEN_ID}={PROXMOX_TOKEN_SECRET}"}

def log(msg):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

def exec_cmd(cmd, timeout=300):
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
                    if err and "error" in err.lower():
                        print(f"STDERR: {err}")
                    return out
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

print("="*60)
print("VERIFY CODE AND REBUILD")
print("="*60)

# Step 1: Check current git status
log("Checking git status on VM...")
exec_cmd(f"cd {VM_WEBSITE_PATH} && git log -1 --oneline")

# Step 2: Check if Quadruped is in the code
log("Checking for 'Quadruped' in source code...")
exec_cmd(f"grep -r 'Quadruped' {VM_WEBSITE_PATH}/components/devices/*.tsx | head -3")

# Step 3: If not found, pull latest code
log("Pulling latest code...")
exec_cmd(f"cd {VM_WEBSITE_PATH} && git fetch origin main && git reset --hard origin/main && git log -1 --oneline")

# Step 4: Verify again
log("Verifying 'Quadruped' in source after pull...")
exec_cmd(f"grep 'Quadruped' {VM_WEBSITE_PATH}/components/devices/mushroom1-details.tsx | head -2")

# Step 5: Stop container
log("Stopping container...")
exec_cmd("docker stop mycosoft-website 2>/dev/null || true")
exec_cmd("docker rm mycosoft-website 2>/dev/null || true")

# Step 6: Clean docker
log("Cleaning Docker cache...")
exec_cmd("docker builder prune -af 2>/dev/null || true", timeout=120)
exec_cmd("docker system prune -af 2>/dev/null || true", timeout=120)

# Step 7: Remove old images
log("Removing old website images...")
exec_cmd("docker rmi mycosoft-always-on-mycosoft-website:latest 2>/dev/null || true")

# Step 8: Rebuild
log("Building new image (this will take 3-5 minutes)...")
exec_cmd(f"cd {VM_MAS_PATH} && docker compose -f docker-compose.always-on.yml build mycosoft-website --no-cache 2>&1 | tail -20", timeout=600)

# Step 9: Start container
log("Starting container with NAS mount...")
exec_cmd(f"""
docker run -d --name mycosoft-website \
  -p 3000:3000 \
  --restart unless-stopped \
  -v {VM_MEDIA_PATH}:/app/public/assets:ro \
  mycosoft-always-on-mycosoft-website:latest 2>&1
""")

# Wait for startup
log("Waiting for container to start (30s)...")
time.sleep(30)

# Step 10: Verify
log("Checking container status...")
exec_cmd("docker ps | grep website")

log("Testing page endpoint...")
exec_cmd("curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/devices/mushroom-1 2>/dev/null")

log("Checking for 'Quadruped' in served page...")
exec_cmd("curl -s http://localhost:3000/devices/mushroom-1 2>/dev/null | grep -o 'Quadruped' | head -1 || echo 'NOT FOUND'")

print("\n" + "="*60)
print("DONE - Please purge Cloudflare and hard refresh browser")
print("="*60)
