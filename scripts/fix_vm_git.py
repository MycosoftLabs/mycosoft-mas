#!/usr/bin/env python3
"""Fix git ownership and verify deployment"""
import requests
import urllib3
import time
urllib3.disable_warnings()

PROXMOX_HOST = "https://192.168.0.202:8006"
headers = {"Authorization": "PVEAPIToken=myca@pve!mas=ca23b6c8-5746-46c4-8e36-fc6caad5a9e5"}
VM_ID = 103
NODE = "pve"

def exec_cmd(cmd, timeout=60):
    url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/exec"
    try:
        data = {"command": "/bin/bash", "input-data": cmd}
        r = requests.post(url, headers=headers, data=data, verify=False, timeout=10)
        if not r.ok:
            return None, f"Failed: {r.status_code}"
        pid = r.json().get("data", {}).get("pid")
        if not pid:
            return None, "No PID"
        
        status_url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/exec-status"
        start = time.time()
        while time.time() - start < timeout:
            time.sleep(2)
            s = requests.get(status_url, headers=headers, params={"pid": pid}, verify=False, timeout=5)
            if s.ok:
                data = s.json().get("data", {})
                if data.get("exited"):
                    return data.get("exitcode", 0), data.get("out-data", "")
        return None, "Timeout"
    except Exception as e:
        return None, str(e)

print("=== Fixing Git Ownership ===")
code, out = exec_cmd("git config --global --add safe.directory /home/mycosoft/mycosoft/website")
print(f"Git safe.directory: {code}")

code, out = exec_cmd("git config --global --add safe.directory /home/mycosoft/mycosoft/mas")
print(f"Git safe.directory mas: {code}")

print("\n=== Pulling Latest Code ===")
code, out = exec_cmd("cd /home/mycosoft/mycosoft/website && git fetch origin && git reset --hard origin/main")
print(f"Git pull: {code}")
if out:
    print(out[:200])

print("\n=== Container Status ===")
code, out = exec_cmd("docker ps --format 'table {{.Names}}\t{{.Status}}'")
print(out if out else "Error")

print("\n=== Quick Health Check ===")
code, out = exec_cmd("curl -s http://localhost:3000 | head -c 200")
print(f"Localhost response: {out[:100] if out else 'No response'}")
