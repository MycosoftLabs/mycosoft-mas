#!/usr/bin/env python3
"""Stop n8n on Sandbox VM via Proxmox"""
import requests
import urllib3
import time
import base64

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PROXMOX_HOST = "https://192.168.0.202:8006"
PROXMOX_TOKEN = "root@pam!cursor_agent=bc1c9dc7-6fca-4e89-8a1d-557a9d117a3e"
VM_ID = 103
NODE = "pve"
headers = {"Authorization": f"PVEAPIToken={PROXMOX_TOKEN}"}

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
        
        status_url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/exec-status"
        start = time.time()
        
        while time.time() - start < timeout:
            time.sleep(2)
            s = requests.get(status_url, headers=headers, params={"pid": pid}, verify=False, timeout=5)
            if s.ok:
                data = s.json().get("data", {})
                if data.get("exited"):
                    out_b64 = data.get("out-data", "")
                    try:
                        out = base64.b64decode(out_b64).decode() if out_b64 else ""
                    except:
                        out = out_b64
                    return data.get("exitcode", 0) == 0, out
        return None, "Timeout"
    except Exception as e:
        return None, str(e)

print("Stopping n8n on Sandbox VM...")
# Try multiple methods to stop n8n
cmds = [
    "docker stop mas-n8n-1 2>&1 || true",
    "docker stop n8n 2>&1 || true", 
    "cd /home/mycosoft/mycosoft/mas && docker compose stop n8n 2>&1 || true",
    "docker ps --filter 'name=n8n' --format '{{.Names}} {{.Status}}'",
]

for cmd in cmds:
    print(f"Running: {cmd[:50]}...")
    success, output = exec_cmd(cmd)
    if output:
        print(f"  Result: {output[:100]}")
