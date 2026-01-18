#!/usr/bin/env python3
"""Simple VM status check script"""

import subprocess
import sys
import os

# Force UTF-8 output
os.environ['PYTHONIOENCODING'] = 'utf-8'

VM_IP = "192.168.0.187"
PROXMOX_HOST = "192.168.0.202"
VM_USER = "mycosoft"
VM_PASSWORD = "Mushroom1!Mushroom1!"

def run_on_vm(command: str) -> str:
    """Run a command on the VM via Proxmox host"""
    # Build SSH chain: Windows -> Proxmox -> VM
    full_cmd = f"sshpass -p '{VM_PASSWORD}' ssh -o StrictHostKeyChecking=no {VM_USER}@{VM_IP} '{command}'"
    
    # Run via Proxmox
    proxmox_cmd = ["ssh", "-o", "StrictHostKeyChecking=no", f"root@{PROXMOX_HOST}", full_cmd]
    
    try:
        result = subprocess.run(
            proxmox_cmd,
            capture_output=True,
            text=True,
            timeout=60,
            encoding='utf-8',
            errors='replace'
        )
        return result.stdout + result.stderr
    except Exception as e:
        return f"Error: {e}"


def main():
    print("=" * 60)
    print("VM 103 STATUS CHECK")
    print("=" * 60)
    
    # Check 1: VM is reachable
    print("\n[1] Checking VM connectivity...")
    result = run_on_vm("echo 'Connected to VM'")
    print(f"    {result.strip()}")
    
    # Check 2: List /opt/mycosoft
    print("\n[2] Contents of /opt/mycosoft/:")
    result = run_on_vm("ls -la /opt/mycosoft/ 2>/dev/null || echo 'Directory not found'")
    for line in result.strip().split('\n')[:15]:
        print(f"    {line}")
    
    # Check 3: Docker containers
    print("\n[3] Docker containers:")
    result = run_on_vm("docker ps -a --format 'table {{.Names}}\\t{{.Status}}' 2>/dev/null || echo 'Docker not running'")
    for line in result.strip().split('\n')[:15]:
        print(f"    {line}")
    
    # Check 4: Check website docker-compose
    print("\n[4] Website docker-compose.yml (first 20 lines):")
    result = run_on_vm("head -20 /opt/mycosoft/website/docker-compose.yml 2>/dev/null || echo 'File not found'")
    for line in result.strip().split('\n')[:10]:
        print(f"    {line}")
    
    # Check 5: Disk space
    print("\n[5] Disk space:")
    result = run_on_vm("df -h / | tail -1")
    print(f"    {result.strip()}")
    
    print("\n" + "=" * 60)
    print("CHECK COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
