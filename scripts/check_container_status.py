#!/usr/bin/env python3
"""Check container status and logs on VM 103"""
import requests
import urllib3
import time
import base64
import sys

# Fix Windows encoding
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
urllib3.disable_warnings()

PROXMOX_HOST = "https://192.168.0.202:8006"
PROXMOX_TOKEN_ID = os.environ.get("PROXMOX_TOKEN_ID", "myca@pve!mas")
PROXMOX_TOKEN_SECRET = os.environ.get("PROXMOX_TOKEN_SECRET", "")
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
                    except Exception:
                        out = out_b64
                    try:
                        err = base64.b64decode(err_b64).decode() if err_b64 else ""
                    except Exception:
                        err = err_b64
                    return result.get("exitcode", 0), out + err
        return None, "Timeout"
    except Exception as e:
        return None, str(e)

print("=== CHECKING CONTAINER STATUS ===")
code, out = exec_cmd("docker ps -a --format 'table {{.Names}}\t{{.Status}}' | grep -E 'website|NAMES'")
print(out if out else "No output")

print("\n=== CHECKING SYMLINK ===")
code, out = exec_cmd("ls -la /home/mycosoft/WEBSITE/")
print(out if out else "No output")

print("\n=== CHECKING WEBSITE PATH ===")  
code, out = exec_cmd("ls -la /home/mycosoft/mycosoft/website/ | head -10")
print(out if out else "No output")

print("\n=== LAST BUILD ERROR (if any) ===")
code, out = exec_cmd("docker logs mycosoft-always-on-mycosoft-website-1 --tail 20 2>&1")
print(out if out else "No container logs")

print("\n=== TRYING DIRECT BUILD TO SEE ERROR ===")
code, out = exec_cmd("cd /home/mycosoft/mycosoft/mas && docker compose -f docker-compose.always-on.yml build mycosoft-website 2>&1 | tail -50", timeout=180)
print(out if out else "No build output")
