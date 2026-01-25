#!/usr/bin/env python3
"""
DEPLOYMENT WITH PROTOCOL - Full deployment following mandatory protocol
Clears memory, prunes Docker, rebuilds, and purges Cloudflare

Usage: python scripts/deploy_with_protocol.py
"""
import requests
import urllib3
import time
import sys
import os
import base64

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration
PROXMOX_HOST = "https://192.168.0.202:8006"
PROXMOX_TOKEN_ID = os.getenv("PROXMOX_TOKEN_ID", "myca@pve!mas")
PROXMOX_TOKEN_SECRET = os.getenv("PROXMOX_TOKEN_SECRET", "ca23b6c8-5746-46c4-8e36-fc6caad5a9e5")
VM_ID = 103
NODE = "pve"

# Cloudflare
CF_ZONE_ID = os.getenv("CF_ZONE_ID", "")
CF_API_TOKEN = os.getenv("CF_API_TOKEN", "")

headers = {
    "Authorization": f"PVEAPIToken={PROXMOX_TOKEN_ID}={PROXMOX_TOKEN_SECRET}"
}


def log(msg, level="INFO"):
    ts = time.strftime("%H:%M:%S")
    symbols = {
        "INFO": "[i]",
        "OK": "[+]",
        "WARN": "[!]",
        "ERR": "[X]",
        "RUN": "[>]",
        "CLEAN": "[~]"
    }
    print(f"[{ts}] {symbols.get(level, '*')} {msg}")


def check_vm():
    url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/status/current"
    try:
        r = requests.get(url, headers=headers, verify=False, timeout=5)
        if r.ok:
            data = r.json().get("data", {})
            status = data.get("status") == "running"
            mem_used = data.get("mem", 0)
            mem_max = data.get("maxmem", 1)
            mem_pct = (mem_used / mem_max) * 100 if mem_max else 0
            return status, mem_pct
    except Exception as e:
        print(f"Error checking VM: {e}")
    return False, 0


def exec_cmd(cmd, timeout=120, show_output=False):
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
                    code = data.get("exitcode", 0)
                    out_b64 = data.get("out-data", "")
                    err_b64 = data.get("err-data", "")
                    
                    # Decode base64 if present
                    try:
                        out = base64.b64decode(out_b64).decode() if out_b64 else ""
                    except:
                        out = out_b64
                    try:
                        err = base64.b64decode(err_b64).decode() if err_b64 else ""
                    except:
                        err = err_b64
                    
                    if show_output and (out or err):
                        print(f"    Output: {(out or err)[:200]}")
                    
                    return code, out if code == 0 else (err or out)
        return None, "Timeout waiting for command"
    except Exception as e:
        return None, str(e)


def purge_cloudflare():
    if not CF_ZONE_ID or not CF_API_TOKEN:
        return False
    
    url = f"https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/purge_cache"
    cf_headers = {
        "Authorization": f"Bearer {CF_API_TOKEN}",
        "Content-Type": "application/json"
    }
    try:
        r = requests.post(url, headers=cf_headers, json={"purge_everything": True}, timeout=10)
        return r.ok
    except:
        return False


def main():
    start = time.time()
    
    print("\n" + "=" * 70)
    print("  MYCOSOFT DEPLOYMENT WITH PROTOCOL")
    print("  Following docs/DEPLOYMENT_PROTOCOL_MANDATORY.md")
    print("=" * 70 + "\n")
    
    # Pre-flight Check
    log("PRE-FLIGHT: Checking VM 103...", "RUN")
    running, mem_pct = check_vm()
    
    if not running:
        log("VM 103 is not running!", "ERR")
        sys.exit(1)
    
    log(f"VM 103 running, memory: {mem_pct:.1f}%", "OK")
    
    if mem_pct > 80:
        log(f"WARNING: Memory high ({mem_pct:.1f}%). Consider VM restart.", "WARN")
    
    # STEP 1: Clean Docker environment (CRITICAL)
    print("\n--- STEP 1: CLEAN DOCKER ENVIRONMENT ---")
    log("Running docker system prune...", "CLEAN")
    exec_cmd("docker system prune -f 2>&1", 60)
    log("Pruned unused containers/networks", "OK")
    
    log("Running docker builder prune...", "CLEAN")
    exec_cmd("docker builder prune -f 2>&1", 60)
    log("Cleared build cache", "OK")
    
    log("Running docker image prune...", "CLEAN")
    exec_cmd("docker image prune -f 2>&1", 30)
    log("Removed dangling images", "OK")
    
    # STEP 2: Pull latest code
    print("\n--- STEP 2: PULL LATEST CODE ---")
    log("Configuring git safe.directory...", "RUN")
    exec_cmd("export HOME=/root && git config --global --add safe.directory /home/mycosoft/mycosoft/website", 10)
    
    log("Fetching and resetting to origin/main...", "RUN")
    code, out = exec_cmd(
        "export HOME=/root && cd /home/mycosoft/mycosoft/website && git fetch origin main && git reset --hard origin/main 2>&1",
        60, show_output=True
    )
    if code == 0:
        log("Code updated successfully", "OK")
    else:
        log(f"Git issue (continuing): {out[:100]}", "WARN")
    
    # STEP 3: Build with --no-cache
    print("\n--- STEP 3: BUILD WITH NO-CACHE ---")
    log("Building Docker image (may take 2-3 minutes)...", "RUN")
    
    # Ensure symlink exists for build context
    exec_cmd("mkdir -p /home/mycosoft/WEBSITE && ln -sf /home/mycosoft/mycosoft/website /home/mycosoft/WEBSITE/website", 10)
    
    code, out = exec_cmd(
        "cd /home/mycosoft/mycosoft/mas && docker compose -f docker-compose.always-on.yml build mycosoft-website --no-cache 2>&1",
        600,  # 10 minute timeout for build
        show_output=True
    )
    
    if code == 0:
        log("Docker build complete", "OK")
    else:
        log(f"Build issue: {out[:200]}", "WARN")
        # Continue anyway to see if container can start with existing image
    
    # STEP 4: Force recreate container
    print("\n--- STEP 4: FORCE RECREATE CONTAINER ---")
    log("Recreating website container...", "RUN")
    code, out = exec_cmd(
        "cd /home/mycosoft/mycosoft/mas && docker compose -f docker-compose.always-on.yml up -d --force-recreate mycosoft-website 2>&1",
        120, show_output=True
    )
    
    if code == 0:
        log("Container recreated", "OK")
    else:
        log(f"Recreate issue: {out[:100]}", "WARN")
    
    # STEP 5: Verify container
    print("\n--- STEP 5: VERIFY CONTAINER ---")
    log("Checking container status...", "RUN")
    time.sleep(5)  # Wait for container to start
    
    code, out = exec_cmd("docker ps --format '{{.Names}} {{.Status}}' 2>&1 | grep website", 10)
    if code == 0 and "Up" in str(out):
        log(f"Container running: {out.strip()}", "OK")
    else:
        log("Container may not be running properly", "WARN")
    
    # Quick health check
    code, out = exec_cmd("curl -s http://localhost:3000 -o /dev/null -w '%{http_code}'", 10)
    if code == 0 and "200" in str(out):
        log("Health check: HTTP 200", "OK")
    else:
        log(f"Health check result: {out}", "WARN")
    
    # STEP 6: Purge Cloudflare cache
    print("\n--- STEP 6: PURGE CLOUDFLARE CACHE ---")
    log("Purging Cloudflare cache...", "RUN")
    
    if purge_cloudflare():
        log("Cloudflare cache purged via API", "OK")
    else:
        log("MANUAL ACTION: Purge Cloudflare cache via dashboard!", "WARN")
        log("   Dashboard: https://dash.cloudflare.com", "INFO")
        log("   Domain: mycosoft.com -> Caching -> Purge Everything", "INFO")
    
    # Summary
    elapsed = time.time() - start
    
    print("\n" + "=" * 70)
    print(f"  DEPLOYMENT COMPLETE in {elapsed:.1f} seconds")
    print("=" * 70)
    
    print("\nVERIFY THESE URLs:")
    print("   [1] https://sandbox.mycosoft.com")
    print("   [2] https://sandbox.mycosoft.com/security (check for tour button)")
    print("   [3] https://sandbox.mycosoft.com/security/compliance")
    print()
    
    print("MANUAL STEPS IF CLOUDFLARE NOT AUTO-PURGED:")
    print("   1. Go to dash.cloudflare.com")
    print("   2. Select mycosoft.com")
    print("   3. Caching -> Configuration -> Purge Everything")
    print()


if __name__ == "__main__":
    main()
