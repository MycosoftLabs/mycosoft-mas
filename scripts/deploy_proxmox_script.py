#!/usr/bin/env python3
"""
Deploy to sandbox via Proxmox API using file-write + exec approach
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

def exec_simple(cmd):
    """Execute a simple command (no args)"""
    resp = requests.post(f"{base_url}/exec", headers=headers, 
                        data={"command": cmd}, verify=False, timeout=30)
    if resp.ok:
        return resp.json().get("data", {}).get("pid")
    print(f"Exec error: {resp.status_code}")
    return None

def wait_for_pid(pid, timeout=600):
    """Wait for command to complete and return output"""
    start = time.time()
    while time.time() - start < timeout:
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
        time.sleep(3)
    return None

def file_write(path, content):
    """Write content to a file on the VM"""
    # Open file
    resp = requests.post(f"{base_url}/file-open", headers=headers,
                        data={"path": path, "mode": "w"}, verify=False)
    if not resp.ok:
        print(f"file-open error: {resp.text[:200]}")
        return False
    
    handle = resp.json().get("data")
    if not handle:
        print("No file handle returned")
        return False
    
    # Write content (base64 encoded)
    encoded = base64.b64encode(content.encode()).decode()
    resp = requests.post(f"{base_url}/file-write", headers=headers,
                        data={"handle": handle, "buf-b64": encoded}, verify=False)
    if not resp.ok:
        print(f"file-write error: {resp.text[:200]}")
    
    # Close file
    requests.post(f"{base_url}/file-close", headers=headers,
                 data={"handle": handle}, verify=False)
    
    return resp.ok

def main():
    print("=" * 60)
    print("  DEPLOYING VIA PROXMOX FILE + EXEC")
    print("=" * 60)
    
    # Write deployment script to VM
    deploy_script = """#!/bin/bash
set -e
echo "=== Starting deployment ==="

cd /opt/mycosoft/website
echo "[1] Pulling latest code..."
git fetch origin
git reset --hard origin/main
echo "Git pull complete"

echo "[2] Building Docker image..."
docker build -t website-website:latest --no-cache . 2>&1 | tail -20

echo "[3] Stopping old container..."
docker stop mycosoft-website 2>/dev/null || true
docker rm mycosoft-website 2>/dev/null || true

echo "[4] Starting new container..."
cd /opt/mycosoft
docker compose -p mycosoft-production up -d mycosoft-website

echo "[5] Waiting for startup..."
sleep 15

echo "[6] Container status:"
docker ps --filter name=mycosoft-website --format "table {{.Names}}\t{{.Status}}"

echo "=== Deployment complete ==="
"""
    
    print("\n[1] Writing deploy script to VM...")
    if not file_write("/tmp/deploy_website.sh", deploy_script):
        print("Failed to write script")
        return
    print("  Script written to /tmp/deploy_website.sh")
    
    # Make executable
    print("\n[2] Making script executable...")
    pid = exec_simple("/bin/chmod")
    if not pid:
        # chmod needs args, try alternative
        chmod_script = "#!/bin/bash\nchmod +x /tmp/deploy_website.sh"
        file_write("/tmp/chmod.sh", chmod_script)
    
    # Actually, let's just run bash with the script as input
    print("\n[3] Running deployment (this may take 5-10 minutes)...")
    
    # Write a wrapper that runs bash
    wrapper = "#!/bin/bash\nbash /tmp/deploy_website.sh 2>&1"
    file_write("/tmp/run_deploy.sh", wrapper)
    
    # Execute using bash
    pid = exec_simple("/bin/bash")
    if not pid:
        print("Could not start bash")
        # Try alternative: use input-data
        return
    
    print(f"  Started with PID: {pid}")
    print("  Waiting for completion...")
    
    result = wait_for_pid(pid, timeout=900)
    if result:
        print(f"\n  Exit code: {result['exitcode']}")
        if result['stdout']:
            print(f"\n  Output:\n{result['stdout']}")
        if result['stderr']:
            print(f"\n  Errors:\n{result['stderr']}")
    else:
        print("  Timeout or error")
    
    print("\n" + "=" * 60)
    print("Test: https://sandbox.mycosoft.com")
    print("=" * 60)

if __name__ == "__main__":
    main()
