#!/usr/bin/env python3
"""
Deploy MYCA Voice System to Sandbox VM
Created: February 4, 2026
"""
import paramiko
import sys
import time

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'Mushroom1!Mushroom1!'

MAS_REPO = "/home/mycosoft/mycosoft/mas"
COMPOSE_DIR = "/opt/mycosoft"

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
        print("MYCA Voice System Deployment")
        print("=" * 60)
        print(f"\nConnecting to Sandbox VM ({VM_HOST})...")
        client.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)
        print("Connected!\n")
        
        # Step 1: Check current container status
        print("=" * 60)
        print("Step 1: Current Container Status")
        print("=" * 60)
        run_command(client, "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'")
        
        # Step 2: Pull latest MAS code
        print("\n" + "=" * 60)
        print("Step 2: Updating MAS Repository")
        print("=" * 60)
        run_command(client, f"cd {MAS_REPO} && git fetch origin")
        run_command(client, f"cd {MAS_REPO} && git reset --hard origin/main")
        run_command(client, f"cd {MAS_REPO} && git log --oneline -3")
        
        # Step 3: Check if n8n is running, if not start it
        print("\n" + "=" * 60)
        print("Step 3: Checking n8n Status")
        print("=" * 60)
        out, _, _ = run_command(client, "docker ps --filter 'name=n8n' --format '{{.Names}}'")
        if 'n8n' not in out:
            print("n8n is not running. Starting n8n...")
            run_command(client, f"cd {COMPOSE_DIR} && docker compose -f docker-compose.always-on.yml up -d n8n", timeout=120)
            time.sleep(5)
        else:
            print("n8n is already running.")
        
        # Step 4: Check other essential services
        print("\n" + "=" * 60)
        print("Step 4: Checking Essential Services")
        print("=" * 60)
        
        # Check and start services if needed
        services = ['redis', 'postgres', 'mindex-api']
        for service in services:
            out, _, _ = run_command(client, f"docker ps --filter 'name={service}' --format '{{{{.Names}}}}'")
            if service not in out.lower():
                print(f"{service} not running - attempting to start...")
                run_command(client, f"cd {COMPOSE_DIR} && docker compose -f docker-compose.always-on.yml up -d {service}", timeout=60)
        
        # Step 5: Import n8n workflows if needed
        print("\n" + "=" * 60)
        print("Step 5: Checking n8n Workflow Imports")
        print("=" * 60)
        run_command(client, "curl -s http://localhost:5678/healthz 2>/dev/null || echo 'n8n not responding on 5678'")
        
        # Step 6: Final status check
        print("\n" + "=" * 60)
        print("Step 6: Final Container Status")
        print("=" * 60)
        run_command(client, "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'")
        
        # Step 7: Test endpoints
        print("\n" + "=" * 60)
        print("Step 7: Testing Endpoints")
        print("=" * 60)
        
        endpoints = [
            ("Website", "http://localhost:3000"),
            ("MINDEX API", "http://localhost:8000"),
            ("n8n", "http://localhost:5678"),
        ]
        
        for name, url in endpoints:
            out, _, code = run_command(client, f"curl -s -o /dev/null -w '%{{http_code}}' {url} 2>/dev/null || echo 'FAILED'")
            status = "OK" if out in ['200', '301', '302'] else "NOT RESPONDING"
            print(f"  {name}: {status} ({out})")
        
        print("\n" + "=" * 60)
        print("Deployment Complete!")
        print("=" * 60)
        print("\nTest URLs:")
        print("  - https://sandbox.mycosoft.com")
        print("  - https://sandbox.mycosoft.com/natureos")
        print("  - http://192.168.0.187:5678 (n8n)")
        print("  - http://192.168.0.187:8000 (MINDEX API)")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        client.close()

if __name__ == "__main__":
    main()
