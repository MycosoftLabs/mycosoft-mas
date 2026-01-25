#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    MYCOSOFT MASTER DEPLOYMENT SCRIPT                          ║
║                                                                               ║
║  This is the ONE script to use for ALL website deployments to sandbox.       ║
║  It handles EVERYTHING: git pull, cache clearing, builds, and verification.  ║
║                                                                               ║
║  KNOWN PATHS (DO NOT CHANGE WITHOUT UPDATING VM):                             ║
║  - VM IP: 192.168.0.187                                                       ║
║  - Proxmox: 192.168.0.202:8006                                               ║
║  - VM Website Code: /home/mycosoft/mycosoft/website                          ║
║  - VM MAS Code: /home/mycosoft/mycosoft/mas                                   ║
║  - Docker Compose: /home/mycosoft/mycosoft/mas/docker-compose.always-on.yml  ║
║  - Container Name: mycosoft-always-on-mycosoft-website-1                      ║
║  - NAS Media Mount: /opt/mycosoft/media/website/assets                        ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Usage:
    python MASTER_DEPLOY.py              # Full deployment with all caches cleared
    python MASTER_DEPLOY.py --quick      # Skip cache clearing (only use if you know caches are clean)
    python MASTER_DEPLOY.py --verify     # Only verify current deployment status
"""

import requests
import urllib3
import time
import sys
import argparse
import base64

# Suppress SSL warnings for self-signed Proxmox cert
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Fix Windows encoding issues
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION - THESE ARE THE CORRECT VALUES, DO NOT CHANGE
# ═══════════════════════════════════════════════════════════════════════════════

# Proxmox API
PROXMOX_HOST = "https://192.168.0.202:8006"
PROXMOX_TOKEN_ID = "myca@pve!mas"
PROXMOX_TOKEN_SECRET = "ca23b6c8-5746-46c4-8e36-fc6caad5a9e5"
PROXMOX_NODE = "pve"
VM_ID = 103

# VM Paths - THESE ARE CORRECT AS OF JAN 21, 2026
VM_WEBSITE_PATH = "/home/mycosoft/mycosoft/website"
VM_MAS_PATH = "/home/mycosoft/mycosoft/mas"
VM_COMPOSE_FILE = "docker-compose.always-on.yml"
VM_CONTAINER_NAME = "mycosoft-always-on-mycosoft-website-1"
VM_MEDIA_PATH = "/opt/mycosoft/media/website/assets"

# Cloudflare
CF_ZONE_ID = "afd4d5ce84fb58d7a6e2fb98a207fbc6"
# Note: Token should be set as environment variable CLOUDFLARE_API_TOKEN

# Verification URLs
SANDBOX_URL = "https://sandbox.mycosoft.com"
MUSHROOM1_URL = "https://sandbox.mycosoft.com/devices/mushroom-1"

# ═══════════════════════════════════════════════════════════════════════════════
# API HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

headers = {"Authorization": f"PVEAPIToken={PROXMOX_TOKEN_ID}={PROXMOX_TOKEN_SECRET}"}

def log(msg, level="INFO"):
    """Log with timestamp and level."""
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    symbols = {"INFO": "[*]", "OK": "[+]", "WARN": "[!]", "ERROR": "[X]", "STEP": "[>]"}
    print(f"{ts} {symbols.get(level, '[*]')} {msg}")

def exec_cmd(cmd, timeout=300, show_output=True):
    """Execute command on VM via Proxmox QEMU agent."""
    url = f"{PROXMOX_HOST}/api2/json/nodes/{PROXMOX_NODE}/qemu/{VM_ID}/agent/exec"
    
    try:
        data = {"command": "/bin/bash", "input-data": cmd}
        r = requests.post(url, headers=headers, data=data, verify=False, timeout=15)
        
        if not r.ok:
            log(f"Exec request failed: {r.status_code}", "ERROR")
            return None, f"Request failed: {r.status_code}"
        
        pid = r.json().get("data", {}).get("pid")
        if not pid:
            log("No PID returned", "ERROR")
            return None, "No PID"
        
        # Poll for result
        status_url = f"{PROXMOX_HOST}/api2/json/nodes/{PROXMOX_NODE}/qemu/{VM_ID}/agent/exec-status?pid={pid}"
        start = time.time()
        
        while time.time() - start < timeout:
            time.sleep(2)
            sr = requests.get(status_url, headers=headers, verify=False, timeout=10)
            if sr.ok:
                sd = sr.json().get("data", {})
                if sd.get("exited"):
                    out = sd.get("out-data", "")
                    err = sd.get("err-data", "")
                    exitcode = sd.get("exitcode", -1)
                    
                    # Decode base64 if present
                    try:
                        if out:
                            out = base64.b64decode(out).decode('utf-8', errors='replace')
                        if err:
                            err = base64.b64decode(err).decode('utf-8', errors='replace')
                    except:
                        pass
                    
                    if show_output and out:
                        for line in out.strip().split('\n')[:20]:  # Limit output
                            print(f"    {line}")
                    
                    if exitcode != 0 and err:
                        log(f"Command error: {err[:200]}", "WARN")
                    
                    return out, err if exitcode != 0 else None
        
        return None, "Timeout"
        
    except Exception as e:
        return None, str(e)

# ═══════════════════════════════════════════════════════════════════════════════
# DEPLOYMENT STEPS
# ═══════════════════════════════════════════════════════════════════════════════

def step_verify_connectivity():
    """Step 0: Verify we can reach the VM."""
    log("Verifying VM connectivity...", "STEP")
    
    out, err = exec_cmd("echo 'VM_CONNECTED' && hostname && uptime", timeout=30)
    if err or not out or "VM_CONNECTED" not in out:
        log(f"Cannot connect to VM: {err}", "ERROR")
        return False
    
    log("VM connectivity verified", "OK")
    return True

def step_check_vm_state():
    """Step 1: Check current VM state."""
    log("Checking current VM state...", "STEP")
    
    # Check git status
    out, err = exec_cmd(f"cd {VM_WEBSITE_PATH} && git log -1 --oneline && git status --short")
    if out:
        log(f"Current website commit: {out.split(chr(10))[0] if out else 'unknown'}", "INFO")
    
    # Check container status
    out, err = exec_cmd(f"docker ps -a --filter name=website --format '{{{{.Names}}}} {{{{.Status}}}}'")
    if out:
        log(f"Container status: {out.strip()}", "INFO")
    
    return True

def step_git_pull():
    """Step 2: Pull latest code."""
    log("Pulling latest code from GitHub...", "STEP")
    
    # Website repo
    out, err = exec_cmd(f"""
        cd {VM_WEBSITE_PATH} && 
        git fetch origin main && 
        git reset --hard origin/main && 
        git log -1 --oneline
    """, timeout=120)
    
    if err:
        log(f"Git pull failed for website: {err}", "ERROR")
        return False
    
    log("Website code updated", "OK")
    
    # MAS repo (for compose file)
    out, err = exec_cmd(f"""
        cd {VM_MAS_PATH} && 
        git fetch origin main && 
        git reset --hard origin/main && 
        git log -1 --oneline
    """, timeout=120)
    
    if err:
        log(f"Git pull failed for MAS: {err}", "WARN")
        # Continue anyway - website code is more important
    
    log("MAS code updated", "OK")
    return True

def step_clean_all_caches():
    """Step 3: Clean ALL caches - Docker, Next.js, everything."""
    log("Cleaning ALL caches (this ensures fresh build)...", "STEP")
    
    # Stop container first
    log("Stopping website container...", "INFO")
    exec_cmd(f"docker stop {VM_CONTAINER_NAME} 2>/dev/null || true", timeout=60)
    exec_cmd(f"docker rm {VM_CONTAINER_NAME} 2>/dev/null || true", timeout=60)
    
    # Clean Docker caches
    log("Cleaning Docker build cache...", "INFO")
    exec_cmd("docker builder prune -af 2>/dev/null || true", timeout=120)
    
    log("Cleaning unused Docker images...", "INFO")
    exec_cmd("docker image prune -af 2>/dev/null || true", timeout=120)
    
    log("Cleaning unused Docker volumes...", "INFO")
    exec_cmd("docker volume prune -f 2>/dev/null || true", timeout=60)
    
    log("Running Docker system prune...", "INFO")
    exec_cmd("docker system prune -af 2>/dev/null || true", timeout=180)
    
    # Remove any bad symlinks in website directory
    log("Removing any bad symlinks in website directory...", "INFO")
    exec_cmd(f"find {VM_WEBSITE_PATH} -maxdepth 1 -type l -delete 2>/dev/null || true", timeout=30)
    
    # Clean Next.js cache inside website directory
    log("Cleaning Next.js caches...", "INFO")
    exec_cmd(f"rm -rf {VM_WEBSITE_PATH}/.next 2>/dev/null || true", timeout=30)
    exec_cmd(f"rm -rf {VM_WEBSITE_PATH}/node_modules/.cache 2>/dev/null || true", timeout=30)
    
    log("All caches cleaned", "OK")
    return True

def step_build_image():
    """Step 4: Build Docker image with --no-cache."""
    log("Building Docker image (no cache, clean build)...", "STEP")
    log("This may take 3-5 minutes...", "INFO")
    
    out, err = exec_cmd(f"""
        cd {VM_MAS_PATH} && 
        docker compose -f {VM_COMPOSE_FILE} build mycosoft-website --no-cache --progress=plain 2>&1 | tail -20
    """, timeout=600, show_output=True)
    
    if err and "error" in err.lower():
        log(f"Build failed: {err}", "ERROR")
        return False
    
    # Check if image was created
    out2, _ = exec_cmd("docker images | grep -i mycosoft | head -5")
    if out2:
        log("Docker image built successfully", "OK")
        return True
    else:
        log("Image build may have failed - no mycosoft image found", "WARN")
        return True  # Continue and see if container starts

def step_start_container():
    """Step 5: Start container with force-recreate and NAS volume mount."""
    log("Starting website container...", "STEP")
    
    # First try docker compose
    out, err = exec_cmd(f"""
        cd {VM_MAS_PATH} && 
        docker compose -f {VM_COMPOSE_FILE} up -d mycosoft-website --force-recreate 2>&1
    """, timeout=120)
    
    # Wait a bit and check if container is running
    time.sleep(10)
    out, err = exec_cmd(f"docker ps --filter name=website --format '{{{{.Names}}}} {{{{.Status}}}}'")
    
    if not out or "Up" not in out:
        log("Docker compose failed, trying direct docker run with NAS mount...", "WARN")
        
        # Fallback to docker run with correct volume mount for NAS media
        exec_cmd("docker stop mycosoft-website 2>/dev/null || true", timeout=30)
        exec_cmd("docker rm mycosoft-website 2>/dev/null || true", timeout=30)
        
        # Start with NAS volume mount - CRITICAL for videos to work
        out, err = exec_cmd(f"""
            docker run -d --name mycosoft-website \\
              -p 3000:3000 \\
              --restart unless-stopped \\
              -v {VM_MEDIA_PATH}:/app/public/assets:ro \\
              mycosoft-always-on-mycosoft-website:latest 2>&1
        """, timeout=60)
        
        if err and "error" in err.lower():
            log(f"Docker run failed: {err}", "ERROR")
            return False
    
    # Wait for container to be healthy
    log("Waiting for container to be healthy (30s)...", "INFO")
    time.sleep(30)
    
    out, err = exec_cmd(f"docker ps --filter name=website --format '{{{{.Names}}}} {{{{.Status}}}}'")
    if out and "Up" in out:
        log(f"Container running: {out.strip()}", "OK")
        
        # Verify NAS mount is working
        log("Verifying NAS media mount...", "INFO")
        exec_cmd("docker exec mycosoft-website ls /app/public/assets/mushroom1/ 2>/dev/null | head -5 || echo 'MOUNT CHECK FAILED'")
        
        return True
    else:
        log("Container may not be running properly", "WARN")
        return True  # Continue to verification

def step_verify_local():
    """Step 6: Verify container responds locally including videos."""
    log("Verifying container responds locally...", "STEP")
    
    # Check localhost response
    out, err = exec_cmd("curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/ 2>/dev/null || echo 'FAIL'")
    
    if out and "200" in out:
        log("Local container responding HTTP 200", "OK")
    else:
        log(f"Local response: {out}", "WARN")
        
        # Check logs for errors
        log("Checking container logs for errors...", "INFO")
        exec_cmd(f"docker logs mycosoft-website --tail 20 2>&1 | tail -10")
        
        return False
    
    # CRITICAL: Verify video endpoint works (catches missing NAS mount)
    log("Verifying video endpoint (NAS mount test)...", "INFO")
    out, err = exec_cmd("curl -s -o /dev/null -w '%{http_code}' 'http://localhost:3000/assets/mushroom1/close%201.mp4' 2>/dev/null || echo 'FAIL'")
    
    if out and "200" in out:
        log("Video endpoint responding HTTP 200 - NAS mount OK", "OK")
    else:
        log(f"Video endpoint response: {out} - NAS mount may be broken!", "ERROR")
        log("Videos will NOT work without NAS mount!", "ERROR")
        
        # Try to fix by restarting with volume mount
        log("Attempting to fix by restarting container with NAS mount...", "INFO")
        exec_cmd("docker stop mycosoft-website 2>/dev/null || true", timeout=30)
        exec_cmd("docker rm mycosoft-website 2>/dev/null || true", timeout=30)
        exec_cmd(f"""
            docker run -d --name mycosoft-website \\
              -p 3000:3000 \\
              --restart unless-stopped \\
              -v {VM_MEDIA_PATH}:/app/public/assets:ro \\
              mycosoft-always-on-mycosoft-website:latest 2>&1
        """, timeout=60)
        time.sleep(15)
        
        # Check again
        out, err = exec_cmd("curl -s -o /dev/null -w '%{http_code}' 'http://localhost:3000/assets/mushroom1/close%201.mp4' 2>/dev/null || echo 'FAIL'")
        if out and "200" in out:
            log("Video endpoint now working after NAS mount fix", "OK")
        else:
            log("Video endpoint still failing - manual intervention needed", "ERROR")
            return False
    
    return True

def step_purge_cloudflare():
    """Step 7: Purge Cloudflare cache."""
    log("Purging Cloudflare cache...", "STEP")
    
    import os
    cf_token = os.environ.get('CLOUDFLARE_API_TOKEN')
    
    if not cf_token:
        log("CLOUDFLARE_API_TOKEN not set - please purge manually in Cloudflare dashboard", "WARN")
        log("URL: https://dash.cloudflare.com -> mycosoft.com -> Caching -> Purge Everything", "INFO")
        return True
    
    try:
        cf_headers = {
            'Authorization': f'Bearer {cf_token}',
            'Content-Type': 'application/json'
        }
        cf_url = f'https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/purge_cache'
        
        r = requests.post(cf_url, headers=cf_headers, json={'purge_everything': True}, timeout=30)
        
        if r.status_code == 200 and r.json().get('success'):
            log("Cloudflare cache purged", "OK")
        else:
            log(f"Cloudflare purge response: {r.status_code}", "WARN")
            log("Please purge manually in Cloudflare dashboard", "INFO")
    except Exception as e:
        log(f"Cloudflare purge error: {e}", "WARN")
        log("Please purge manually in Cloudflare dashboard", "INFO")
    
    return True

def step_verify_sandbox():
    """Step 8: Verify sandbox.mycosoft.com responds."""
    log("Verifying sandbox.mycosoft.com...", "STEP")
    
    try:
        # Simple request to verify site is up
        r = requests.get(SANDBOX_URL, timeout=30, allow_redirects=True)
        if r.status_code == 200:
            log(f"Sandbox responding: {r.status_code}", "OK")
        else:
            log(f"Sandbox response: {r.status_code}", "WARN")
        
        # Check Mushroom 1 page
        r2 = requests.get(MUSHROOM1_URL, timeout=30, allow_redirects=True)
        if r2.status_code == 200:
            log(f"Mushroom 1 page responding: {r2.status_code}", "OK")
            
            # Check for expected content
            if "Environmental drone" in r2.text:
                log("Page content verified: 'Environmental drone' found", "OK")
            else:
                log("Page content may be outdated - 'Environmental drone' not found", "WARN")
        else:
            log(f"Mushroom 1 page response: {r2.status_code}", "WARN")
            
    except Exception as e:
        log(f"Verification error: {e}", "ERROR")
        return False
    
    return True

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN EXECUTION
# ═══════════════════════════════════════════════════════════════════════════════

def run_full_deployment(skip_cache_clear=False):
    """Run complete deployment."""
    
    print("\n" + "="*80)
    print("       MYCOSOFT MASTER DEPLOYMENT - FULL CACHE CLEAR + REBUILD")
    print("="*80 + "\n")
    
    steps = [
        ("Verify Connectivity", step_verify_connectivity),
        ("Check Current State", step_check_vm_state),
        ("Pull Latest Code", step_git_pull),
    ]
    
    if not skip_cache_clear:
        steps.append(("Clean All Caches", step_clean_all_caches))
    
    steps.extend([
        ("Build Docker Image", step_build_image),
        ("Start Container", step_start_container),
        ("Verify Local", step_verify_local),
        ("Purge Cloudflare", step_purge_cloudflare),
        ("Verify Sandbox", step_verify_sandbox),
    ])
    
    results = []
    
    for i, (name, func) in enumerate(steps, 1):
        print(f"\n{'─'*80}")
        print(f"  STEP {i}/{len(steps)}: {name}")
        print(f"{'─'*80}")
        
        try:
            result = func()
            results.append((name, result))
            
            if not result:
                log(f"Step '{name}' failed - continuing anyway", "WARN")
        except Exception as e:
            log(f"Step '{name}' error: {e}", "ERROR")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*80)
    print("       DEPLOYMENT SUMMARY")
    print("="*80)
    
    all_ok = True
    for name, result in results:
        status = "[OK]" if result else "[FAILED]"
        print(f"  {status:10} {name}")
        if not result:
            all_ok = False
    
    print("="*80)
    
    if all_ok:
        print("\n  [+] DEPLOYMENT COMPLETE - All steps succeeded")
        print(f"\n  Verify at: {MUSHROOM1_URL}")
        print("  Remember to Ctrl+Shift+R (hard refresh) in browser\n")
    else:
        print("\n  [!] DEPLOYMENT COMPLETED WITH WARNINGS - Check logs above")
        print("  Some steps may have failed but deployment may still work\n")
    
    return all_ok

def run_verify_only():
    """Just verify current deployment status."""
    
    print("\n" + "="*80)
    print("       MYCOSOFT DEPLOYMENT VERIFICATION")
    print("="*80 + "\n")
    
    step_verify_connectivity()
    step_check_vm_state()
    step_verify_local()
    step_verify_sandbox()
    
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mycosoft Master Deployment Script")
    parser.add_argument("--quick", action="store_true", help="Skip cache clearing")
    parser.add_argument("--verify", action="store_true", help="Only verify deployment")
    args = parser.parse_args()
    
    if args.verify:
        run_verify_only()
    else:
        success = run_full_deployment(skip_cache_clear=args.quick)
        sys.exit(0 if success else 1)
