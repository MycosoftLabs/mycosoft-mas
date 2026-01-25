#!/usr/bin/env python3
"""
Setup Device Media Folders on VM
=================================
Creates the folder structure for all device media assets on the VM.
These folders will be served via the NAS mount.

Folder structure:
  /opt/mycosoft/media/website/assets/
    ├── mushroom1/   (already exists)
    ├── sporebase/
    ├── hyphae1/
    ├── myconode/
    └── alarm/
"""

import requests
import urllib3
import time
import base64
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
urllib3.disable_warnings()

# Proxmox configuration
PROXMOX_HOST = "https://192.168.0.202:8006"
PROXMOX_TOKEN_ID = "myca@pve!mas"
PROXMOX_TOKEN_SECRET = "ca23b6c8-5746-46c4-8e36-fc6caad5a9e5"
VM_ID = 103
NODE = "pve"

# Device folders to create
DEVICES = ["mushroom1", "sporebase", "hyphae1", "myconode", "alarm"]
BASE_PATH = "/opt/mycosoft/media/website/assets"

headers = {"Authorization": f"PVEAPIToken={PROXMOX_TOKEN_ID}={PROXMOX_TOKEN_SECRET}"}


def exec_cmd(cmd: str, timeout: int = 60):
    """Execute command on VM via Proxmox QEMU Guest Agent."""
    url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/exec"
    try:
        data = {"command": "/bin/bash", "input-data": cmd}
        r = requests.post(url, headers=headers, data=data, verify=False, timeout=15)
        if not r.ok:
            return None, f"Exec failed: {r.status_code}"
        pid = r.json().get("data", {}).get("pid")
        if not pid:
            return None, "PID not returned"

        start_time = time.time()
        while True:
            status_url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/exec-status?pid={pid}"
            status_r = requests.get(status_url, headers=headers, verify=False, timeout=10)
            if not status_r.ok:
                return None, f"Status check failed: {status_r.status_code}"

            status_data = status_r.json().get("data", {})
            if status_data.get("exited"):
                out_data = status_data.get("out-data", "")
                err_data = status_data.get("err-data", "")
                
                # Handle base64 decoding with padding fix
                def safe_b64decode(data):
                    if not data:
                        return ""
                    try:
                        # Add padding if needed
                        padding = 4 - len(data) % 4
                        if padding != 4:
                            data += "=" * padding
                        return base64.b64decode(data).decode('utf-8', errors='replace')
                    except Exception:
                        # Return raw if not base64
                        return data
                
                stdout = safe_b64decode(out_data)
                stderr = safe_b64decode(err_data)
                return stdout.strip(), stderr.strip()

            if time.time() - start_time > timeout:
                return None, "Command timed out"
            time.sleep(1)
    except requests.exceptions.RequestException as e:
        return None, f"Network error: {e}"


def main():
    print("=" * 60)
    print(" SETUP DEVICE MEDIA FOLDERS ON VM")
    print("=" * 60)
    print()

    # Check VM connectivity
    print("[1] Testing VM connectivity...")
    stdout, stderr = exec_cmd("hostname")
    if stderr:
        print(f"    ERROR: Cannot connect to VM: {stderr}")
        return 1
    print(f"    Connected to: {stdout}")
    print()

    # Create base directory if needed
    print(f"[2] Ensuring base path exists: {BASE_PATH}")
    stdout, stderr = exec_cmd(f"mkdir -p {BASE_PATH}")
    if stderr:
        print(f"    ERROR: {stderr}")
    else:
        print("    OK")
    print()

    # Create device folders
    print("[3] Creating device folders...")
    for device in DEVICES:
        device_path = f"{BASE_PATH}/{device}"
        stdout, stderr = exec_cmd(f"mkdir -p {device_path}")
        if stderr:
            print(f"    ERROR creating {device}: {stderr}")
        else:
            # Verify
            stdout, stderr = exec_cmd(f"test -d {device_path} && echo EXISTS || echo MISSING")
            if "EXISTS" in (stdout or ""):
                print(f"    [OK]     {device_path}")
            else:
                print(f"    [WARN]   {device_path} - may not exist")
    print()

    # List current contents
    print("[4] Current folder structure:")
    stdout, stderr = exec_cmd(f"ls -la {BASE_PATH}/")
    if stdout:
        for line in stdout.split("\n"):
            print(f"    {line}")
    print()

    # Check NAS mount status
    print("[5] Checking NAS mount status...")
    stdout, stderr = exec_cmd("mount | grep -i mycosoft-nas || echo 'No NAS mount found'")
    if stdout:
        for line in stdout.split("\n"):
            print(f"    {line}")
    print()

    # Summary
    print("=" * 60)
    print(" SETUP COMPLETE")
    print("=" * 60)
    print()
    print("Device asset folders are ready at:")
    for device in DEVICES:
        print(f"  - {BASE_PATH}/{device}/")
    print()
    print("Next steps:")
    print("  1. Add media files to local: website/public/assets/{device}/")
    print("  2. Run: python scripts/media/sync_website_media_paramiko.py")
    print("  3. Restart container if needed: docker restart mycosoft-website")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
