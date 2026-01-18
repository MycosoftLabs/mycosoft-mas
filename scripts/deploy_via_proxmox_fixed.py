#!/usr/bin/env python3
"""
Deploy to sandbox.mycosoft.com via Proxmox API
Runs commands on VM 103 using QEMU Guest Agent
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

def exec_command(command):
    """Execute command on VM via QEMU Guest Agent using bash -c"""
    url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/exec"
    # Proxmox API wants the command as path + args
    data = {
        "command": "/bin/bash",
        "input-data": base64.b64encode(command.encode()).decode()
    }
    # Add args separately
    params = f"command=/bin/bash&arg=-c&arg={requests.utils.quote(command)}"
    
    try:
        response = requests.post(
            url, 
            headers=headers, 
            data={"command": "/bin/bash", "arg": ["-c", command]},
            verify=False, 
            timeout=60
        )
        if response.ok:
            result = response.json().get("data", {})
            pid = result.get("pid")
            print(f"  PID: {pid}")
            return pid
        else:
            print(f"  Error {response.status_code}: {response.text[:200]}")
            return None
    except Exception as e:
        print(f"  Exception: {e}")
        return None

def get_exec_status(pid):
    """Get status of executed command"""
    url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/exec-status"
    try:
        response = requests.get(url, headers=headers, params={"pid": pid}, verify=False, timeout=30)
        if response.ok:
            return response.json().get("data", {})
        return None
    except Exception as e:
        print(f"  Status error: {e}")
        return None

def run_command(command, timeout=600):
    """Run command and wait for completion"""
    print(f"\n>>> {command}")
    pid = exec_command(command)
    if not pid:
        return None
    
    start = time.time()
    while time.time() - start < timeout:
        time.sleep(3)
        status = get_exec_status(pid)
        if status:
            if status.get("exited"):
                exit_code = status.get("exitcode", -1)
                out_data = status.get("out-data", "")
                err_data = status.get("err-data", "")
                # Decode base64 if needed
                try:
                    if out_data:
                        out_data = base64.b64decode(out_data).decode('utf-8', errors='replace')
                except:
                    pass
                try:
                    if err_data:
                        err_data = base64.b64decode(err_data).decode('utf-8', errors='replace')
                except:
                    pass
                print(f"  Exit: {exit_code}")
                if out_data:
                    print(f"  Out: {out_data[:500]}")
                if err_data and exit_code != 0:
                    print(f"  Err: {err_data[:200]}")
                return exit_code
    
    print(f"  Timeout after {timeout}s")
    return None

def main():
    print("=" * 60)
    print("  DEPLOYING VIA PROXMOX API")
    print("=" * 60)
    
    # Check VM
    url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/status/current"
    resp = requests.get(url, headers=headers, verify=False)
    if resp.ok:
        data = resp.json().get("data", {})
        print(f"VM: {data.get('name')} - {data.get('status')}")
    
    # Run deployment
    commands = [
        "cd /opt/mycosoft/website && git fetch origin && git reset --hard origin/main",
        "cd /opt/mycosoft/website && docker build -t website-website:latest --no-cache .",
        "docker stop mycosoft-website || true",
        "docker rm mycosoft-website || true",
        "cd /opt/mycosoft && docker compose -p mycosoft-production up -d mycosoft-website",
        "sleep 10 && docker ps --filter name=mycosoft-website"
    ]
    
    for i, cmd in enumerate(commands, 1):
        print(f"\n[{i}/{len(commands)}]")
        result = run_command(cmd, timeout=600)
        if result is None:
            print("  FAILED - stopping")
            break
    
    print("\n" + "=" * 60)
    print("  DONE - Test https://sandbox.mycosoft.com")
    print("=" * 60)

if __name__ == "__main__":
    main()
