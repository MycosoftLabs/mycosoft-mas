#!/usr/bin/env python3
"""
MAS VM Provisioning Script - Automated
Creates VM 188 for the MAS v2 Agent Runtime System using verified Proxmox credentials.
"""
import requests
import urllib3
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Verified working credentials from docs/PROXMOX_UNIFI_API_REFERENCE.md
PROXMOX_HOST = "192.168.0.202"
PROXMOX_TOKEN = "root@pam!cursor_agent=bc1c9dc7-6fca-4e89-8a1d-557a9d117a3e"
NODE = "pve"

# MAS VM Configuration
MAS_VM_CONFIG = {
    "vmid": 188,
    "name": "mycosoft-mas",
    "memory": 65536,  # 64 GB
    "cores": 16,
    "sockets": 1,
    "cpu": "host",
    "ostype": "l26",
    "scsihw": "virtio-scsi-single",
    "scsi0": "local-lvm:500,discard=on,iothread=1,ssd=1",
    "net0": "virtio,bridge=vmbr0,firewall=1",
    "boot": "order=scsi0;net0",
    "agent": 1,
    "description": "MAS v2 Agent Runtime System - 40 agents containerized",
}

headers = {
    "Authorization": f"PVEAPIToken={PROXMOX_TOKEN}",
}

def log(msg, level="INFO"):
    ts = time.strftime("%H:%M:%S")
    symbols = {"INFO": "[i]", "OK": "[+]", "WARN": "[!]", "ERR": "[X]", "RUN": "[>]"}
    print(f"[{ts}] {symbols.get(level, '*')} {msg}")

def check_connection():
    """Verify Proxmox API connection"""
    url = f"https://{PROXMOX_HOST}:8006/api2/json/nodes"
    try:
        r = requests.get(url, headers=headers, verify=False, timeout=10)
        if r.ok:
            nodes = r.json().get("data", [])
            return True, [n["node"] for n in nodes]
        return False, f"HTTP {r.status_code}"
    except Exception as e:
        return False, str(e)

def list_vms():
    """List all VMs"""
    url = f"https://{PROXMOX_HOST}:8006/api2/json/nodes/{NODE}/qemu"
    try:
        r = requests.get(url, headers=headers, verify=False, timeout=10)
        if r.ok:
            return r.json().get("data", [])
        return []
    except:
        return []

def get_isos():
    """List available ISOs"""
    url = f"https://{PROXMOX_HOST}:8006/api2/json/nodes/{NODE}/storage/local/content"
    try:
        r = requests.get(url, headers=headers, verify=False, timeout=10)
        if r.ok:
            content = r.json().get("data", [])
            return [c for c in content if c.get("content") == "iso"]
        return []
    except:
        return []

def create_vm(config):
    """Create VM with given configuration"""
    url = f"https://{PROXMOX_HOST}:8006/api2/json/nodes/{NODE}/qemu"
    try:
        r = requests.post(url, headers=headers, data=config, verify=False, timeout=30)
        if r.ok:
            return True, r.json().get("data", "")
        return False, f"HTTP {r.status_code}: {r.text}"
    except Exception as e:
        return False, str(e)

def clone_vm(source_vmid, new_vmid, new_name):
    """Clone an existing VM"""
    url = f"https://{PROXMOX_HOST}:8006/api2/json/nodes/{NODE}/qemu/{source_vmid}/clone"
    data = {
        "newid": new_vmid,
        "name": new_name,
        "full": 1,
        "target": NODE,
    }
    try:
        r = requests.post(url, headers=headers, data=data, verify=False, timeout=30)
        if r.ok:
            return True, r.json().get("data", "")
        return False, f"HTTP {r.status_code}: {r.text}"
    except Exception as e:
        return False, str(e)

def main():
    print("=" * 60)
    print("MAS VM PROVISIONING")
    print("=" * 60)
    
    # Step 1: Check connection
    log("Connecting to Proxmox API...", "RUN")
    ok, nodes = check_connection()
    if not ok:
        log(f"Failed to connect: {nodes}", "ERR")
        return False
    log(f"Connected. Nodes: {nodes}", "OK")
    
    # Step 2: List existing VMs
    log("Checking existing VMs...", "RUN")
    vms = list_vms()
    print("\n    Existing VMs:")
    for vm in vms:
        print(f"    - VM {vm['vmid']}: {vm['name']} ({vm.get('status', 'unknown')})")
    
    # Check if VM 188 already exists
    existing = [v for v in vms if v["vmid"] == 188]
    if existing:
        log(f"VM 188 already exists: {existing[0]['name']}", "WARN")
        print("\n    The MAS VM is already provisioned!")
        print("    To access: https://192.168.0.202:8006/#v1:0:=qemu/188:")
        return True
    
    # Step 3: Check for Ubuntu template
    log("Checking for templates or ISOs...", "RUN")
    
    # Check for ubuntu template VM (usually ID 101 or similar)
    templates = [v for v in vms if "template" in v["name"].lower() or "ubuntu" in v["name"].lower()]
    if templates:
        print(f"\n    Found potential template: {templates[0]['name']} (VM {templates[0]['vmid']})")
    
    isos = get_isos()
    if isos:
        print("\n    Available ISOs:")
        for iso in isos[:5]:
            print(f"    - {iso.get('volid', 'unknown')}")
    
    # Step 4: Create VM
    log("Creating MAS VM (ID: 188)...", "RUN")
    print(f"\n    Configuration:")
    print(f"    - Name: {MAS_VM_CONFIG['name']}")
    print(f"    - Memory: {MAS_VM_CONFIG['memory']} MB ({MAS_VM_CONFIG['memory'] // 1024} GB)")
    print(f"    - Cores: {MAS_VM_CONFIG['cores']}")
    print(f"    - Disk: 500 GB on local-lvm")
    print()
    
    success, result = create_vm(MAS_VM_CONFIG)
    
    if success:
        log(f"VM creation started: {result}", "OK")
    else:
        log(f"VM creation failed: {result}", "ERR")
        
        # Try cloning if creation fails
        ubuntu_template = next((v for v in vms if v.get("vmid") == 101), None)
        if ubuntu_template:
            log("Trying to clone from ubuntu-cursor template...", "RUN")
            success, result = clone_vm(101, 188, "mycosoft-mas")
            if success:
                log(f"Clone started: {result}", "OK")
            else:
                log(f"Clone also failed: {result}", "ERR")
    
    print("\n" + "=" * 60)
    print("PROVISIONING RESULT")
    print("=" * 60)
    
    if success:
        print("\nNext Steps:")
        print("1. Access Proxmox: https://192.168.0.202:8006")
        print("2. Attach Ubuntu 22.04 Server ISO to VM 188")
        print("3. Start VM and install Ubuntu")
        print("4. Configure static IP: 192.168.0.188")
        print("5. Follow docs/MAS_VM_PROVISIONING_GUIDE.md for full setup")
    else:
        print("\nManual creation required:")
        print("1. Go to https://192.168.0.202:8006")
        print("2. Create VM 188 with: 16 cores, 64GB RAM, 500GB disk")
        print("3. Name it 'mycosoft-mas'")
        print("4. Follow docs/MAS_VM_PROVISIONING_GUIDE.md")
    
    return success

if __name__ == "__main__":
    main()
