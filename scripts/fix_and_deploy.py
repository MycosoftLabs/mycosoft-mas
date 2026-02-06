#!/usr/bin/env python3
"""
Fix permissions and deploy MYCA Voice System to Sandbox VM
Created: February 4, 2026
Updated: February 6, 2026 - Added Docker cache cleanup on every deploy
"""
import paramiko
import sys
import time

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'REDACTED_VM_SSH_PASSWORD'

MAS_REPO = "/home/mycosoft/mycosoft/mas"

def run_command(client, cmd, timeout=120):
    """Execute command and return output."""
    print(f">>> {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    exit_code = stdout.channel.recv_exit_status()
    if out:
        print(out)
    if err and exit_code != 0:
        print(f"STDERR: {err}")
    return out, err, exit_code

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print("=" * 60)
        print("MYCA Voice System - Fix & Deploy")
        print("=" * 60)
        print(f"\nConnecting to Sandbox VM ({VM_HOST})...")
        client.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)
        print("Connected!\n")
        
        # Step 0: ALWAYS Clear Docker Cache First (prevents memory bloat)
        print("=" * 60)
        print("Step 0: Clearing Docker Cache (REQUIRED on every deploy)")
        print("=" * 60)
        print("This prevents memory bloat from old images/containers...")
        run_command(client, "docker container prune -f", timeout=60)
        run_command(client, "docker image prune -a -f", timeout=120)
        run_command(client, "docker volume prune -f", timeout=60)
        run_command(client, "docker builder prune -a -f", timeout=120)
        run_command(client, "docker system prune -f", timeout=60)
        print("Docker cache cleared!")
        
        # Step 1: Fix permissions on MAS repo
        print("=" * 60)
        print("Step 1: Fixing Permissions on MAS Repository")
        print("=" * 60)
        run_command(client, f"sudo chown -R mycosoft:mycosoft {MAS_REPO}")
        run_command(client, f"sudo chmod -R 755 {MAS_REPO}")
        
        # Step 2: Pull latest code
        print("\n" + "=" * 60)
        print("Step 2: Pulling Latest Code")
        print("=" * 60)
        run_command(client, f"cd {MAS_REPO} && git fetch origin")
        run_command(client, f"cd {MAS_REPO} && git reset --hard origin/main")
        run_command(client, f"cd {MAS_REPO} && git log --oneline -5")
        
        # Step 3: Find docker-compose files
        print("\n" + "=" * 60)
        print("Step 3: Finding Docker Compose Files")
        print("=" * 60)
        run_command(client, "find /opt/mycosoft -name 'docker-compose*.yml' 2>/dev/null | head -10")
        run_command(client, "find /home/mycosoft -name 'docker-compose*.yml' 2>/dev/null | head -10")
        
        # Step 4: Check for n8n container or image
        print("\n" + "=" * 60)
        print("Step 4: Checking n8n Status")
        print("=" * 60)
        run_command(client, "docker images | grep n8n")
        run_command(client, "docker ps -a | grep n8n")
        
        # Step 5: Try to start n8n from various locations
        print("\n" + "=" * 60)
        print("Step 5: Starting n8n")
        print("=" * 60)
        
        # Check if there's a stopped n8n container
        out, _, _ = run_command(client, "docker ps -a --filter 'name=n8n' --format '{{.Names}}'")
        if 'n8n' in out:
            print("Found existing n8n container, starting it...")
            run_command(client, "docker start n8n")
        else:
            # Try to run n8n directly
            print("No existing n8n container. Checking for n8n compose files...")
            
            # Check in MAS repo
            out, _, _ = run_command(client, f"ls {MAS_REPO}/docker-compose*.yml 2>/dev/null | head -5")
            if out:
                print(f"Found compose files in MAS repo")
                # Try to start n8n from MAS repo docker-compose
                run_command(client, f"cd {MAS_REPO} && docker compose up -d n8n 2>/dev/null || echo 'n8n not in this compose'")
        
        # Step 6: Check all running services
        print("\n" + "=" * 60)
        print("Step 6: Final Container Status")
        print("=" * 60)
        run_command(client, "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'")
        
        # Step 7: Test all endpoints
        print("\n" + "=" * 60)
        print("Step 7: Testing All Endpoints")
        print("=" * 60)
        
        endpoints = [
            ("Website", "http://localhost:3000", 200),
            ("MINDEX API", "http://localhost:8000", 200),
            ("Mycorrhizae API", "http://localhost:8002", 200),
            ("n8n", "http://localhost:5678", 200),
        ]
        
        results = []
        for name, url, expected in endpoints:
            out, _, _ = run_command(client, f"curl -s -o /dev/null -w '%{{http_code}}' {url} 2>/dev/null || echo '000'")
            status = "OK" if out == str(expected) else "NOT OK"
            results.append((name, status, out))
            print(f"  {name}: {status} (HTTP {out})")
        
        # Step 8: Check disk space and memory
        print("\n" + "=" * 60)
        print("Step 8: System Resources")
        print("=" * 60)
        run_command(client, "df -h / | tail -1")
        run_command(client, "free -h | grep Mem")
        
        print("\n" + "=" * 60)
        print("Deployment Summary")
        print("=" * 60)
        print("\nService Status:")
        for name, status, code in results:
            icon = "✓" if status == "OK" else "✗"
            print(f"  {icon} {name}: {status}")
        
        print("\nTest URLs:")
        print("  - https://sandbox.mycosoft.com")
        print("  - https://sandbox.mycosoft.com/natureos")
        print("  - http://192.168.0.187:8000/docs (MINDEX API)")
        print("  - http://192.168.0.187:8002/docs (Mycorrhizae API)")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        client.close()

if __name__ == "__main__":
    main()
