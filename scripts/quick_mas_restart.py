#!/usr/bin/env python3
"""Quick restart of MAS container - pull latest and restart"""

import paramiko
import time
import sys
import io
import os

# Fix unicode issues
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Load credentials from environment
VM = os.environ.get("MAS_VM_IP", "192.168.0.188")
USER = os.environ.get("VM_USER", "mycosoft")
PASS = os.environ.get("VM_PASSWORD")

if not PASS:
    print("ERROR: VM_PASSWORD environment variable is not set.")
    print("Please set it before running this script:")
    print("  $env:VM_PASSWORD = 'your-password'  # PowerShell")
    print("  export VM_PASSWORD='your-password'  # Bash")
    sys.exit(1)


def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print(f"Connecting to MAS VM ({VM})...")
        client.connect(VM, username=USER, password=PASS, timeout=30)
        
        # Pull latest code
        print("\n[1/3] Pulling latest code...")
        cmd = "cd /home/mycosoft/mycosoft/mas && git fetch && git reset --hard origin/main && git log -1 --oneline"
        stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
        print(stdout.read().decode('utf-8', errors='replace'))
        
        # Stop and remove old container
        print("\n[2/3] Stopping old container...")
        cmd = "docker stop myca-orchestrator-new 2>/dev/null; docker rm myca-orchestrator-new 2>/dev/null; echo 'Done'"
        stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
        print(stdout.read().decode('utf-8', errors='replace'))
        
        # Start new container (using pre-built image)
        print("\n[3/3] Starting container...")
        # Note: Using existing image, just restart
        cmd = """docker run -d --name myca-orchestrator-new \\
            --restart unless-stopped \\
            --network host \\
            -e MAS_API_PORT=8000 \\
            -e MINDEX_API_URL=http://192.168.0.189:8000 \\
            -e REDIS_URL=redis://192.168.0.189:6379/0 \\
            -e ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}" \\
            -e OPENAI_API_KEY="${OPENAI_API_KEY:-}" \\
            -e GROQ_API_KEY="${GROQ_API_KEY:-}" \\
            -e GEMINI_API_KEY="${GEMINI_API_KEY:-}" \\
            -e XAI_API_KEY="${XAI_API_KEY:-}" \\
            mycosoft/mas-agent:latest"""
        stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
        print(stdout.read().decode('utf-8', errors='replace'))
        err = stderr.read().decode('utf-8', errors='replace')
        if err:
            print(f"Stderr: {err}")
        
        # Wait and check
        print("\nWaiting for startup...")
        time.sleep(10)
        
        # Health check
        print("\n[+] Health check:")
        stdin, stdout, stderr = client.exec_command("curl -s http://127.0.0.1:8000/health | head -200", timeout=30)
        print(stdout.read().decode('utf-8', errors='replace'))
        
        # Test ping
        print("\n[+] Testing /api/myca/ping:")
        stdin, stdout, stderr = client.exec_command("curl -s http://127.0.0.1:8000/api/myca/ping", timeout=30)
        print(stdout.read().decode('utf-8', errors='replace'))
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
