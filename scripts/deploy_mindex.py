#!/usr/bin/env python3
"""Deploy MINDEX API to VM 189"""

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
        
        # Pull latest code
        print("\n[0/3] Pulling latest code...")
        cmd = "cd /home/mycosoft/mindex && git fetch && git reset --hard origin/main && git log -1 --oneline"
        stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
        print(stdout.read().decode('utf-8', errors='replace'))
        
        # Build Docker image
        print("\n[1/3] Building MINDEX API Docker image (no cache)...")
        cmd = "cd /home/mycosoft/mindex && docker build --no-cache -t mindex-api:latest . 2>&1 | tail -30"
        stdin, stdout, stderr = client.exec_command(cmd, timeout=600)
        out = stdout.read().decode('utf-8', errors='replace')
        print(out)
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            print(f"Build may have failed (exit {exit_code})")
            # Check if image exists anyway
            stdin, stdout, stderr = client.exec_command("docker images mindex-api:latest --format '{{.ID}}'", timeout=30)
            image_id = stdout.read().decode('utf-8', errors='replace').strip()
            if not image_id:
                print("No image created, aborting.")
                return
            print(f"Image exists: {image_id}, continuing...")
        
        # Stop and remove old container
        print("\n[2/3] Stopping old container...")
        cmd = "docker stop mindex-api 2>/dev/null; docker rm mindex-api 2>/dev/null; echo 'Done'"
        stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
        print(stdout.read().decode('utf-8', errors='replace'))
        
        # Start new container
        print("\n[3/3] Starting MINDEX API container...")
        cmd = """docker run -d --name mindex-api \
          --restart unless-stopped \
          --network host \
          -e MINDEX_DB_HOST=127.0.0.1 \
          -e MINDEX_DB_PORT=5432 \
          -e MINDEX_DB_USER=mycosoft \
          -e MINDEX_DB_PASSWORD=REDACTED_DB_PASSWORD \
          -e MINDEX_DB_NAME=mindex \
          -e REDIS_URL=redis://127.0.0.1:6379/0 \
          -e QDRANT_URL=http://127.0.0.1:6333 \
          -e API_HOST=0.0.0.0 \
          -e API_PORT=8000 \
          -e MINDEX_API_KEY=mindex_dev_key_2026 \
          mindex-api:latest"""
        stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
        print(stdout.read().decode('utf-8', errors='replace'))
        err = stderr.read().decode('utf-8', errors='replace')
        if err:
            print(f"Stderr: {err}")
        
        # Check status
        print("\n[+] Container status:")
        stdin, stdout, stderr = client.exec_command("docker ps --filter name=mindex-api", timeout=30)
        print(stdout.read().decode('utf-8', errors='replace'))
        
        # Health check
        print("\n[+] Health check:")
        import time
        time.sleep(5)
        stdin, stdout, stderr = client.exec_command("curl -s http://127.0.0.1:8000/api/v1/health | head -200", timeout=30)
        print(stdout.read().decode('utf-8', errors='replace'))
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
