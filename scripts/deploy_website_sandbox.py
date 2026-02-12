#!/usr/bin/env python3
"""Deploy website to Sandbox VM 187"""

import paramiko
import time
import sys
import io
import os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Load credentials from environment
VM = os.environ.get("SANDBOX_VM_IP", "192.168.0.187")
USER = os.environ.get("VM_USER", "mycosoft")
PASS = os.environ.get("VM_PASSWORD")

if not PASS:
    print("ERROR: VM_PASSWORD environment variable is not set.")
    print("Please set it before running this script:")
    print("  $env:VM_PASSWORD = 'your-password'  # PowerShell")
    print("  export VM_PASSWORD='your-password'  # Bash")
    sys.exit(1)


def run_cmd(client, cmd, timeout=600, show_lines=50):
    """Run command and show output"""
    print(f"Running: {cmd[:80]}...")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    
    lines = out.strip().split('\n')
    if len(lines) > show_lines:
        print(f"... ({len(lines) - show_lines} lines hidden) ...")
        for line in lines[-show_lines:]:
            print(line)
    else:
        print(out)
    
    if err.strip():
        print(f"STDERR: {err[:500]}")
    
    return stdout.channel.recv_exit_status()


def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print(f"Connecting to Sandbox VM ({VM})...")
        client.connect(VM, username=USER, password=PASS, timeout=30)
        
        # Pull latest code
        print("\n[1/4] Pulling latest code...")
        run_cmd(client, "cd /opt/mycosoft/website && git fetch && git reset --hard origin/main && git log -1 --oneline")
        
        # Build Docker image
        print("\n[2/4] Building Docker image (this takes a few minutes)...")
        exit_code = run_cmd(client, "cd /opt/mycosoft/website && docker build --no-cache -t mycosoft-always-on-mycosoft-website:latest . 2>&1", timeout=600)
        
        if exit_code != 0:
            print(f"Build may have issues (exit {exit_code}), checking image...")
            run_cmd(client, "docker images mycosoft-always-on-mycosoft-website:latest --format '{{.ID}} {{.CreatedAt}}'")
        
        # Stop and remove old container
        print("\n[3/4] Stopping old container...")
        run_cmd(client, "docker stop mycosoft-website 2>/dev/null; docker rm mycosoft-website 2>/dev/null; echo 'Stopped'")
        
        # Start new container with NAS mount
        print("\n[4/4] Starting container with NAS mount...")
        run_cmd(client, """docker run -d --name mycosoft-website -p 3000:3000 \\
            -v /opt/mycosoft/media/website/assets:/app/public/assets:ro \\
            --restart unless-stopped \\
            mycosoft-always-on-mycosoft-website:latest""")
        
        # Wait and check
        print("\nWaiting for startup...")
        time.sleep(10)
        
        # Check container
        print("\n[+] Container status:")
        run_cmd(client, "docker ps --filter name=mycosoft-website")
        
        # Health check
        print("\n[+] Health check:")
        run_cmd(client, "curl -s http://localhost:3000 | head -50")
        
        print("\n" + "=" * 60)
        print("Website deployed to sandbox.mycosoft.com")
        print("Remember to purge Cloudflare cache!")
        print("=" * 60)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()


if __name__ == "__main__":
    main()
