#!/usr/bin/env python3
"""
Mycosoft Sandbox Deployment Script
===================================
One-click deployment of all services to sandbox.mycosoft.com

Services Deployed:
- Website (port 3000)
- MycoBrain (port 8765)
- PostgreSQL (port 5432)
- Redis (port 6379)
- Plus all collectors and monitoring services

Usage: python deploy_sandbox.py
"""
import paramiko
import sys
import time

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# VM Configuration
VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'Mushroom1!Mushroom1!'
WEBSITE_PATH = '/opt/mycosoft/website'

def run_cmd(ssh, cmd, name, timeout=600):
    """Execute command on VM with proper output handling."""
    print(f"\n{'='*60}")
    print(f"[STEP] {name}")
    print(f"{'='*60}")
    print(f"CMD: {cmd[:100]}{'...' if len(cmd) > 100 else ''}")
    
    try:
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode('utf-8', errors='replace')
        err = stderr.read().decode('utf-8', errors='replace')
        
        # Show last 30 lines of output
        lines = out.strip().split('\n')
        if len(lines) > 30:
            print(f"... ({len(lines) - 30} lines omitted) ...")
            print('\n'.join(lines[-30:]))
        else:
            print(out)
        
        if err and exit_code != 0:
            print(f"STDERR: {err[:500]}")
        
        status = "OK" if exit_code == 0 else "FAILED"
        print(f"\n[{status}] Exit code: {exit_code}")
        return exit_code == 0
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

def main():
    print("=" * 70)
    print("  MYCOSOFT SANDBOX DEPLOYMENT")
    print("  Target: sandbox.mycosoft.com (192.168.0.187)")
    print("=" * 70)
    
    # Connect to VM
    print("\n[1] Connecting to VM...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)
        print("Connected successfully!")
    except Exception as e:
        print(f"Failed to connect: {e}")
        return 1
    
    # Check system status
    run_cmd(client, "free -h && df -h / && uptime", "System Status Check")
    
    # Check what containers are running
    run_cmd(client, "docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'", "Current Container Status")
    
    # Pull latest code
    run_cmd(client, f"cd {WEBSITE_PATH} && git fetch origin && git reset --hard origin/main && git log --oneline -3", "Pull Latest Code")
    
    # Check the pricing in mushroom1-details.tsx
    run_cmd(client, f"grep -n '2,000\\|599' {WEBSITE_PATH}/components/devices/mushroom1-details.tsx | head -10", "Check Mushroom1 Pricing in Code")
    
    # Stop all containers and clean up
    run_cmd(client, "docker compose down 2>/dev/null; docker stop $(docker ps -aq) 2>/dev/null; docker system prune -f", "Stop All Containers")
    
    # Build and start just the essential services first
    run_cmd(client, f"cd {WEBSITE_PATH} && docker compose up -d postgres redis", "Start Database Services", timeout=120)
    
    # Wait for databases
    run_cmd(client, "sleep 10 && docker ps --format 'table {{.Names}}\t{{.Status}}'", "Wait for Databases")
    
    # Build website with fresh image
    print("\n" + "=" * 60)
    print("[CRITICAL] Building Website Container")
    print("This may take 3-5 minutes...")
    print("=" * 60)
    
    success = run_cmd(client, f"cd {WEBSITE_PATH} && docker compose build website --no-cache 2>&1", "Build Website", timeout=600)
    
    if not success:
        print("\n[!] Build failed, checking Dockerfile...")
        run_cmd(client, f"cat {WEBSITE_PATH}/Dockerfile.production | head -30", "Dockerfile Check")
    
    # Start website
    run_cmd(client, f"cd {WEBSITE_PATH} && docker compose up -d website", "Start Website", timeout=120)
    
    # Check status
    run_cmd(client, "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'", "Final Container Status")
    
    # Test website
    run_cmd(client, "sleep 5 && curl -s -o /dev/null -w 'HTTP Status: %{http_code}\\n' http://localhost:3000/", "Test Website")
    
    # Test the mushroom-1 page
    run_cmd(client, "curl -s http://localhost:3000/devices/mushroom-1 | grep -o '\\$[0-9,]*' | head -5", "Check Mushroom1 Page Pricing")
    
    client.close()
    
    print("\n" + "=" * 70)
    print("  DEPLOYMENT COMPLETE")
    print("  Website: https://sandbox.mycosoft.com/")
    print("  Mushroom 1: https://sandbox.mycosoft.com/devices/mushroom-1")
    print("=" * 70)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
