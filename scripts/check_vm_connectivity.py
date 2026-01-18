#!/usr/bin/env python3
"""Check VM connectivity and status"""

import paramiko
import time

# Configuration
PROXMOX_HOST = "192.168.0.202"
PROXMOX_USER = "root"
PROXMOX_PASSWORD = "20202020"

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "Mushroom1!Mushroom1!"

def main():
    print("=" * 50)
    print("CHECKING VM CONNECTIVITY")
    print("=" * 50)
    
    # Connect to Proxmox
    print("\n[1] Connecting to Proxmox host...")
    proxmox = paramiko.SSHClient()
    proxmox.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        proxmox.connect(PROXMOX_HOST, username=PROXMOX_USER, password=PROXMOX_PASSWORD, timeout=10)
        print("    SUCCESS: Connected to Proxmox!")
    except Exception as e:
        print(f"    FAILED: {e}")
        return
    
    # Test VM connectivity via Proxmox
    print("\n[2] Testing VM connectivity through Proxmox...")
    cmd = f"sshpass -p '{VM_PASSWORD}' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 {VM_USER}@{VM_IP} 'hostname && uptime && df -h /'"
    
    try:
        stdin, stdout, stderr = proxmox.exec_command(cmd, timeout=20)
        output = stdout.read().decode()
        error = stderr.read().decode()
        
        if output:
            print("    SUCCESS: VM is reachable!")
            print(f"    Output:\n{output}")
        if error:
            print(f"    Errors: {error}")
    except Exception as e:
        print(f"    FAILED: {e}")
    
    # Check Docker status on VM
    print("\n[3] Checking Docker status on VM...")
    cmd = f"sshpass -p '{VM_PASSWORD}' ssh -o StrictHostKeyChecking=no {VM_USER}@{VM_IP} 'sudo docker ps --format \"table {{{{.Names}}}}\\t{{{{.Status}}}}\" 2>/dev/null || echo Docker not running'"
    
    try:
        stdin, stdout, stderr = proxmox.exec_command(cmd, timeout=20)
        output = stdout.read().decode()
        print(f"    Docker containers:\n{output}")
    except Exception as e:
        print(f"    FAILED: {e}")
    
    # Check disk space
    print("\n[4] Checking disk space on VM...")
    cmd = f"sshpass -p '{VM_PASSWORD}' ssh -o StrictHostKeyChecking=no {VM_USER}@{VM_IP} 'df -h'"
    
    try:
        stdin, stdout, stderr = proxmox.exec_command(cmd, timeout=20)
        output = stdout.read().decode()
        print(f"    Disk space:\n{output}")
    except Exception as e:
        print(f"    FAILED: {e}")
    
    proxmox.close()
    print("\n" + "=" * 50)
    print("CONNECTIVITY CHECK COMPLETE")
    print("=" * 50)

if __name__ == "__main__":
    main()
