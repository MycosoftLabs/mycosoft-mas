#!/usr/bin/env python3
"""Fix MINDEX port conflict on VM 189"""

import paramiko
import sys
import os

# Load credentials from environment
VM_189 = os.environ.get("MINDEX_VM_IP", "192.168.0.189")
SSH_USER = os.environ.get("VM_USER", "mycosoft")
SSH_PASS = os.environ.get("VM_PASSWORD")

if not SSH_PASS:
    print("ERROR: VM_PASSWORD environment variable is not set.")
    print("Please set it before running this script:")
    print("  $env:VM_PASSWORD = 'your-password'  # PowerShell")
    print("  export VM_PASSWORD='your-password'  # Bash")
    sys.exit(1)


def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print(f"Connecting to {VM_189}...")
        client.connect(VM_189, username=SSH_USER, password=SSH_PASS, timeout=30)
        
        # Stop the container
        print("\n[1/4] Stopping container...")
        cmd = "docker stop mindex-api"
        stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
        print(stdout.read().decode('utf-8', errors='replace'))
        
        # Kill any process using port 8000
        print("\n[2/4] Killing any process on port 8000...")
        cmd = "sudo fuser -k 8000/tcp 2>/dev/null || echo 'No process on port'"
        stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
        print(stdout.read().decode('utf-8', errors='replace'))
        
        # Check if port is free
        print("\n[3/4] Checking port...")
        cmd = "sudo lsof -i :8000 2>/dev/null | head -5 || echo 'Port is free'"
        stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
        print(stdout.read().decode('utf-8', errors='replace'))
        
        # Start container
        print("\n[4/4] Starting container...")
        cmd = "docker start mindex-api && sleep 5 && docker logs mindex-api 2>&1 | tail -10"
        stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
        print(stdout.read().decode('utf-8', errors='replace'))
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
