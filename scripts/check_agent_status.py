#!/usr/bin/env python3
"""Check agent deployment status"""
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
            time.sleep(3)
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

print("=" * 60)
print("AGENT DEPLOYMENT STATUS CHECK")
print("=" * 60)

print("\n1. Docker images (agent-related):")
result = exec_cmd("docker images | grep -E '(agent|orchestrator|mas-)' | head -15")
print(result)

print("\n2. Running containers (all):")
result = exec_cmd("docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | head -20")
print(result)

print("\n3. Docker compose status for agents:")
result = exec_cmd("cd /home/mycosoft/mycosoft/mas/docker && docker compose -f docker-compose.agents.yml ps 2>&1")
print(result)

print("\n4. Recent container events:")
result = exec_cmd("docker events --since 60s --until 0s --format '{{.Action}} {{.Actor.Attributes.name}}' 2>&1 | head -10 || echo 'No recent events'")
print(result)
