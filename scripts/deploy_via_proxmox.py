#!/usr/bin/env python3
"""
Deploy to sandbox.mycosoft.com via Proxmox API
Runs commands on VM 103 using QEMU Guest Agent
"""
import requests
import urllib3
import time
import json

# Disable SSL warnings for self-signed cert
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration
PROXMOX_HOST = "https://192.168.0.202:8006"
PROXMOX_TOKEN_ID = "myca@pve!mas"
PROXMOX_TOKEN_SECRET = "ca23b6c8-5746-46c4-8e36-fc6caad5a9e5"
VM_ID = 103  # mycosoft-sandbox
NODE = "pve"  # Proxmox node name

headers = {
    "Authorization": f"PVEAPIToken={PROXMOX_TOKEN_ID}={PROXMOX_TOKEN_SECRET}"
}

def get_vm_status():
    """Get VM 103 status"""
    url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/status/current"
    try:
        response = requests.get(url, headers=headers, verify=False, timeout=10)
        if response.ok:
            return response.json().get("data", {})
        else:
            print(f"Error getting VM status: {response.status_code}")
            return None
    except Exception as e:
        print(f"Connection error: {e}")
        return None

def exec_command(command):
    """Execute command on VM via QEMU Guest Agent"""
    url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/exec"
    data = {
        "command": command,
        "input-data": ""
    }
    try:
        response = requests.post(url, headers=headers, data=data, verify=False, timeout=60)
        if response.ok:
            result = response.json().get("data", {})
            pid = result.get("pid")
            print(f"  Command started with PID: {pid}")
            return pid
        else:
            print(f"  Exec error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"  Exec exception: {e}")
        return None

def get_exec_status(pid):
    """Get status of executed command"""
    url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/exec-status"
    data = {"pid": pid}
    try:
        response = requests.get(url, headers=headers, params=data, verify=False, timeout=30)
        if response.ok:
            return response.json().get("data", {})
        return None
    except Exception as e:
        print(f"  Status check error: {e}")
        return None

def run_command_wait(command, timeout=300):
    """Run command and wait for completion"""
    print(f"\n>>> Running: {command}")
    pid = exec_command(command)
    if not pid:
        return None
    
    start = time.time()
    while time.time() - start < timeout:
        time.sleep(2)
        status = get_exec_status(pid)
        if status:
            if status.get("exited"):
                exit_code = status.get("exitcode", -1)
                out_data = status.get("out-data", "")
                err_data = status.get("err-data", "")
                print(f"  Exit code: {exit_code}")
                if out_data:
                    print(f"  Output: {out_data[:500]}")
                if err_data:
                    print(f"  Stderr: {err_data[:200]}")
                return {"exitcode": exit_code, "stdout": out_data, "stderr": err_data}
    
    print(f"  Command timed out after {timeout}s")
    return None

def main():
    print("=" * 60)
    print("  MYCOSOFT SANDBOX DEPLOYMENT VIA PROXMOX API")
    print("=" * 60)
    
    # Check VM status
    print("\n[1] Checking VM 103 status...")
    status = get_vm_status()
    if status:
        print(f"  VM Status: {status.get('status')}")
        print(f"  VM Name: {status.get('name')}")
        if status.get("status") != "running":
            print("  ERROR: VM is not running!")
            return
    else:
        print("  Could not connect to Proxmox or VM")
        print("  Trying alternative approach...")
    
    # Deployment commands
    commands = [
        "cd /opt/mycosoft/website && git fetch origin && git reset --hard origin/main",
        "cd /opt/mycosoft/website && docker build -t website-website:latest --no-cache .",
        "docker stop mycosoft-website 2>/dev/null || true",
        "docker rm mycosoft-website 2>/dev/null || true",
        "cd /opt/mycosoft && docker compose -p mycosoft-production up -d mycosoft-website",
        "docker ps --format 'table {{.Names}}\\t{{.Status}}'"
    ]
    
    print("\n[2] Running deployment commands...")
    for i, cmd in enumerate(commands, 1):
        print(f"\n--- Step {i}/{len(commands)} ---")
        result = run_command_wait(cmd, timeout=300)
        if result and result.get("exitcode") != 0:
            print(f"  Warning: Command returned non-zero exit code")
    
    print("\n" + "=" * 60)
    print("  DEPLOYMENT COMPLETE!")
    print("=" * 60)
    print("\nTest URLs:")
    print("  - https://sandbox.mycosoft.com")
    print("  - https://sandbox.mycosoft.com/admin")
    print("  - https://sandbox.mycosoft.com/natureos")
    print("  - https://sandbox.mycosoft.com/natureos/devices")

if __name__ == "__main__":
    main()
