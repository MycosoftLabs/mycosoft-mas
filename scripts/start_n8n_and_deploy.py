#!/usr/bin/env python3
"""
Start n8n and deploy code to Sandbox VM
Created: February 4, 2026
"""
import paramiko
import sys

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'REDACTED_VM_SSH_PASSWORD'

def run_command(client, cmd, timeout=120):
    """Execute command and return output."""
    print(f">>> {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    exit_code = stdout.channel.recv_exit_status()
    # Replace problematic characters for Windows console
    out_safe = out.encode('ascii', errors='replace').decode('ascii')
    err_safe = err.encode('ascii', errors='replace').decode('ascii')
    if out_safe:
        print(out_safe)
    if err_safe:
        print(f"STDERR: {err_safe}")
    return out, err, exit_code

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print("=" * 60)
        print("Start n8n and Deploy Code")
        print("=" * 60)
        client.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)
        print("Connected!\n")
        
        # Step 1: Try to start n8n from the n8n folder
        print("=" * 60)
        print("Step 1: Starting n8n from dedicated compose")
        print("=" * 60)
        
        # Check if n8n compose exists
        out, _, _ = run_command(client, "cat /opt/mycosoft/mas/n8n/docker-compose.yml 2>/dev/null | head -20")
        
        if 'n8n' in out.lower() or 'version' in out.lower():
            print("\nStarting n8n from /opt/mycosoft/mas/n8n/...")
            run_command(client, "cd /opt/mycosoft/mas/n8n && docker compose up -d", timeout=180)
        else:
            # Try to run n8n directly
            print("\nNo n8n compose found. Running n8n container directly...")
            run_command(client, """docker run -d --name n8n \
                -p 5678:5678 \
                -v n8n_data:/home/node/.n8n \
                --restart unless-stopped \
                n8nio/n8n:latest""", timeout=300)
        
        # Step 2: Check if the /opt/mycosoft/mas repo can be updated instead
        print("\n" + "=" * 60)
        print("Step 2: Checking /opt/mycosoft/mas Repository")
        print("=" * 60)
        run_command(client, "ls -la /opt/mycosoft/mas/.git 2>/dev/null || echo 'No git repo'")
        run_command(client, "cd /opt/mycosoft/mas && git remote -v 2>/dev/null || echo 'No git remote'")
        
        # Try updating /opt/mycosoft/mas instead
        out, _, _ = run_command(client, "cd /opt/mycosoft/mas && git fetch origin 2>/dev/null && git status")
        if 'origin/main' in out or 'Your branch' in out:
            print("\nUpdating /opt/mycosoft/mas...")
            run_command(client, "cd /opt/mycosoft/mas && git reset --hard origin/main")
            run_command(client, "cd /opt/mycosoft/mas && git log --oneline -3")
        
        # Step 3: Final status
        print("\n" + "=" * 60)
        print("Step 3: Final Container Status")
        print("=" * 60)
        run_command(client, "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'")
        
        # Step 4: Test endpoints
        print("\n" + "=" * 60)
        print("Step 4: Testing Endpoints")
        print("=" * 60)
        
        endpoints = [
            ("Website", "http://localhost:3000"),
            ("MINDEX API", "http://localhost:8000"),
            ("Mycorrhizae API", "http://localhost:8002/health"),
            ("n8n", "http://localhost:5678"),
        ]
        
        for name, url in endpoints:
            out, _, _ = run_command(client, f"curl -s -o /dev/null -w '%{{http_code}}' {url} 2>/dev/null || echo 'FAIL'")
            status = "[OK]" if out in ['200', '301', '302'] else "[NOT OK]"
            print(f"  {status} {name}: HTTP {out}")
        
        print("\n" + "=" * 60)
        print("Done!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        client.close()

if __name__ == "__main__":
    main()
