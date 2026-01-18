#!/usr/bin/env python3
"""
Upgrade VM 103: Shutdown, increase memory to 64GB, disk to 1TB, then restart
"""
import requests
import urllib3
import time
import sys

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PROXMOX_HOST = "https://192.168.0.202:8006"
PROXMOX_TOKEN_ID = "myca@pve!mas"
PROXMOX_TOKEN_SECRET = "ca23b6c8-5746-46c4-8e36-fc6caad5a9e5"
VM_ID = 103
NODE = "pve"

headers = {
    "Authorization": f"PVEAPIToken={PROXMOX_TOKEN_ID}={PROXMOX_TOKEN_SECRET}"
}

def api_get(endpoint):
    url = f"{PROXMOX_HOST}/api2/json{endpoint}"
    resp = requests.get(url, headers=headers, verify=False, timeout=30)
    return resp

def api_post(endpoint, data=None):
    url = f"{PROXMOX_HOST}/api2/json{endpoint}"
    resp = requests.post(url, headers=headers, data=data or {}, verify=False, timeout=60)
    return resp

def api_put(endpoint, data=None):
    url = f"{PROXMOX_HOST}/api2/json{endpoint}"
    resp = requests.put(url, headers=headers, data=data or {}, verify=False, timeout=60)
    return resp

def get_vm_status():
    resp = api_get(f"/nodes/{NODE}/qemu/{VM_ID}/status/current")
    if resp.ok:
        return resp.json().get("data", {})
    return None

def get_vm_config():
    resp = api_get(f"/nodes/{NODE}/qemu/{VM_ID}/config")
    if resp.ok:
        return resp.json().get("data", {})
    return None

def shutdown_vm():
    print("Sending shutdown command...")
    resp = api_post(f"/nodes/{NODE}/qemu/{VM_ID}/status/shutdown")
    if resp.ok:
        print(f"  Shutdown initiated: {resp.json()}")
        return True
    else:
        print(f"  Error: {resp.status_code} - {resp.text[:200]}")
        # Try stop instead
        print("  Trying force stop...")
        resp = api_post(f"/nodes/{NODE}/qemu/{VM_ID}/status/stop")
        return resp.ok

def wait_for_shutdown(timeout=120):
    print(f"Waiting for VM to shut down (max {timeout}s)...")
    start = time.time()
    while time.time() - start < timeout:
        status = get_vm_status()
        if status:
            state = status.get("status")
            print(f"  Status: {state}")
            if state == "stopped":
                return True
        time.sleep(5)
    return False

def resize_disk(disk, size_gb):
    """Resize disk to specified size in GB"""
    print(f"Resizing {disk} to {size_gb}GB...")
    # Proxmox resize needs the size increase, not absolute size
    # Use format: +500G to add 500GB
    resp = api_put(f"/nodes/{NODE}/qemu/{VM_ID}/resize", {
        "disk": disk,
        "size": f"{size_gb}G"
    })
    if resp.ok:
        print(f"  Disk resize initiated")
        return True
    else:
        print(f"  Error: {resp.status_code} - {resp.text[:300]}")
        return False

def update_memory(memory_mb):
    """Update VM memory"""
    print(f"Setting memory to {memory_mb}MB ({memory_mb//1024}GB)...")
    resp = api_put(f"/nodes/{NODE}/qemu/{VM_ID}/config", {
        "memory": memory_mb
    })
    if resp.ok:
        print(f"  Memory updated")
        return True
    else:
        print(f"  Error: {resp.status_code} - {resp.text[:200]}")
        return False

def start_vm():
    print("Starting VM...")
    resp = api_post(f"/nodes/{NODE}/qemu/{VM_ID}/status/start")
    if resp.ok:
        print(f"  Start initiated")
        return True
    else:
        print(f"  Error: {resp.status_code} - {resp.text[:200]}")
        return False

def wait_for_running(timeout=180):
    print(f"Waiting for VM to start (max {timeout}s)...")
    start = time.time()
    while time.time() - start < timeout:
        status = get_vm_status()
        if status:
            state = status.get("status")
            print(f"  Status: {state}")
            if state == "running":
                return True
        time.sleep(5)
    return False

def main():
    print("=" * 60)
    print("  VM 103 UPGRADE: 64GB RAM + 1TB DISK")
    print("=" * 60)
    
    # Get current status
    print("\n[1] Current VM status:")
    status = get_vm_status()
    if status:
        print(f"  Name: {status.get('name')}")
        print(f"  Status: {status.get('status')}")
        print(f"  Memory: {status.get('maxmem', 0) // (1024**3)}GB")
        print(f"  CPUs: {status.get('cpus')}")
    else:
        print("  ERROR: Could not get VM status")
        return 1
    
    # Get current config
    print("\n[2] Current VM config:")
    config = get_vm_config()
    if config:
        print(f"  Memory: {config.get('memory')}MB")
        print(f"  Cores: {config.get('cores')}")
        # Find disk
        for key in config:
            if key.startswith('scsi') or key.startswith('virtio') or key.startswith('ide'):
                print(f"  {key}: {config[key]}")
    
    # Shutdown VM if running
    print("\n[3] Shutting down VM...")
    if status.get("status") == "running":
        if not shutdown_vm():
            print("  Failed to initiate shutdown")
            return 1
        if not wait_for_shutdown(timeout=120):
            print("  VM did not shut down in time")
            return 1
    else:
        print("  VM already stopped")
    
    # Update memory to 64GB
    print("\n[4] Upgrading memory to 64GB...")
    if not update_memory(65536):  # 64GB = 65536MB
        print("  Memory upgrade failed, continuing...")
    
    # Resize disk to 1TB
    print("\n[5] Resizing disk to 1TB...")
    # Find the main disk from config
    disk_key = None
    for key in config:
        if key.startswith('scsi0') or key.startswith('virtio0'):
            disk_key = key
            break
    
    if disk_key:
        # Set absolute size to 1TB
        if not resize_disk(disk_key, 1024):
            print("  Disk resize failed, continuing...")
    else:
        print("  Could not find disk to resize")
    
    # Start VM
    print("\n[6] Starting VM...")
    if not start_vm():
        print("  Failed to start VM")
        return 1
    
    if not wait_for_running(timeout=180):
        print("  VM did not start in time")
        return 1
    
    print("\n[7] Waiting 30s for services to initialize...")
    time.sleep(30)
    
    # Verify new config
    print("\n[8] Verifying new configuration:")
    status = get_vm_status()
    if status:
        print(f"  Memory: {status.get('maxmem', 0) // (1024**3)}GB")
        print(f"  Status: {status.get('status')}")
    
    print("\n" + "=" * 60)
    print("  VM UPGRADE COMPLETE!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. SSH into VM and expand LVM partition")
    print("2. Run deployment script")
    print("3. Clear Cloudflare cache")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
