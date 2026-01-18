#!/usr/bin/env python3
"""
Deploy to sandbox via Proxmox API using input-data for stdin
"""
import requests
import urllib3
import time
import base64

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PROXMOX_HOST = "https://192.168.0.202:8006"
PROXMOX_TOKEN_ID = "myca@pve!mas"
PROXMOX_TOKEN_SECRET = "ca23b6c8-5746-46c4-8e36-fc6caad5a9e5"
VM_ID = 103
NODE = "pve"

headers = {
    "Authorization": f"PVEAPIToken={PROXMOX_TOKEN_ID}={PROXMOX_TOKEN_SECRET}"
}

base_url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent"

def exec_with_stdin(command, stdin_data):
    """Execute command with stdin data"""
    # Encode stdin as base64
    encoded = base64.b64encode(stdin_data.encode()).decode()
    
    resp = requests.post(f"{base_url}/exec", headers=headers, 
                        data={
                            "command": command,
                            "input-data": encoded
                        }, 
                        verify=False, timeout=60)
    if resp.ok:
        return resp.json().get("data", {}).get("pid")
    print(f"Exec error {resp.status_code}: {resp.text[:300]}")
    return None

def wait_for_pid(pid, timeout=900):
    """Wait for command to complete"""
    start = time.time()
    last_check = 0
    while time.time() - start < timeout:
        if time.time() - last_check > 10:
            elapsed = int(time.time() - start)
            print(f"  ... waiting ({elapsed}s)")
            last_check = time.time()
        
        resp = requests.get(f"{base_url}/exec-status", headers=headers,
                           params={"pid": pid}, verify=False, timeout=30)
        if resp.ok:
            data = resp.json().get("data", {})
            if data.get("exited"):
                return {
                    "exitcode": data.get("exitcode", -1),
                    "stdout": data.get("out-data", ""),
                    "stderr": data.get("err-data", "")
                }
        time.sleep(5)
    return None

def main():
    print("=" * 60)
    print("  DEPLOYING VIA PROXMOX API (stdin method)")
    print("=" * 60)
    
    # Deployment script
    deploy_script = """
set -e
echo "=== Starting deployment ==="

cd /opt/mycosoft/website
echo "[1] Pulling latest code..."
git fetch origin
git reset --hard origin/main

echo "[2] Building Docker image (this takes a few minutes)..."
docker build -t website-website:latest --no-cache . 2>&1 | tail -30

echo "[3] Stopping old container..."
docker stop mycosoft-website 2>/dev/null || true
docker rm mycosoft-website 2>/dev/null || true

echo "[4] Starting new container..."
cd /opt/mycosoft
docker compose -p mycosoft-production up -d mycosoft-website

echo "[5] Waiting for startup..."
sleep 15

echo "[6] Container status:"
docker ps --filter name=mycosoft-website

echo "=== Deployment complete ==="
"""
    
    print("\nRunning deployment via /bin/bash with stdin...")
    print("This will take 5-10 minutes for Docker build.\n")
    
    pid = exec_with_stdin("/bin/bash", deploy_script)
    if not pid:
        print("Failed to start")
        return
    
    print(f"Started with PID: {pid}")
    
    result = wait_for_pid(pid, timeout=900)
    if result:
        print(f"\n{'='*40}")
        print(f"Exit code: {result['exitcode']}")
        print(f"{'='*40}")
        if result['stdout']:
            print(f"\nOutput:\n{result['stdout']}")
        if result['stderr'] and result['exitcode'] != 0:
            print(f"\nErrors:\n{result['stderr']}")
    else:
        print("Timeout waiting for completion")
    
    print("\n" + "=" * 60)
    print("Test: https://sandbox.mycosoft.com/login")
    print("=" * 60)

if __name__ == "__main__":
    main()
