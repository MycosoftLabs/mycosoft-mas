#!/usr/bin/env python3
"""Temporary script to redeploy MAS orchestrator to VM 188."""

import paramiko
import sys
from pathlib import Path

def load_credentials():
    creds_file = Path(__file__).parent.parent / ".credentials.local"
    password = None
    with open(creds_file, 'r') as f:
        for line in f:
            if line.startswith('VM_SSH_PASSWORD=') or line.startswith('VM_PASSWORD='):
                password = line.split('=', 1)[1].strip()
                break
    return password

def run_ssh_command(ssh, cmd, desc, timeout=600):
    print(f"\n=== {desc} ===")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    output = stdout.read().decode()
    err = stderr.read().decode()
    exit_code = stdout.channel.recv_exit_status()
    
    # For build, show last 20 lines only
    if output:
        lines = output.strip().split('\n')
        if len(lines) > 20 and 'build' in desc.lower():
            print('... (truncated) ...')
            print('\n'.join(lines[-20:]))
        else:
            print(output.strip())
    if err and exit_code != 0:
        print(f"STDERR: {err.strip()}")
    print(f"Exit code: {exit_code}")
    return exit_code, output

def main():
    password = load_credentials()
    if not password:
        print("ERROR: Could not load credentials")
        sys.exit(1)
    
    print("Connecting to 192.168.0.188...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('192.168.0.188', username='mycosoft', password=password, timeout=30)
    print("Connected!")
    
    # Step 1: Check what's currently running
    run_ssh_command(ssh, "docker ps --format '{{.Names}} {{.Status}}' | grep -i orch || echo 'No orchestrator containers'", "Current containers")
    
    # Step 2: Stop ALL orchestrator containers
    run_ssh_command(ssh, "docker stop $(docker ps -q --filter 'name=orchestrator') 2>/dev/null || echo 'No running orchestrator containers to stop'", "Stop orchestrators")
    run_ssh_command(ssh, "docker rm $(docker ps -aq --filter 'name=orchestrator') 2>/dev/null || echo 'No orchestrator containers to remove'", "Remove orchestrators")
    
    # Step 3: Check port 8001 is free
    run_ssh_command(ssh, "ss -tlnp | grep 8001 || echo 'Port 8001 is free'", "Check port 8001")
    
    # Step 4: Update code
    run_ssh_command(ssh, "cd /home/mycosoft/mycosoft/mas && git fetch origin && git reset --hard origin/main", "Git update")
    
    # Step 5: Fix poetry.lock
    run_ssh_command(ssh, "cd /home/mycosoft/mycosoft/mas && poetry lock --no-update 2>&1 || echo 'Poetry lock may need attention'", "Poetry lock", timeout=120)
    
    # Step 6: Docker build
    exit_code, _ = run_ssh_command(ssh, "cd /home/mycosoft/mycosoft/mas && docker build -t mycosoft/mas-agent:latest --no-cache .", "Docker build", timeout=600)
    if exit_code != 0:
        print("\nERROR: Docker build failed!")
        ssh.close()
        sys.exit(1)
    
    # Step 7: Start container
    run_ssh_command(ssh, "docker run -d --name myca-orchestrator-new --restart unless-stopped -p 8001:8000 mycosoft/mas-agent:latest", "Start container")
    
    # Step 8: Verify
    run_ssh_command(ssh, "sleep 5 && docker ps --format '{{.Names}} {{.Status}}' | grep orch", "Verify running")
    
    # Step 9: Health check
    run_ssh_command(ssh, "curl -s http://localhost:8001/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8001/health", "Health check")
    
    ssh.close()
    print("\n=== DEPLOYMENT COMPLETE ===")

if __name__ == "__main__":
    main()
