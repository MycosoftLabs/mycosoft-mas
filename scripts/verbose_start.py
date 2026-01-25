#!/usr/bin/env python3
"""Get verbose error from docker compose."""
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
                    exitcode = sd.get("exitcode", -1)
                    try:
                        if out:
                            out = base64.b64decode(out).decode('utf-8', errors='replace')
                        if err:
                            err = base64.b64decode(err).decode('utf-8', errors='replace')
                    except:
                        pass
                    print(f"Exit code: {exitcode}")
                    if out:
                        print(f"STDOUT:\n{out}")
                    if err:
                        print(f"STDERR:\n{err}")
                    return out, err, exitcode
        print("Timeout!")
        return None, None, -1
    except Exception as e:
        print(f"Error: {e}")
        return None, None, -1

print("="*60)
print("VERBOSE: Starting website container")
print("="*60)

# Try running docker run directly with the image
print("\n[1] Try docker run directly with the built image...")
exec_cmd("""
docker run -d --name website-test \
  -p 3000:3000 \
  --restart unless-stopped \
  mycosoft-always-on-mycosoft-website:latest 2>&1
""")

print("\n[2] Check if it started...")
exec_cmd("docker ps | grep website")

print("\n[3] If running, check logs...")
exec_cmd("docker logs website-test --tail 20 2>&1 || echo 'Container not running'")

print("\n[4] Check localhost:3000...")
time.sleep(10)
exec_cmd("curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/ 2>/dev/null || echo 'CURL_FAIL'")
