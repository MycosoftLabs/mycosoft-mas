#!/usr/bin/env python3
"""Check VM status and transfer Docker images"""

import paramiko
import os
import sys
from pathlib import Path
import time

# Configuration
PROXMOX_HOST = "192.168.0.202"
PROXMOX_USER = "root"
PROXMOX_PASSWORD = "20202020"
VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "Mushroom1!Mushroom1!"

EXPORT_DIR = Path(r"C:\Users\admin2\Desktop\MYCOSOFT\DOCKER_EXPORTS")


def get_proxmox_connection():
    """Connect to Proxmox"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(PROXMOX_HOST, username=PROXMOX_USER, password=PROXMOX_PASSWORD, timeout=10)
    return client


def run_on_vm(proxmox, cmd):
    """Run command on VM through Proxmox"""
    full_cmd = f"sshpass -p '{VM_PASSWORD}' ssh -o StrictHostKeyChecking=no {VM_USER}@{VM_IP} \"{cmd}\""
    stdin, stdout, stderr = proxmox.exec_command(full_cmd)
    out = stdout.read().decode()
    err = stderr.read().decode()
    return out, err


def check_vm_status():
    """Check current VM status"""
    print("=" * 60)
    print("CHECKING VM STATUS")
    print("=" * 60)
    
    try:
        proxmox = get_proxmox_connection()
        print("[OK] Connected to Proxmox")
        
        # Check VM connectivity
        out, err = run_on_vm(proxmox, "hostname")
        if out.strip():
            print(f"[OK] VM hostname: {out.strip()}")
        else:
            print(f"[ERROR] Cannot connect to VM: {err}")
            return
        
        # Check disk space
        out, err = run_on_vm(proxmox, "df -h /")
        print(f"\nDisk Space:\n{out}")
        
        # Check Docker
        out, err = run_on_vm(proxmox, "sudo docker ps --format 'table {{.Names}}\t{{.Status}}'")
        print(f"Docker Containers:\n{out}")
        
        # Check if images directory exists
        out, err = run_on_vm(proxmox, "ls -la /opt/mycosoft/images/ 2>/dev/null || echo 'Directory not found'")
        print(f"\nImages directory:\n{out}")
        
        proxmox.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        return False


def transfer_images():
    """Transfer Docker images to VM"""
    print("\n" + "=" * 60)
    print("TRANSFERRING DOCKER IMAGES TO VM")
    print("=" * 60)
    
    try:
        proxmox = get_proxmox_connection()
        
        # Create destination directory
        print("Creating destination directory...")
        out, err = run_on_vm(proxmox, "sudo mkdir -p /opt/mycosoft/images; sudo chown mycosoft:mycosoft /opt/mycosoft/images")
        print(f"  {out or 'Created'}")
        
        # Get list of tar files
        tar_files = list(EXPORT_DIR.glob("*.tar"))
        print(f"\nFound {len(tar_files)} images to transfer:")
        for f in tar_files:
            size_mb = f.stat().st_size / (1024 * 1024)
            print(f"  - {f.name}: {size_mb:.1f} MB")
        
        total_size = sum(f.stat().st_size for f in tar_files) / (1024 * 1024)
        print(f"\nTotal: {total_size:.1f} MB")
        
        # Transfer each file
        sftp_proxmox = proxmox.open_sftp()
        
        for i, tar_file in enumerate(tar_files, 1):
            print(f"\n[{i}/{len(tar_files)}] Transferring {tar_file.name}...")
            size_mb = tar_file.stat().st_size / (1024 * 1024)
            
            # First copy to Proxmox /tmp
            proxmox_temp = f"/tmp/{tar_file.name}"
            
            print(f"  -> Uploading to Proxmox ({size_mb:.1f} MB)...")
            start = time.time()
            
            # Use callback to show progress
            def progress(transferred, total):
                pct = (transferred / total) * 100
                print(f"\r    {pct:.1f}% ({transferred/(1024*1024):.1f}/{total/(1024*1024):.1f} MB)", end="", flush=True)
            
            sftp_proxmox.put(str(tar_file), proxmox_temp, callback=progress)
            print()  # New line after progress
            
            elapsed = time.time() - start
            print(f"    Uploaded in {elapsed:.1f}s ({size_mb/elapsed:.1f} MB/s)")
            
            # Then copy from Proxmox to VM
            print(f"  -> Copying to VM...")
            cmd = f"sshpass -p '{VM_PASSWORD}' scp -o StrictHostKeyChecking=no {proxmox_temp} {VM_USER}@{VM_IP}:/opt/mycosoft/images/"
            stdin, stdout, stderr = proxmox.exec_command(cmd)
            stdout.read()  # Wait for completion
            err = stderr.read().decode()
            if err and "warning" not in err.lower():
                print(f"    Warning: {err}")
            
            # Cleanup Proxmox temp
            proxmox.exec_command(f"rm -f {proxmox_temp}")
            print(f"    Done!")
        
        sftp_proxmox.close()
        
        # Verify transfer
        print("\nVerifying transferred files...")
        out, err = run_on_vm(proxmox, "ls -la /opt/mycosoft/images/")
        print(out)
        
        proxmox.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False


def load_images():
    """Load Docker images on VM"""
    print("\n" + "=" * 60)
    print("LOADING DOCKER IMAGES ON VM")
    print("=" * 60)
    
    try:
        proxmox = get_proxmox_connection()
        
        # Load each image
        out, err = run_on_vm(proxmox, "cd /opt/mycosoft/images && for f in *.tar; do echo Loading $f...; sudo docker load -i $f; done")
        print(out)
        if err:
            print(f"Errors: {err}")
        
        # List loaded images
        print("\nLoaded images:")
        out, err = run_on_vm(proxmox, "sudo docker images | grep -E 'mycosoft|mindex|website'")
        print(out)
        
        proxmox.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        action = sys.argv[1]
        if action == "status":
            check_vm_status()
        elif action == "transfer":
            transfer_images()
        elif action == "load":
            load_images()
        elif action == "all":
            if check_vm_status():
                if transfer_images():
                    load_images()
    else:
        # Default: check status
        check_vm_status()
