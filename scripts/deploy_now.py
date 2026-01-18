#!/usr/bin/env python3
"""
Deploy to sandbox.mycosoft.com NOW
Uses Proxmox QEMU Guest Agent
"""
import requests
import urllib3
import time
import sys

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PROXMOX_HOST = "https://192.168.0.202:8006"
TOKEN_ID = "myca@pve!mas"
TOKEN_SECRET = "ca23b6c8-5746-46c4-8e36-fc6caad5a9e5"
headers = {"Authorization": f"PVEAPIToken={TOKEN_ID}={TOKEN_SECRET}"}

def exec_cmd(cmd, timeout=300):
    """Execute command via QEMU guest agent"""
    print(f">>> {cmd[:70]}{'...' if len(cmd) > 70 else ''}")
    url = f"{PROXMOX_HOST}/api2/json/nodes/pve/qemu/103/agent/exec"
    r = requests.post(url, headers=headers, data={"command": cmd}, verify=False, timeout=30)
    if r.status_code != 200:
        print(f"    FAILED: {r.status_code}")
        return None
    pid = r.json().get("data", {}).get("pid")
    
    start = time.time()
    while time.time() - start < timeout:
        time.sleep(3)
        url2 = f"{PROXMOX_HOST}/api2/json/nodes/pve/qemu/103/agent/exec-status"
        r2 = requests.get(url2, headers=headers, params={"pid": pid}, verify=False, timeout=30)
        if r2.status_code == 200:
            data = r2.json().get("data", {})
            if data.get("exited"):
                code = data.get("exitcode", -1)
                out = data.get("out-data", "")
                err = data.get("err-data", "")
                status = "OK" if code == 0 else f"EXIT {code}"
                print(f"    [{status}] {out[:150] if out else ''}")
                if err and code != 0:
                    print(f"    ERROR: {err[:100]}")
                return code
    print(f"    TIMEOUT after {timeout}s")
    return -1

def main():
    print("=" * 60)
    print("  MYCOSOFT SANDBOX DEPLOYMENT")
    print("  Target: sandbox.mycosoft.com (VM 103)")
    print("=" * 60)
    print()
    
    # Step 1: Fix SSH permissions
    print("[1/7] Fixing SSH key permissions...")
    exec_cmd("/bin/chmod 700 /home/mycosoft/.ssh")
    exec_cmd("/bin/chmod 600 /home/mycosoft/.ssh/authorized_keys")
    exec_cmd("/bin/chown -R mycosoft:mycosoft /home/mycosoft/.ssh")
    
    # Step 2: Pull latest code
    print("\n[2/7] Pulling latest code from GitHub...")
    exec_cmd('/bin/bash -c "cd /opt/mycosoft/website && git pull origin main"', 60)
    
    # Step 3: Build website container
    print("\n[3/7] Building website container (this may take a few minutes)...")
    exec_cmd('/bin/bash -c "cd /opt/mycosoft/website && docker compose -f docker-compose.always-on.yml build mycosoft-website"', 600)
    
    # Step 4: Restart website container
    print("\n[4/7] Restarting website container...")
    exec_cmd('/bin/bash -c "cd /opt/mycosoft/website && docker compose -f docker-compose.always-on.yml up -d mycosoft-website"', 120)
    
    # Step 5: Check/Enable PostGIS
    print("\n[5/7] Checking PostGIS extension...")
    exec_cmd('/bin/bash -c "docker exec mindex-postgres psql -U mindex -c \'CREATE EXTENSION IF NOT EXISTS postgis;\' 2>/dev/null || echo skipped"', 30)
    
    # Step 6: Restart MINDEX API
    print("\n[6/7] Restarting MINDEX API...")
    exec_cmd('/bin/bash -c "cd /opt/mycosoft/website && docker compose -f docker-compose.always-on.yml restart mindex-api || true"', 60)
    
    # Step 7: Restart Cloudflare tunnel
    print("\n[7/7] Restarting Cloudflare tunnel...")
    exec_cmd("/bin/systemctl restart cloudflared")
    
    # Verify
    print("\n[VERIFY] Checking container status...")
    exec_cmd('/bin/bash -c "docker ps --format \'{{.Names}} {{.Status}}\' | head -10"')
    
    print()
    print("=" * 60)
    print("  DEPLOYMENT COMPLETE!")
    print("=" * 60)
    print()
    print("Test URLs:")
    print("  - https://sandbox.mycosoft.com")
    print("  - https://sandbox.mycosoft.com/admin")
    print("  - https://sandbox.mycosoft.com/natureos")
    print("  - https://sandbox.mycosoft.com/natureos/devices")
    print()
    print("Cloudflare Cache: Clear at dash.cloudflare.com")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
