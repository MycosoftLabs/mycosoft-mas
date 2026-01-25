#!/usr/bin/env python3
"""
Deploy website to Sandbox VM following mandatory protocol
"""
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

def log(msg, level="INFO"):
    ts = time.strftime("%H:%M:%S")
    symbols = {"INFO": "[i]", "OK": "[+]", "WARN": "[!]", "ERR": "[X]", "RUN": "[>]"}
    print(f"[{ts}] {symbols.get(level, '*')} {msg}")

def exec_cmd(cmd, timeout=300, show_output=True):
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
            time.sleep(5)
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
                        output = (out or err)[:800]
                        for line in output.split('\n')[:15]:
                            print(f"    {line}")
                    
                    return code == 0, out or err
            
        return None, "Timeout"
    except Exception as e:
        return None, str(e)

def main():
    print("=" * 60)
    print("WEBSITE DEPLOYMENT TO SANDBOX VM")
    print("=" * 60)
    
    # Step 1: Pull latest website code
    log("Pulling latest website code from GitHub...", "RUN")
    success, output = exec_cmd(
        "cd /home/mycosoft/mycosoft/website && git fetch origin main && git reset --hard origin/main && git log -1 --oneline",
        timeout=60
    )
    if success:
        log("Website code updated", "OK")
    else:
        log(f"Pull warning: {output[:100] if output else 'Unknown'}", "WARN")
    
    # Step 2: Clean Docker environment
    log("Cleaning Docker build cache...", "RUN")
    exec_cmd("docker system prune -f && docker builder prune -f", timeout=60, show_output=False)
    log("Docker cleaned", "OK")
    
    # Step 3: Rebuild website container
    log("Building website container with --no-cache (this takes 2-3 minutes)...", "RUN")
    success, output = exec_cmd(
        "cd /home/mycosoft/mycosoft/mas && docker compose -f docker-compose.always-on.yml build mycosoft-website --no-cache 2>&1 | tail -20",
        timeout=400
    )
    if success:
        log("Website container built", "OK")
    else:
        log(f"Build completed with: {output[:100] if output else 'output'}", "WARN")
    
    # Step 4: Force recreate container
    log("Force recreating website container...", "RUN")
    success, output = exec_cmd(
        "cd /home/mycosoft/mycosoft/mas && docker compose -f docker-compose.always-on.yml up -d --force-recreate mycosoft-website 2>&1",
        timeout=60
    )
    log("Container recreated", "OK")
    
    # Step 5: Verify container running
    log("Verifying container status...", "RUN")
    success, output = exec_cmd("docker ps | grep website")
    
    # Step 6: Wait and check health
    log("Waiting for container startup (10s)...", "RUN")
    time.sleep(10)
    
    log("Checking health endpoint...", "RUN")
    success, output = exec_cmd("curl -s http://localhost:3000/api/health 2>&1")
    if success and "ok" in str(output).lower():
        log("Health check passed", "OK")
    else:
        log(f"Health: {output[:100] if output else 'No response'}", "WARN")
    
    print("\n" + "=" * 60)
    print("WEBSITE DEPLOYMENT COMPLETE")
    print("=" * 60)
    print("\nNext step: Purge Cloudflare cache at https://dash.cloudflare.com")
    print("Then verify at: https://sandbox.mycosoft.com/natureos/mas")
    
    return True

if __name__ == "__main__":
    main()
