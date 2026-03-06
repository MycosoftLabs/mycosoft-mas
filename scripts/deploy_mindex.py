#!/usr/bin/env python3
"""Deploy MINDEX API to VM 189. Prefer docker compose on VM. Loads .credentials.local."""

import paramiko
import sys
import os
from pathlib import Path

# Load credentials from .credentials.local
creds = Path(__file__).resolve().parent.parent / ".credentials.local"
if creds.exists():
    for line in creds.read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

VM_189 = os.environ.get("MINDEX_VM_IP", "192.168.0.189")
SSH_USER = os.environ.get("VM_USER", "mycosoft")
SSH_PASS = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")

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
        
        # Pull latest code
        print("\n[1/3] Pulling latest code...")
        cmd = "cd /home/mycosoft/mindex && git fetch origin && git reset --hard origin/main && git log -1 --oneline"
        stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
        print(stdout.read().decode('utf-8', errors='replace'))
        
        # Stop, build, and start via docker compose (VM has .env with DB password). Service is 'api'.
        print("\n[2/3] Stopping and rebuilding via docker compose...")
        cmd = "cd /home/mycosoft/mindex && docker compose stop api 2>/dev/null; docker compose build --no-cache api 2>&1 | tail -60"
        stdin, stdout, stderr = client.exec_command(cmd, timeout=900)
        out = stdout.read().decode('utf-8', errors='replace')
        print(out)
        if stdout.channel.recv_exit_status() != 0:
            print("Build may have failed - check output above")
        
        print("\n[3/3] Starting MINDEX API container...")
        cmd = "cd /home/mycosoft/mindex && docker compose up -d api"
        stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
        out = stdout.read().decode('utf-8', errors='replace')
        err = stderr.read().decode('utf-8', errors='replace')
        print(out or err)
        
        # Check status
        print("\n[+] Container status:")
        stdin, stdout, stderr = client.exec_command("docker ps --filter name=mindex-api", timeout=30)
        print(stdout.read().decode('utf-8', errors='replace'))
        
        # Health check
        print("\n[+] Health check:")
        import time
        time.sleep(5)
        stdin, stdout, stderr = client.exec_command("curl -s http://127.0.0.1:8000/health 2>/dev/null || curl -s http://127.0.0.1:8000/api/v1/health", timeout=30)
        print(stdout.read().decode('utf-8', errors='replace'))
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
