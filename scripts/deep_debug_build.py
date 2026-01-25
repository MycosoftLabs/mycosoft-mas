#!/usr/bin/env python3
"""
Deep debug the build issue - find what's referencing /app/website
"""
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

def exec_cmd(cmd, timeout=60):
    url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/exec"
    try:
        data = {"command": "/bin/bash", "input-data": cmd}
        r = requests.post(url, headers=headers, data=data, verify=False, timeout=10)
        if not r.ok:
            return None, f"Exec failed: {r.status_code}"
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
                    out_b64 = result.get("out-data", "")
                    err_b64 = result.get("err-data", "")
                    try:
                        out = base64.b64decode(out_b64).decode() if out_b64 else ""
                    except:
                        out = out_b64
                    try:
                        err = base64.b64decode(err_b64).decode() if err_b64 else ""
                    except:
                        err = err_b64
                    return result.get("exitcode", 0), out + err
        return None, "Timeout"
    except Exception as e:
        return None, str(e)

print("=== CHECKING FOR SYMLINKS IN WEBSITE DIR ===")
code, out = exec_cmd("find /home/mycosoft/mycosoft/website -type l 2>/dev/null | head -20")
print(out if out else "No symlinks found")

print("\n=== CHECKING FOR .next DIRECTORY ===")
code, out = exec_cmd("ls -la /home/mycosoft/mycosoft/website/.next 2>&1 | head -10")
print(out if out else "No .next")

print("\n=== CHECKING next.config.js ===")
code, out = exec_cmd("cat /home/mycosoft/mycosoft/website/next.config.js")
print(out if out else "Not found")

print("\n=== CHECKING Dockerfile.container ===")
code, out = exec_cmd("cat /home/mycosoft/mycosoft/website/Dockerfile.container")
print(out if out else "Not found")

print("\n=== SEARCH FOR 'website' STRING IN CODE FILES ===")
code, out = exec_cmd("grep -r 'website' /home/mycosoft/mycosoft/website/*.js /home/mycosoft/mycosoft/website/*.mjs 2>/dev/null | head -20")
print(out if out else "No matches")

print("\n=== CHECKING DOCKER COMPOSE BUILD CONTEXT ===")
code, out = exec_cmd("grep -A5 'mycosoft-website' /home/mycosoft/mycosoft/mas/docker-compose.always-on.yml | head -20")
print(out if out else "Not found")
