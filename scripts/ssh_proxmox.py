#!/usr/bin/env python3
"""SSH to Proxmox to check auth status."""

import subprocess
import sys

PROXMOX_IP = '192.168.0.90'
USERNAME = 'root'
PASSWORD = '20202020'

# Commands to run on Proxmox
commands = [
    "hostname",
    "cat /etc/pve/.version 2>/dev/null || pveversion",
    "cat /etc/passwd | grep root",
    "pveum user list 2>/dev/null || echo 'pveum not available'",
    "systemctl status pveproxy --no-pager | head -5",
    "journalctl -u pveproxy --no-pager -n 10 2>/dev/null | tail -10",
]

print("=" * 60)
print(f"  SSH TO PROXMOX - {PROXMOX_IP}")
print("=" * 60)

# Use paramiko if available, otherwise try subprocess
try:
    import paramiko
    
    print("\nConnecting via paramiko...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(PROXMOX_IP, username=USERNAME, password=PASSWORD, timeout=10)
        print("Connected successfully!")
        
        for cmd in commands:
            print(f"\n>>> {cmd}")
            stdin, stdout, stderr = client.exec_command(cmd, timeout=10)
            output = stdout.read().decode()
            error = stderr.read().decode()
            if output:
                print(output.strip())
            if error:
                print(f"STDERR: {error.strip()}")
        
        # Check PAM configuration
        print("\n>>> Checking PAM auth...")
        stdin, stdout, stderr = client.exec_command("cat /etc/pam.d/common-auth | head -20")
        print(stdout.read().decode())
        
        # Check if root password is set correctly
        print("\n>>> Testing local PAM auth...")
        stdin, stdout, stderr = client.exec_command(f"echo '{PASSWORD}' | su -c 'echo PAM_AUTH_OK' root 2>&1")
        result = stdout.read().decode()
        print(result)
        
        client.close()
        
    except paramiko.AuthenticationException:
        print("SSH Authentication failed! Password might be wrong.")
    except paramiko.SSHException as e:
        print(f"SSH error: {e}")
    except Exception as e:
        print(f"Connection error: {e}")
        
except ImportError:
    print("paramiko not installed, trying plink...")
    
    # Try with plink
    cmd = f'echo y | plink -ssh {USERNAME}@{PROXMOX_IP} -pw "{PASSWORD}" "hostname && pveversion"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    print(result.stdout)
    print(result.stderr)

print("\n" + "=" * 60)
