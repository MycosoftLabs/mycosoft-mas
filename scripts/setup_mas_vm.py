#!/usr/bin/env python3
"""
Setup MAS VM - Attach ISO and configure for installation
"""
import requests
import urllib3
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PROXMOX_HOST = "192.168.0.202"
PROXMOX_TOKEN = "root@pam!cursor_agent=bc1c9dc7-6fca-4e89-8a1d-557a9d117a3e"
NODE = "pve"
VMID = 188

headers = {"Authorization": f"PVEAPIToken={PROXMOX_TOKEN}"}
BASE_URL = f"https://{PROXMOX_HOST}:8006/api2/json"

def log(msg, level="INFO"):
    ts = time.strftime("%H:%M:%S")
    symbols = {"INFO": "[i]", "OK": "[+]", "WARN": "[!]", "ERR": "[X]", "RUN": "[>]"}
    print(f"[{ts}] {symbols.get(level, '*')} {msg}")

def get_vm_config():
    """Get VM configuration"""
    url = f"{BASE_URL}/nodes/{NODE}/qemu/{VMID}/config"
    r = requests.get(url, headers=headers, verify=False, timeout=10)
    if r.ok:
        return r.json().get("data", {})
    return {}

def update_vm_config(config):
    """Update VM configuration"""
    url = f"{BASE_URL}/nodes/{NODE}/qemu/{VMID}/config"
    r = requests.put(url, headers=headers, data=config, verify=False, timeout=30)
    return r.ok, r.text

def start_vm():
    """Start the VM"""
    url = f"{BASE_URL}/nodes/{NODE}/qemu/{VMID}/status/start"
    r = requests.post(url, headers=headers, verify=False, timeout=30)
    return r.ok, r.json().get("data", "") if r.ok else r.text

def get_vm_status():
    """Get VM status"""
    url = f"{BASE_URL}/nodes/{NODE}/qemu/{VMID}/status/current"
    r = requests.get(url, headers=headers, verify=False, timeout=10)
    if r.ok:
        return r.json().get("data", {})
    return {}

def main():
    print("=" * 60)
    print("MAS VM SETUP")
    print("=" * 60)
    
    # Step 1: Check VM exists
    log("Checking VM 188 status...", "RUN")
    status = get_vm_status()
    if not status:
        log("VM 188 not found!", "ERR")
        return False
    log(f"VM found: {status.get('name', 'unknown')} - {status.get('status', 'unknown')}", "OK")
    
    # Step 2: Get current config
    log("Getting current configuration...", "RUN")
    config = get_vm_config()
    print(f"\n    Current config:")
    print(f"    - Memory: {config.get('memory', 'N/A')} MB")
    print(f"    - Cores: {config.get('cores', 'N/A')}")
    print(f"    - Disk: {config.get('scsi0', 'N/A')}")
    
    # Step 3: Attach Ubuntu ISO
    log("Attaching Ubuntu 24.04 ISO...", "RUN")
    iso_config = {
        "ide2": "local:iso/ubuntu-24.04.2-live-server-amd64.iso,media=cdrom",
        "boot": "order=ide2;scsi0;net0",
    }
    ok, result = update_vm_config(iso_config)
    if ok:
        log("ISO attached and boot order updated", "OK")
    else:
        log(f"Failed to attach ISO: {result}", "ERR")
    
    # Step 4: Verify updated config
    log("Verifying configuration...", "RUN")
    config = get_vm_config()
    print(f"\n    Updated config:")
    print(f"    - IDE2 (ISO): {config.get('ide2', 'Not set')}")
    print(f"    - Boot order: {config.get('boot', 'N/A')}")
    
    # Step 5: Start VM
    if status.get("status") != "running":
        log("Starting VM 188...", "RUN")
        ok, result = start_vm()
        if ok:
            log(f"VM start task: {result}", "OK")
        else:
            log(f"Failed to start VM: {result}", "WARN")
    else:
        log("VM is already running", "INFO")
    
    print("\n" + "=" * 60)
    print("MAS VM SETUP COMPLETE")
    print("=" * 60)
    print("\nNext Steps:")
    print("1. Open Proxmox console: https://192.168.0.202:8006/#v1:0:=qemu/188:=console")
    print("2. Complete Ubuntu installation:")
    print("   - Username: mycosoft")
    print("   - Password: Mushroom1!Mushroom1!")
    print("   - Hostname: mas-vm")
    print("   - Install OpenSSH server")
    print("3. After installation, configure static IP: 192.168.0.188")
    print("4. Install Docker and setup MAS stack")
    print("\nSee docs/MAS_VM_PROVISIONING_GUIDE.md for complete instructions")
    
    return True

if __name__ == "__main__":
    main()
