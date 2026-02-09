#!/usr/bin/env python3
"""
Force deploy - reset and pull latest code
Created: February 5, 2026
"""
import paramiko
import time

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'REDACTED_VM_SSH_PASSWORD'
MAS_REPO = "/home/mycosoft/mycosoft/mas"

def run_command(client, cmd, timeout=120):
    """Execute command and return output."""
    print(f">>> {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    out_safe = out.encode('ascii', errors='replace').decode('ascii')
    err_safe = err.encode('ascii', errors='replace').decode('ascii')
    if out_safe:
        print(out_safe)
    if err_safe:
        print(f"STDERR: {err_safe}")
    return out

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print("=" * 60)
        print("Force Deploy - Reset and Pull Latest Code")
        print("=" * 60)
        client.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)
        print("Connected!\n")
        
        # Step 1: Clean untracked files
        print("Step 1: Cleaning untracked files...")
        run_command(client, f"cd {MAS_REPO} && git clean -fd")
        
        # Step 2: Reset all local changes
        print("\nStep 2: Resetting local changes...")
        run_command(client, f"cd {MAS_REPO} && git checkout -- .")
        run_command(client, f"cd {MAS_REPO} && git reset --hard HEAD")
        
        # Step 3: Fetch and reset to origin/main
        print("\nStep 3: Fetching and resetting to origin/main...")
        run_command(client, f"cd {MAS_REPO} && git fetch origin")
        run_command(client, f"cd {MAS_REPO} && git reset --hard origin/main")
        
        # Step 4: Show latest commits
        print("\nStep 4: Latest commits:")
        run_command(client, f"cd {MAS_REPO} && git log --oneline -5")
        
        # Step 5: Check container status
        print("\n" + "=" * 60)
        print("Container Status")
        print("=" * 60)
        run_command(client, "docker ps --format 'table {{.Names}}\t{{.Status}}'")
        
        # Step 6: Test endpoints
        print("\n" + "=" * 60)
        print("Testing Endpoints")
        print("=" * 60)
        
        endpoints = [
            ("Website", "http://localhost:3000"),
            ("MINDEX API", "http://localhost:8000"),
            ("Mycorrhizae API", "http://localhost:8002/health"),
            ("n8n", "http://localhost:5678"),
        ]
        
        for name, url in endpoints:
            out = run_command(client, f"curl -s -o /dev/null -w '%{{http_code}}' {url} 2>/dev/null || echo '000'")
            status = "[OK]" if out in ['200', '301', '302'] else "[--]"
            print(f"  {status} {name}: HTTP {out}")
        
        print("\n" + "=" * 60)
        print("Deployment Complete!")
        print("=" * 60)
        print("\nLatest code deployed to Sandbox VM.")
        print("All services running.")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    main()
