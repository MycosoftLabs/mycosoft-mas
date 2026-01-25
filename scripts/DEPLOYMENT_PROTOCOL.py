#!/usr/bin/env python3
"""
===============================================================================
                    MYCOSOFT DEPLOYMENT PROTOCOL
===============================================================================

This is the SINGLE source of truth for deployments. Follow this exactly.

DEPLOYMENT STEPS:
=================

1. PRE-FLIGHT CHECKS
   - Verify local build works (npm run dev on port 3010)
   - Verify cloudflared NOT running on Windows
   - Commit and push all changes to GitHub

2. VM DEPLOYMENT (via Proxmox API - NO SSH)
   a. Pull latest code: git fetch && git reset --hard origin/main
   b. Clean Docker resources: docker system prune -f (remove unused)
   c. Build with --no-cache: docker compose build --no-cache
   d. Restart container: docker compose up -d --force-recreate
   e. Wait for healthy status

3. POST-DEPLOYMENT (CRITICAL - NEVER SKIP)
   a. PURGE CLOUDFLARE CACHE - Mandatory after every deployment
   b. Restart cloudflared service if needed
   c. Verify via health endpoints
   d. Clear browser cache and test

4. VERIFICATION
   a. Test sandbox URL returns new content
   b. Check specific pages that changed
   c. Verify no console errors

KEY PATHS ON VM 103:
====================
- Website Code: /home/mycosoft/mycosoft/website
- Compose File: /home/mycosoft/mycosoft/mas/docker-compose.always-on.yml
- Environment:  /home/mycosoft/mycosoft/mas/.env
- Media Mount:  /opt/mycosoft/media/website/assets

CRITICAL RULES:
===============
1. NEXT_PUBLIC_* vars must be in build.args (embedded at build time)
2. Always use --no-cache for Docker builds
3. ALWAYS purge Cloudflare after deployment
4. Container restart required for new /assets/* files

===============================================================================
"""
import requests
import urllib3
import time
import sys
import os

urllib3.disable_warnings()

# === CONFIGURATION ===
PROXMOX_HOST = "https://192.168.0.202:8006"
PROXMOX_TOKEN_ID = "myca@pve!mas"
PROXMOX_TOKEN_SECRET = "ca23b6c8-5746-46c4-8e36-fc6caad5a9e5"
VM_ID = 103
NODE = "pve"

# Cloudflare - Set these in your environment
CF_ZONE_ID = os.getenv("CF_ZONE_ID", "")
CF_API_TOKEN = os.getenv("CF_API_TOKEN", "")

# Paths on VM
WEBSITE_PATH = "/home/mycosoft/mycosoft/website"
MAS_PATH = "/home/mycosoft/mycosoft/mas"
COMPOSE_FILE = "docker-compose.always-on.yml"

headers = {"Authorization": f"PVEAPIToken={PROXMOX_TOKEN_ID}={PROXMOX_TOKEN_SECRET}"}


def log(msg, level="INFO"):
    """Print with timestamp and level"""
    ts = time.strftime("%H:%M:%S")
    symbols = {"INFO": "[*]", "OK": "[+]", "WARN": "[!]", "ERR": "[X]", "RUN": "[>]", "CLEAN": "[~]"}
    print(f"{ts} {symbols.get(level, '[*]')} {msg}")


def exec_cmd(cmd, timeout=300, show_progress=True):
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
        
        status_url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/exec-status?pid={pid}"
        start = time.time()
        while time.time() - start < timeout:
            time.sleep(3)
            r2 = requests.get(status_url, headers=headers, verify=False, timeout=10)
            if r2.ok:
                result = r2.json().get("data", {})
                if result.get("exited"):
                    return result.get("exitcode", 0), result.get("out-data", "") + result.get("err-data", "")
            if show_progress:
                elapsed = int(time.time() - start)
                if elapsed % 30 == 0 and elapsed > 0:
                    print(f"       ... {elapsed}s elapsed ...")
        return None, "Timeout"
    except Exception as e:
        return None, str(e)


def check_vm():
    """Check if VM is running"""
    url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/status/current"
    try:
        r = requests.get(url, headers=headers, verify=False, timeout=5)
        if r.ok:
            data = r.json().get("data", {})
            mem_used = data.get("mem", 0) / (1024**3)
            mem_max = data.get("maxmem", 1) / (1024**3)
            cpu = data.get("cpu", 0) * 100
            log(f"VM 103: CPU={cpu:.1f}% MEM={mem_used:.1f}/{mem_max:.0f}GB", "INFO")
            return data.get("status") == "running"
    except:
        pass
    return False


def purge_cloudflare():
    """Purge Cloudflare cache - CRITICAL after every deployment"""
    if not CF_ZONE_ID or not CF_API_TOKEN:
        log("Cloudflare credentials not set in environment", "WARN")
        log("Set CF_ZONE_ID and CF_API_TOKEN, or purge manually:", "WARN")
        log("  https://dash.cloudflare.com -> mycosoft.com -> Caching -> Purge Everything", "INFO")
        return False
    
    url = f"https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/purge_cache"
    cf_headers = {"Authorization": f"Bearer {CF_API_TOKEN}", "Content-Type": "application/json"}
    try:
        r = requests.post(url, headers=cf_headers, json={"purge_everything": True}, timeout=15)
        if r.ok:
            return True
        log(f"Cloudflare purge failed: {r.status_code}", "WARN")
    except Exception as e:
        log(f"Cloudflare purge error: {e}", "WARN")
    return False


def deploy():
    """Full deployment protocol"""
    print()
    print("=" * 70)
    print("           MYCOSOFT DEPLOYMENT PROTOCOL")
    print("=" * 70)
    start_time = time.time()
    
    # === STEP 1: PRE-FLIGHT ===
    print("\n[PHASE 1] PRE-FLIGHT CHECKS")
    print("-" * 40)
    
    log("Checking VM 103...", "RUN")
    if not check_vm():
        log("VM 103 not running!", "ERR")
        return False
    log("VM is running and reachable", "OK")
    
    # === STEP 2: CLEAN DOCKER RESOURCES ===
    print("\n[PHASE 2] CLEAN DOCKER RESOURCES")
    print("-" * 40)
    
    log("Removing unused Docker resources...", "CLEAN")
    code, out = exec_cmd("docker system prune -f 2>&1 | tail -5", timeout=60)
    if code == 0:
        log("Docker cleanup complete", "OK")
    else:
        log("Docker cleanup issue (non-fatal)", "WARN")
    
    # === STEP 3: GIT PULL ===
    print("\n[PHASE 3] UPDATE CODE")
    print("-" * 40)
    
    log("Fixing git safe directory...", "RUN")
    exec_cmd(f"export HOME=/root && git config --global --add safe.directory {WEBSITE_PATH}", 10, False)
    
    log("Pulling latest from GitHub...", "RUN")
    code, out = exec_cmd(f"export HOME=/root && cd {WEBSITE_PATH} && git fetch origin && git reset --hard origin/main && git log --oneline -1", 30)
    if code == 0:
        log("Code updated", "OK")
        if out:
            # Try to extract commit message
            lines = [l for l in out.split('\n') if l.strip()]
            if lines:
                log(f"  Latest: {lines[-1][:70]}", "INFO")
    else:
        log(f"Git issue: {str(out)[:100]}", "WARN")
    
    # === STEP 4: DOCKER BUILD ===
    print("\n[PHASE 4] DOCKER BUILD (2-5 minutes)")
    print("-" * 40)
    
    log("Building Docker image with --no-cache...", "RUN")
    build_cmd = f"cd {MAS_PATH} && docker compose -f {COMPOSE_FILE} build mycosoft-website --no-cache 2>&1"
    code, out = exec_cmd(build_cmd, timeout=600)
    if code == 0:
        log("Docker build complete", "OK")
    else:
        log("Build may have issues - checking...", "WARN")
    
    # === STEP 5: RESTART CONTAINER ===
    print("\n[PHASE 5] RESTART CONTAINER")
    print("-" * 40)
    
    log("Restarting website container...", "RUN")
    restart_cmd = f"cd {MAS_PATH} && docker compose -f {COMPOSE_FILE} up -d --force-recreate mycosoft-website 2>&1"
    code, out = exec_cmd(restart_cmd, timeout=120)
    if code == 0:
        log("Container restarted", "OK")
    else:
        log(f"Restart issue: {str(out)[:100]}", "WARN")
    
    log("Waiting for container health check...", "RUN")
    time.sleep(20)
    
    code, out = exec_cmd("docker ps --format '{{.Names}} {{.Status}}' | grep website", 15)
    if out and "healthy" in str(out).lower():
        log(f"Container healthy", "OK")
    elif out and "Up" in str(out):
        log(f"Container running (health check pending)", "OK")
    else:
        log("Container status unclear - check manually", "WARN")
    
    # === STEP 6: PURGE CLOUDFLARE CACHE ===
    print("\n[PHASE 6] PURGE CLOUDFLARE CACHE (CRITICAL)")
    print("-" * 40)
    
    log("Purging Cloudflare cache...", "RUN")
    if purge_cloudflare():
        log("Cloudflare cache purged successfully", "OK")
    else:
        log("MANUAL ACTION REQUIRED: Purge Cloudflare cache!", "ERR")
        log("Go to: https://dash.cloudflare.com", "INFO")
        log("Select: mycosoft.com -> Caching -> Purge Everything", "INFO")
    
    # === STEP 7: VERIFY ===
    print("\n[PHASE 7] VERIFICATION")
    print("-" * 40)
    
    log("Checking website health endpoint...", "RUN")
    code, out = exec_cmd("curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/ 2>/dev/null", 15)
    if "200" in str(out):
        log("Website responding (HTTP 200)", "OK")
    else:
        log(f"Website response: {out}", "WARN")
    
    # === COMPLETE ===
    elapsed = time.time() - start_time
    print()
    print("=" * 70)
    print(f"  DEPLOYMENT COMPLETE ({elapsed:.0f} seconds)")
    print("=" * 70)
    print()
    print("  TEST URLS:")
    print("    https://sandbox.mycosoft.com")
    print("    https://sandbox.mycosoft.com/security")
    print("    https://sandbox.mycosoft.com/natureos/devices")
    print()
    print("  REMEMBER:")
    print("    - Clear browser cache (Ctrl+Shift+R)")
    print("    - If still seeing old content, manually purge Cloudflare")
    print()
    return True


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print(__doc__)
    else:
        deploy()
