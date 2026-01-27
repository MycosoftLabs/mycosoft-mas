#!/usr/bin/env python3
"""
Start MAS Backend Services - January 27, 2026
Starts orchestrator, voice services, and verifies health on MAS VM
"""
import requests
import urllib3
import time
import base64
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Proxmox Configuration
PROXMOX_HOST = "https://192.168.0.202:8006"
PROXMOX_TOKEN = "root@pam!cursor_agent=bc1c9dc7-6fca-4e89-8a1d-557a9d117a3e"
VM_ID = 188  # MAS VM (mycosoft-mas)
NODE = "pve"

headers = {"Authorization": f"PVEAPIToken={PROXMOX_TOKEN}"}

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    symbols = {"INFO": "[i]", "OK": "[+]", "WARN": "[!]", "ERR": "[X]", "RUN": "[>]"}
    print(f"[{ts}] {symbols.get(level, '*')} {msg}")

def exec_cmd(cmd, timeout=120, show_output=True):
    """Execute command via QEMU Guest Agent"""
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
                    err_b64 = data.get("err-data", "")
                    try:
                        out = base64.b64decode(out_b64).decode() if out_b64 else ""
                    except:
                        out = out_b64
                    try:
                        err = base64.b64decode(err_b64).decode() if err_b64 else ""
                    except:
                        err = err_b64
                    
                    if show_output and (out or err):
                        output = (out or err)[:500]
                        for line in output.split('\n')[:10]:
                            if line.strip():
                                print(f"    {line}")
                    
                    return data.get("exitcode", 0) == 0, out or err
        return None, "Timeout"
    except Exception as e:
        return None, str(e)

def check_vm():
    url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/status/current"
    try:
        r = requests.get(url, headers=headers, verify=False, timeout=5)
        if r.ok:
            data = r.json().get("data", {})
            return data.get("status") == "running"
    except:
        pass
    return False

def main():
    print("=" * 70)
    print("START MAS BACKEND SERVICES")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("VM: 101 (MAS VM - 192.168.0.188)")
    print("=" * 70)
    
    # Check VM status
    log("Checking VM 101 status...", "RUN")
    if not check_vm():
        log("VM 101 is not running!", "ERR")
        return False
    log("VM is running", "OK")
    
    # Check current containers
    log("Checking running containers...", "RUN")
    success, output = exec_cmd("docker ps --format '{{.Names}} {{.Status}}' | head -20")
    
    # Services to ensure are running
    services = [
        ("mas-orchestrator", "MAS Orchestrator API"),
        ("n8n", "n8n Workflow Engine"),
        ("redis", "Redis Cache"),
        ("mas-postgres", "PostgreSQL Database"),
    ]
    
    # Check which services are running
    log("Checking required services...", "RUN")
    success, containers = exec_cmd("docker ps --format '{{.Names}}'", show_output=False)
    running = containers.split('\n') if containers else []
    
    for service_name, description in services:
        is_running = any(service_name in c for c in running)
        if is_running:
            log(f"{description}: Running", "OK")
        else:
            log(f"{description}: NOT RUNNING - Starting...", "WARN")
            # Try to start the container
            exec_cmd(f"docker start {service_name} 2>/dev/null || true", show_output=False)
    
    # Start services using docker-compose
    log("Starting services with docker-compose...", "RUN")
    success, output = exec_cmd(
        "cd /home/mycosoft/mycosoft/mas && docker compose up -d mas-orchestrator redis mas-postgres 2>&1 | tail -10",
        timeout=180
    )
    
    # Wait for services to be ready
    log("Waiting for services to be ready...", "RUN")
    time.sleep(10)
    
    # Verify orchestrator health
    log("Checking orchestrator health...", "RUN")
    success, output = exec_cmd("curl -s http://localhost:8001/health 2>&1")
    if success and output and "ok" in output.lower():
        log("Orchestrator is healthy", "OK")
    else:
        log(f"Orchestrator health check: {output[:100] if output else 'No response'}", "WARN")
    
    # Check n8n health
    log("Checking n8n health...", "RUN")
    success, output = exec_cmd("curl -s http://localhost:5678/healthz 2>&1")
    if success and output:
        log("n8n is healthy", "OK")
    else:
        log("n8n health check failed", "WARN")
    
    # Final container status
    log("Final container status...", "RUN")
    success, output = exec_cmd("docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -E 'orchestrator|n8n|redis|postgres' | head -10")
    
    print()
    print("=" * 70)
    print("MAS BACKEND SERVICES CHECK COMPLETE")
    print("=" * 70)
    
    return True

if __name__ == "__main__":
    main()
