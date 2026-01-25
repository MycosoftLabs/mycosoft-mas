#!/usr/bin/env python3
"""Debug why website container isn't starting."""
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
            print("No PID")
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
        print("Timeout!")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

print("="*60)
print("DEBUG: Why isn't website starting?")
print("="*60)

# Check compose file
print("\n[1] Checking docker-compose.always-on.yml location...")
exec_cmd("ls -la /home/mycosoft/mycosoft/mas/docker-compose.always-on.yml")

print("\n[2] Checking website service in compose...")
exec_cmd("cd /home/mycosoft/mycosoft/mas && grep -A 20 'mycosoft-website:' docker-compose.always-on.yml | head -25")

print("\n[3] Checking build context path...")
exec_cmd("ls -la /home/mycosoft/WEBSITE/website 2>&1 || echo 'PATH NOT FOUND'")
exec_cmd("ls -la /home/mycosoft/mycosoft/website 2>&1 | head -5")

print("\n[4] Checking Docker images available...")
exec_cmd("docker images | grep -i mycosoft")

print("\n[5] Trying to start website with verbose output...")
exec_cmd("""
cd /home/mycosoft/mycosoft/mas &&
docker compose -f docker-compose.always-on.yml up -d mycosoft-website 2>&1
""", timeout=120)

print("\n[6] Checking if container was created...")
exec_cmd("docker ps -a | grep -i website || echo 'NO WEBSITE CONTAINER'")

print("\n[7] If exists, checking logs...")
exec_cmd("docker ps -a --filter name=website -q | head -1 | xargs -r docker logs --tail 30 2>&1 || echo 'No container to log'")
