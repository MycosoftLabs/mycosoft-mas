#!/usr/bin/env python3
"""
INSTANT DEPLOY - Fast sandbox deployment via Proxmox API
No SSH, no hangs - uses QEMU Guest Agent for reliable execution

Usage: python scripts/instant_deploy.py
"""
import requests
import urllib3
import time
import sys
import os

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration - Proxmox API
PROXMOX_HOST = "https://192.168.0.202:8006"
PROXMOX_TOKEN_ID = os.getenv("PROXMOX_TOKEN_ID", "myca@pve!mas")
PROXMOX_TOKEN_SECRET = os.getenv("PROXMOX_TOKEN_SECRET", "ca23b6c8-5746-46c4-8e36-fc6caad5a9e5")
VM_ID = 103
NODE = "pve"

# Cloudflare API for cache purge
CF_ZONE_ID = os.getenv("CF_ZONE_ID", "")
CF_API_TOKEN = os.getenv("CF_API_TOKEN", "")

headers = {
    "Authorization": f"PVEAPIToken={PROXMOX_TOKEN_ID}={PROXMOX_TOKEN_SECRET}"
}

def log(msg, level="INFO"):
    """Print with timestamp"""
    ts = time.strftime("%H:%M:%S")
    symbols = {"INFO": "[i]", "OK": "[+]", "WARN": "[!]", "ERR": "[X]", "RUN": "[>]"}
    print(f"[{ts}] {symbols.get(level, '*')} {msg}")

def check_vm():
    """Check if VM is running"""
    url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/status/current"
    try:
        r = requests.get(url, headers=headers, verify=False, timeout=5)
        if r.ok:
            data = r.json().get("data", {})
            return data.get("status") == "running"
    except:
        pass
    return False

def exec_cmd(cmd, timeout=120):
    """Execute command via QEMU Guest Agent and wait"""
    url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/exec"
    try:
        # Use /bin/bash -c to run complex commands
        data = {
            "command": "/bin/bash",
            "input-data": cmd
        }
        r = requests.post(url, headers=headers, data=data, verify=False, timeout=10)
        if not r.ok:
            return None, f"Exec failed: {r.status_code} - {r.text[:100]}"
        pid = r.json().get("data", {}).get("pid")
        if not pid:
            return None, "No PID returned"
        
        # Poll for completion
        status_url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/exec-status"
        start = time.time()
        while time.time() - start < timeout:
            time.sleep(2)
            s = requests.get(status_url, headers=headers, params={"pid": pid}, verify=False, timeout=5)
            if s.ok:
                data = s.json().get("data", {})
                if data.get("exited"):
                    code = data.get("exitcode", 0)
                    # Decode base64 output if present
                    out = data.get("out-data", "")
                    err = data.get("err-data", "")
                    return code, out if code == 0 else err
        return None, "Timeout"
    except Exception as e:
        return None, str(e)

def purge_cloudflare():
    """Purge Cloudflare cache"""
    if not CF_ZONE_ID or not CF_API_TOKEN:
        log("Cloudflare credentials not set - skipping cache purge", "WARN")
        return False
    
    url = f"https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/purge_cache"
    headers = {
        "Authorization": f"Bearer {CF_API_TOKEN}",
        "Content-Type": "application/json"
    }
    try:
        r = requests.post(url, headers=headers, json={"purge_everything": True}, timeout=10)
        return r.ok
    except:
        return False

def main():
    start = time.time()
    
    print("\n" + "="*60)
    print("  MYCOSOFT INSTANT DEPLOY")
    print("="*60 + "\n")
    
    # Step 1: Check VM
    log("Checking VM 103 via Proxmox API...", "RUN")
    if not check_vm():
        log("VM 103 not running or unreachable!", "ERR")
        sys.exit(1)
    log("VM 103 is running", "OK")
    
    # Step 2: Fix git ownership and pull latest code
    log("Pulling latest code from GitHub...", "RUN")
    # First fix git safe.directory (HOME must be set explicitly for qemu-ga)
    exec_cmd("export HOME=/root && git config --global --add safe.directory /home/mycosoft/mycosoft/website", 10)
    code, out = exec_cmd("export HOME=/root && cd /home/mycosoft/mycosoft/website && git fetch origin && git reset --hard origin/main", 30)
    if code == 0:
        log("Code updated", "OK")
    else:
        log(f"Git pull issue: {out[:100]}", "WARN")
    
    # Step 3: Rebuild Docker image
    log("Rebuilding Docker image (this takes ~60s)...", "RUN")
    code, out = exec_cmd("cd /home/mycosoft/mycosoft/mas && docker compose -f docker-compose.always-on.yml build mycosoft-website --no-cache 2>&1", 300)
    if code == 0:
        log("Docker build complete", "OK")
    else:
        log(f"Build issue: {out[:200]}", "WARN")
    
    # Step 4: Restart container
    log("Restarting website container...", "RUN")
    code, out = exec_cmd("cd /home/mycosoft/mycosoft/mas && docker compose -f docker-compose.always-on.yml up -d mycosoft-website 2>&1", 60)
    if code == 0:
        log("Container restarted", "OK")
    else:
        log(f"Restart issue: {out[:100]}", "WARN")
    
    # Step 5: Verify
    log("Verifying deployment...", "RUN")
    code, out = exec_cmd("docker ps --format '{{.Names}} {{.Status}}' | grep website", 10)
    if code == 0 and "Up" in out:
        log(f"Website running: {out.strip()}", "OK")
    else:
        log("Could not verify container status", "WARN")
    
    # Step 6: Purge cache
    log("Purging Cloudflare cache...", "RUN")
    if purge_cloudflare():
        log("Cloudflare cache purged", "OK")
    else:
        log("Purge Cloudflare manually if needed", "WARN")
    
    elapsed = time.time() - start
    
    print("\n" + "="*60)
    print(f"  [OK] DEPLOYMENT COMPLETE in {elapsed:.1f}s")
    print("="*60)
    print("\nTest URLs:")
    print("   https://sandbox.mycosoft.com")
    print("   https://sandbox.mycosoft.com/natureos/devices")
    print()

if __name__ == "__main__":
    main()
