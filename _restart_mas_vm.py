#!/usr/bin/env python3
"""
Restart MAS Orchestrator on VM - February 3, 2026
"""
import paramiko
import time
import sys

VM_HOST = "192.168.0.188"
VM_USER = "mycosoft"
VM_PASS = "Mushroom1!"

def main():
    print("=" * 60)
    print("RESTARTING MAS ORCHESTRATOR ON VM")
    print("=" * 60)
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print(f"\n[1/5] Connecting to {VM_HOST}...")
        ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=10)
        print("[OK] Connected")
        
        # Check current docker state
        print("\n[2/5] Checking Docker containers...")
        stdin, stdout, stderr = ssh.exec_command("docker ps -a --format '{{.Names}} {{.Status}}' | grep -E 'orchestrator|mas'")
        containers = stdout.read().decode().strip()
        print(f"Current containers:\n{containers if containers else '(none found)'}")
        
        # Find the MAS directory
        print("\n[3/5] Finding MAS directory...")
        stdin, stdout, stderr = ssh.exec_command("ls -la /home/mycosoft/mycosoft-mas 2>/dev/null || ls -la ~/mycosoft-mas 2>/dev/null || echo 'NOT FOUND'")
        result = stdout.read().decode().strip()
        
        if "NOT FOUND" in result:
            print("[WARN] MAS directory not found, will need to clone...")
            stdin, stdout, stderr = ssh.exec_command("cd ~ && git clone https://github.com/MycosoftLabs/mycosoft-mas.git 2>&1")
            print(stdout.read().decode())
        else:
            print("[OK] MAS directory exists")
        
        # Pull latest code
        print("\n[4/5] Pulling latest code...")
        commands = [
            "cd ~/mycosoft-mas && git fetch origin && git reset --hard origin/main 2>&1",
        ]
        for cmd in commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            output = stdout.read().decode().strip()
            if output:
                print(output[:200])
        
        # Start the orchestrator
        print("\n[5/5] Starting MAS Orchestrator...")
        
        # Create a simple start script
        start_script = '''#!/bin/bash
cd ~/mycosoft-mas
export PYTHONPATH=~/mycosoft-mas:$PYTHONPATH

# Stop any existing
docker stop mas-orchestrator 2>/dev/null
docker rm mas-orchestrator 2>/dev/null

# Start fresh
docker run -d \\
    --name mas-orchestrator \\
    --restart unless-stopped \\
    -p 8001:8001 \\
    -e PYTHONPATH=/app \\
    -e REDIS_URL=redis://192.168.0.188:6379 \\
    -e POSTGRES_URL=postgresql://postgres:postgres@192.168.0.188:5432/mycosoft \\
    -e N8N_URL=http://192.168.0.188:5678 \\
    -v ~/mycosoft-mas:/app \\
    python:3.11-slim \\
    bash -c "cd /app && pip install -q fastapi uvicorn redis httpx sqlalchemy psycopg2-binary && python -m uvicorn mycosoft_mas.core.myca_main:app --host 0.0.0.0 --port 8001"

echo "Waiting for orchestrator to start..."
sleep 10

# Check health
curl -s http://localhost:8001/health || echo "Health check failed"
'''
        
        # Write and execute the script
        stdin, stdout, stderr = ssh.exec_command(f"cat > ~/start_orchestrator.sh << 'SCRIPT'\n{start_script}\nSCRIPT")
        stdout.read()
        
        stdin, stdout, stderr = ssh.exec_command("chmod +x ~/start_orchestrator.sh && ~/start_orchestrator.sh 2>&1")
        time.sleep(3)
        
        # Read output progressively
        for i in range(20):
            if stdout.channel.recv_ready():
                output = stdout.channel.recv(4096).decode()
                print(output, end='')
            if stdout.channel.exit_status_ready():
                break
            time.sleep(1)
        
        # Final health check
        print("\n\n[FINAL] Health check...")
        stdin, stdout, stderr = ssh.exec_command("curl -s http://localhost:8001/health 2>&1 || echo 'FAILED'")
        health = stdout.read().decode().strip()
        print(f"Health: {health}")
        
        if "status" in health.lower() or "ok" in health.lower():
            print("\n[SUCCESS] MAS Orchestrator is running!")
        else:
            print("\n[WARN] Orchestrator may still be starting. Check logs:")
            stdin, stdout, stderr = ssh.exec_command("docker logs mas-orchestrator --tail 20 2>&1")
            print(stdout.read().decode())
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        ssh.close()

if __name__ == "__main__":
    main()
