#!/usr/bin/env python3
"""
VM SSH Setup Script
Connects to VM 103 via SSH and runs setup commands
"""

import subprocess
import sys
import time
import socket

VM_IP = "192.168.0.87"
VM_USER = "mycosoft"
VM_PASS = "REDACTED_VM_SSH_PASSWORD"
PROXMOX_HOST = "192.168.0.202"
PROXMOX_USER = "root"
PROXMOX_PASS = "20202020"


def check_ssh_port(host, port=22, timeout=3):
    """Check if SSH port is open"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        print(f"Error checking port: {e}")
        return False


def run_ssh_command(host, user, password, command):
    """Run SSH command using sshpass if available, otherwise provide instructions"""
    
    # Try using ssh with password via stdin
    ssh_cmd = f'ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {user}@{host} "{command}"'
    
    print(f"Running: {ssh_cmd}")
    print(f"Password: {password}")
    
    try:
        # Try with sshpass if available
        result = subprocess.run(
            ['sshpass', '-p', password, 'ssh', '-o', 'StrictHostKeyChecking=no', 
             '-o', 'UserKnownHostsFile=/dev/null', f'{user}@{host}', command],
            capture_output=True,
            text=True,
            timeout=60
        )
        print(f"Output: {result.stdout}")
        if result.stderr:
            print(f"Stderr: {result.stderr}")
        return result.returncode == 0
    except FileNotFoundError:
        print("sshpass not found, trying alternative method...")
        return False
    except Exception as e:
        print(f"SSH failed: {e}")
        return False


def ssh_via_proxmox(command):
    """SSH to VM via Proxmox host"""
    
    # Command to run on Proxmox that SSHes to VM
    proxmox_cmd = f'sshpass -p "{VM_PASS}" ssh -o StrictHostKeyChecking=no {VM_USER}@{VM_IP} "{command}"'
    
    full_cmd = f'ssh -o StrictHostKeyChecking=no {PROXMOX_USER}@{PROXMOX_HOST} \'{proxmox_cmd}\''
    
    print(f"Executing via Proxmox: {full_cmd}")
    
    try:
        result = subprocess.run(
            ['ssh', '-o', 'StrictHostKeyChecking=no', f'{PROXMOX_USER}@{PROXMOX_HOST}', proxmox_cmd],
            capture_output=True,
            text=True,
            timeout=120
        )
        print(f"Output: {result.stdout}")
        if result.stderr:
            print(f"Stderr: {result.stderr}")
        return result.returncode == 0
    except Exception as e:
        print(f"SSH via Proxmox failed: {e}")
        return False


def main():
    print("=" * 60)
    print("VM 103 (mycosoft-sandbox) SSH Setup")
    print("=" * 60)
    
    # Check if VM SSH port is open
    print(f"\nChecking SSH port on {VM_IP}...")
    if check_ssh_port(VM_IP):
        print(f"✓ SSH port 22 is OPEN on {VM_IP}")
        
        # Try direct SSH
        print("\nAttempting direct SSH connection...")
        if run_ssh_command(VM_IP, VM_USER, VM_PASS, "hostname && ip addr show ens18 | grep inet"):
            print("✓ Direct SSH successful!")
            
            # Run setup commands
            print("\nRunning setup commands...")
            commands = [
                "sudo apt update",
                "sudo apt install -y qemu-guest-agent openssh-server",
                "sudo systemctl enable qemu-guest-agent",
                "sudo systemctl start qemu-guest-agent",
            ]
            for cmd in commands:
                print(f"\nExecuting: {cmd}")
                run_ssh_command(VM_IP, VM_USER, VM_PASS, f"echo '{VM_PASS}' | sudo -S {cmd}")
    else:
        print(f"✗ SSH port 22 is CLOSED on {VM_IP}")
        print("\nSSH server is not installed yet. Options:")
        print("1. Install via Proxmox console (browser)")
        print("2. Use Proxmox qm terminal command")
        
        # Try via Proxmox
        print("\nTrying to execute via Proxmox host...")
        ssh_via_proxmox("hostname")
    
    print("\n" + "=" * 60)
    print("Done!")


if __name__ == "__main__":
    main()

