#!/usr/bin/env python3
"""
Mycosoft Sandbox Deployment Script
Uses Proxmox QEMU Guest Agent to execute commands on VM 103

Based on: docs/VM103_DEPLOYMENT_COMPLETE.md
          docs/MYCOSOFT_STACK_DEPLOYMENT.md
"""
import requests
import urllib3
import time
import base64
import json
import subprocess
import sys

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==============================================================================
# Configuration from docs/SESSION_VM_CREATION_JAN17_2026.md
# ==============================================================================
PROXMOX_HOST = "https://192.168.0.202:8006"
PROXMOX_TOKEN_ID = "myca@pve!mas"  # Working token from test_proxmox.py
PROXMOX_TOKEN_SECRET = "ca23b6c8-5746-46c4-8e36-fc6caad5a9e5"
VM_ID = 103
NODE = "pve"

# SSH fallback (from docs/VM103_DEPLOYMENT_COMPLETE.md)
VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "Mushroom1!Mushroom1!"

headers = {
    "Authorization": f"PVEAPIToken={PROXMOX_TOKEN_ID}={PROXMOX_TOKEN_SECRET}"
}

def log(msg, level="INFO"):
    """Log message with timestamp"""
    print(f"[{level}] {msg}")

def api_get(path):
    """GET request to Proxmox API"""
    url = f"{PROXMOX_HOST}/api2/json{path}"
    try:
        r = requests.get(url, headers=headers, verify=False, timeout=30)
        return r.status_code, r.json() if r.ok else r.text
    except Exception as e:
        return 0, str(e)

def api_post(path, data=None):
    """POST request to Proxmox API"""
    url = f"{PROXMOX_HOST}/api2/json{path}"
    try:
        r = requests.post(url, headers=headers, data=data, verify=False, timeout=120)
        return r.status_code, r.json() if r.ok else r.text
    except Exception as e:
        return 0, str(e)

def check_vm_status():
    """Check if VM 103 is running"""
    log("Checking VM 103 status...")
    status, data = api_get(f"/nodes/{NODE}/qemu/{VM_ID}/status/current")
    if status == 200 and isinstance(data, dict):
        vm_data = data.get("data", {})
        vm_status = vm_data.get("status", "unknown")
        vm_name = vm_data.get("name", "unknown")
        log(f"VM {VM_ID} ({vm_name}): {vm_status}")
        return vm_status == "running"
    else:
        log(f"Failed to get VM status: {status} - {data}", "ERROR")
        return False

def exec_via_agent(command, timeout=120):
    """Execute command via QEMU Guest Agent"""
    log(f"Executing via agent: {command[:60]}...")
    
    # Start command
    status, data = api_post(f"/nodes/{NODE}/qemu/{VM_ID}/agent/exec", {
        "command": command
    })
    
    if status != 200:
        log(f"Agent exec failed: {status} - {data}", "ERROR")
        return None
    
    pid = data.get("data", {}).get("pid")
    if not pid:
        log("No PID returned from agent", "ERROR")
        return None
    
    log(f"  Command started with PID {pid}")
    
    # Wait for completion
    start = time.time()
    while time.time() - start < timeout:
        time.sleep(2)
        status, result = api_get(f"/nodes/{NODE}/qemu/{VM_ID}/agent/exec-status?pid={pid}")
        if status == 200 and isinstance(result, dict):
            result_data = result.get("data", {})
            if result_data.get("exited"):
                exit_code = result_data.get("exitcode", -1)
                out_data = result_data.get("out-data", "")
                err_data = result_data.get("err-data", "")
                
                # Decode base64 output if present
                if out_data:
                    try:
                        out_data = base64.b64decode(out_data).decode('utf-8', errors='replace')
                    except:
                        pass
                if err_data:
                    try:
                        err_data = base64.b64decode(err_data).decode('utf-8', errors='replace')
                    except:
                        pass
                
                log(f"  Exit code: {exit_code}")
                if out_data:
                    log(f"  Output: {out_data[:300]}")
                if err_data and exit_code != 0:
                    log(f"  Error: {err_data[:200]}", "WARN")
                return exit_code
    
    log(f"  Command timed out after {timeout}s", "WARN")
    return -1

def check_agent_available():
    """Check if QEMU Guest Agent is responding"""
    log("Checking QEMU Guest Agent...")
    status, data = api_get(f"/nodes/{NODE}/qemu/{VM_ID}/agent/info")
    if status == 200:
        log("  Guest Agent is available")
        return True
    else:
        log(f"  Guest Agent not available: {status}", "WARN")
        return False

def deploy_via_agent():
    """Deploy using QEMU Guest Agent"""
    log("\n" + "=" * 60)
    log("Deploying via QEMU Guest Agent")
    log("=" * 60)
    
    commands = [
        # Step 1: Pull latest code
        ("Pulling latest code", "cd /opt/mycosoft/website && git pull origin main 2>&1"),
        
        # Step 2: Build website container
        ("Building website container", "cd /opt/mycosoft/website && docker compose -f docker-compose.always-on.yml build mycosoft-website 2>&1"),
        
        # Step 3: Restart website
        ("Restarting website container", "cd /opt/mycosoft/website && docker compose -f docker-compose.always-on.yml up -d mycosoft-website 2>&1"),
        
        # Step 4: Check PostGIS
        ("Checking PostGIS", "docker exec mindex-postgres psql -U mindex -c 'SELECT PostGIS_version();' 2>&1 || echo 'PostGIS check skipped'"),
        
        # Step 5: Restart MINDEX API
        ("Restarting MINDEX API", "cd /opt/mycosoft/website && docker compose -f docker-compose.always-on.yml restart mindex-api 2>&1 || true"),
        
        # Step 6: Restart Cloudflare tunnel
        ("Restarting Cloudflare tunnel", "systemctl restart cloudflared 2>&1"),
        
        # Step 7: Verify containers
        ("Verifying containers", "docker ps --format 'table {{.Names}}\\t{{.Status}}' 2>&1 | head -15"),
    ]
    
    results = []
    for i, (desc, cmd) in enumerate(commands, 1):
        log(f"\n[Step {i}/{len(commands)}] {desc}")
        exit_code = exec_via_agent(cmd, timeout=300)
        results.append((desc, exit_code))
        if exit_code is None:
            log(f"  Skipping remaining steps - agent not available", "WARN")
            return False
    
    # Summary
    log("\n" + "=" * 60)
    log("Deployment Summary")
    log("=" * 60)
    for desc, code in results:
        status = "OK" if code == 0 else ("SKIP" if code is None else "FAIL")
        log(f"  [{status}] {desc}")
    
    return all(code == 0 or code is None for _, code in results)

def main():
    print("=" * 70)
    print("  MYCOSOFT SANDBOX DEPLOYMENT")
    print("  Target: VM 103 (mycosoft-sandbox) - sandbox.mycosoft.com")
    print("=" * 70)
    print()
    print("  Based on documentation:")
    print("    - docs/VM103_DEPLOYMENT_COMPLETE.md")
    print("    - docs/MYCOSOFT_STACK_DEPLOYMENT.md")
    print("    - docs/SESSION_VM_CREATION_JAN17_2026.md")
    print()
    
    # Check VM is running
    if not check_vm_status():
        log("VM 103 is not running. Please start it in Proxmox.", "ERROR")
        return 1
    
    # Check if QEMU Guest Agent is available
    agent_available = check_agent_available()
    
    if agent_available:
        # Deploy via QEMU Guest Agent
        success = deploy_via_agent()
    else:
        log("QEMU Guest Agent not available. Using SSH fallback...", "WARN")
        log(f"Please run these commands manually via SSH:", "INFO")
        log(f"  ssh {VM_USER}@{VM_IP}", "INFO")
        log(f"  Password: {VM_PASSWORD}", "INFO")
        log(f"", "INFO")
        log(f"  cd /opt/mycosoft/website", "INFO")
        log(f"  git pull origin main", "INFO")
        log(f"  docker compose -f docker-compose.always-on.yml build mycosoft-website --no-cache", "INFO")
        log(f"  docker compose -f docker-compose.always-on.yml up -d mycosoft-website", "INFO")
        log(f"  sudo systemctl restart cloudflared", "INFO")
        success = False
    
    print()
    print("=" * 70)
    if success:
        print("  DEPLOYMENT SUCCESSFUL!")
    else:
        print("  DEPLOYMENT REQUIRES MANUAL STEPS")
    print("=" * 70)
    print()
    print("Test URLs:")
    print("  - https://sandbox.mycosoft.com")
    print("  - https://sandbox.mycosoft.com/admin")
    print("  - https://sandbox.mycosoft.com/natureos")
    print("  - https://sandbox.mycosoft.com/natureos/devices")
    print()
    print("Cloudflare Cache:")
    print("  Clear at: https://dash.cloudflare.com → mycosoft.com → Caching → Purge")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
