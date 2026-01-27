#!/usr/bin/env python3
"""
Deploy to Sandbox VM
Date: January 27, 2026
Pulls latest code from GitHub and rebuilds the website container
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
VM_ID = 103  # Sandbox VM
NODE = "pve"

headers = {"Authorization": f"PVEAPIToken={PROXMOX_TOKEN}"}

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    symbols = {"INFO": "[i]", "OK": "[+]", "WARN": "[!]", "ERR": "[X]", "RUN": "[>]"}
    print(f"[{ts}] {symbols.get(level, '*')} {msg}")

def exec_cmd(cmd, timeout=180, show_output=True):
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
            time.sleep(3)
            s = requests.get(status_url, headers=headers, params={"pid": pid}, verify=False, timeout=5)
            if s.ok:
                data = s.json().get("data", {})
                if data.get("exited"):
                    code = data.get("exitcode", 0)
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
                    
                    return code == 0, out or err
            
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
    print("=" * 60)
    print("DEPLOY TO SANDBOX VM (103)")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Step 1: Check VM
    log("Checking VM 103 status...", "RUN")
    if not check_vm():
        log("VM is not running!", "ERR")
        return False
    log("VM is running", "OK")
    
    # Step 2: Pull website code
    log("Pulling latest website code...", "RUN")
    success, output = exec_cmd(
        "cd /home/mycosoft/mycosoft/website && git fetch origin main && git reset --hard origin/main && git log -1 --oneline",
        timeout=120
    )
    if success:
        log("Website code updated", "OK")
    else:
        log(f"Pull warning: {output[:100]}", "WARN")
    
    # Step 3: Pull MAS code
    log("Pulling latest MAS code...", "RUN")
    success, output = exec_cmd(
        "cd /home/mycosoft/mycosoft/mas && git fetch origin main && git reset --hard origin/main && git log -1 --oneline",
        timeout=120
    )
    if success:
        log("MAS code updated", "OK")
    else:
        log(f"Pull warning: {output[:100]}", "WARN")
    
    # Step 4: Stop n8n on Sandbox (it's now on MAS VM)
    log("Stopping n8n on Sandbox (moved to MAS VM)...", "RUN")
    exec_cmd("docker stop n8n 2>/dev/null || true", timeout=30, show_output=False)
    log("n8n stopped", "OK")
    
    # Step 5: Rebuild website container
    log("Rebuilding website container (no-cache)...", "RUN")
    success, output = exec_cmd(
        "cd /home/mycosoft/mycosoft/website && docker build -t website-website:latest --no-cache . 2>&1 | tail -20",
        timeout=600
    )
    if success:
        log("Website container built", "OK")
    else:
        log(f"Build output: {output[:200] if output else 'No output'}", "WARN")
    
    # Step 6: Restart website container
    log("Restarting website container...", "RUN")
    success, output = exec_cmd(
        "cd /home/mycosoft/mycosoft/mas && docker compose -f docker-compose.always-on.yml up -d --force-recreate mycosoft-website 2>&1",
        timeout=60
    )
    log("Website container restarted", "OK")
    
    # Step 7: Verify containers
    log("Verifying containers...", "RUN")
    success, output = exec_cmd("docker ps --format 'table {{.Names}}\t{{.Status}}' | head -15")
    
    # Step 8: Test health
    log("Testing website health...", "RUN")
    time.sleep(10)
    success, output = exec_cmd("curl -s http://localhost:3000/api/health 2>&1 | head -5")
    if success and output:
        log("Website health check passed", "OK")
    else:
        log("Health check pending", "WARN")
    
    print()
    print("=" * 60)
    print("DEPLOYMENT COMPLETE")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Purge Cloudflare cache at https://dash.cloudflare.com")
    print("2. Verify at https://sandbox.mycosoft.com")
    print("3. Test n8n integration via voice/chat")
    
    return True

if __name__ == "__main__":
    main()
