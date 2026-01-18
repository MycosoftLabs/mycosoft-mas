#!/usr/bin/env python3
"""Install Docker on VM 103 via SSH"""

import paramiko
import time

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "Mushroom1!Mushroom1!"

def run_sudo_command(ssh, cmd, timeout=600):
    """Run a sudo command with password via stdin"""
    full_cmd = f"echo '{VM_PASS}' | sudo -S {cmd}"
    print(f"\n>>> Running: sudo {cmd[:60]}...")
    
    stdin, stdout, stderr = ssh.exec_command(full_cmd, timeout=timeout)
    
    out = stdout.read().decode()
    err = stderr.read().decode()
    
    if out:
        # Print last 20 lines to avoid flooding
        lines = out.strip().split('\n')
        if len(lines) > 20:
            print(f"... ({len(lines) - 20} lines omitted)")
            print('\n'.join(lines[-20:]))
        else:
            print(out)
    
    # Filter out password prompt from stderr
    err_lines = [l for l in err.split('\n') if 'password' not in l.lower() and l.strip()]
    if err_lines:
        print(f"stderr: {' '.join(err_lines[:5])}")
    
    return out, err

def run_command(ssh, cmd, timeout=300):
    """Run a regular command"""
    print(f"\n>>> Running: {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    
    out = stdout.read().decode()
    err = stderr.read().decode()
    
    if out:
        print(out)
    if err:
        print(f"stderr: {err}")
    
    return out, err

def main():
    print("=" * 60)
    print(f"Connecting to VM at {VM_IP}...")
    print("=" * 60)
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASS, timeout=30)
    
    print("Connected!")
    
    # Check current state
    run_command(ssh, "hostname && uname -a")
    
    # Enable QEMU Guest Agent
    print("\n=== Enabling QEMU Guest Agent ===")
    run_sudo_command(ssh, "systemctl enable --now qemu-guest-agent")
    
    # Install Docker
    print("\n=== Downloading Docker installer ===")
    run_command(ssh, "curl -fsSL https://get.docker.com -o /tmp/get-docker.sh")
    
    print("\n=== Installing Docker (this takes a few minutes) ===")
    run_sudo_command(ssh, "sh /tmp/get-docker.sh", timeout=600)
    
    # Add user to docker group
    print("\n=== Adding user to docker group ===")
    run_sudo_command(ssh, "usermod -aG docker mycosoft")
    
    # Install Docker Compose plugin
    print("\n=== Installing Docker Compose ===")
    run_sudo_command(ssh, "apt install -y docker-compose-plugin", timeout=300)
    
    # Start Docker
    print("\n=== Starting Docker ===")
    run_sudo_command(ssh, "systemctl enable --now docker")
    
    # Verify installation
    print("\n=== Verifying Installation ===")
    run_sudo_command(ssh, "docker --version")
    run_sudo_command(ssh, "docker compose version")
    
    # Install additional tools
    print("\n=== Installing additional tools ===")
    run_sudo_command(ssh, "apt install -y git curl wget htop net-tools")
    
    ssh.close()
    print("\n" + "=" * 60)
    print("DOCKER INSTALLATION COMPLETE!")
    print(f"VM IP: {VM_IP}")
    print("You can now SSH with: ssh mycosoft@192.168.0.187")
    print("=" * 60)

if __name__ == "__main__":
    main()
