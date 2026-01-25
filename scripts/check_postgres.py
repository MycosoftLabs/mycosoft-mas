#!/usr/bin/env python3
"""Check PostgreSQL configuration"""
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
            return f"Exec failed: {r.status_code}"
        
        pid = r.json().get("data", {}).get("pid")
        if not pid:
            return "No PID"
        
        status_url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/exec-status"
        start = time.time()
        
        while time.time() - start < timeout:
            time.sleep(2)
            s = requests.get(status_url, headers=headers, params={"pid": pid}, verify=False, timeout=5)
            if s.ok:
                data = s.json().get("data", {})
                if data.get("exited"):
                    out_b64 = data.get("out-data", "")
                    err_b64 = data.get("err-data", "")
                    try:
                        out = base64.b64decode(out_b64).decode() if out_b64 else ""
                    except:
                        out = out_b64
                    try:
                        err = base64.b64decode(err_b64).decode() if err_b64 else ""
                    except:
                        err = err_b64
                    return out or err or "Command completed"
        return "Timeout"
    except Exception as e:
        return str(e)

print("Checking PostgreSQL configuration on VM...")
print("-" * 60)

print("\n1. Check docker-compose environment for postgres...")
result = exec_cmd("grep -A 10 'mycosoft-postgres' /home/mycosoft/mycosoft/mas/docker-compose.always-on.yml 2>&1 | head -20")
print(result)

print("\n2. Check POSTGRES_USER in .env...")
result = exec_cmd("grep -i postgres /home/mycosoft/mycosoft/mas/.env 2>&1")
print(result)

print("\n3. List databases using postgres user...")
result = exec_cmd("docker exec mycosoft-postgres psql -U postgres -c '\\l' 2>&1")
print(result)

print("\n4. List roles...")
result = exec_cmd("docker exec mycosoft-postgres psql -U postgres -c '\\du' 2>&1")
print(result)
