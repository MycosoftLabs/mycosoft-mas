#!/usr/bin/env python3
"""Quick deploy to sandbox VM - Feb 5, 2026"""
import paramiko
import time

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'REDACTED_VM_SSH_PASSWORD'

def run(client, cmd, timeout=300):
    print(f">>> {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    exit_code = stdout.channel.recv_exit_status()
    if out:
        for line in out.split('\n')[:20]:
            print(f"  {line}")
        if len(out.split('\n')) > 20:
            print(f"  ... ({len(out.split(chr(10)))} total lines)")
    if err and exit_code != 0:
        print(f"  [stderr] {err[:500]}")
    return out, exit_code

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print("="*60)
    print("Deploying MINDEX + Voice to Sandbox VM")
    print("="*60)
    
    print(f"\nConnecting to {VM_HOST}...")
    client.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)
    print("Connected!\n")
    
    # Check current containers
    print("Current containers:")
    run(client, "docker ps --format 'table {{.Names}}\t{{.Status}}' | head -15")
    
    # Rebuild MINDEX API container
    print("\n" + "="*60)
    print("Rebuilding MINDEX API container...")
    print("="*60)
    
    run(client, "cd /opt/mycosoft/mas && docker compose stop mindex-api 2>/dev/null || true")
    run(client, "cd /opt/mycosoft/mas && docker compose rm -f mindex-api 2>/dev/null || true")
    run(client, "cd /opt/mycosoft/mas && docker compose build --no-cache mindex-api 2>&1 | tail -30")
    run(client, "cd /opt/mycosoft/mas && docker compose up -d mindex-api 2>&1")
    
    # Wait for container to start
    print("\nWaiting for services...")
    time.sleep(5)
    
    # Check container status
    print("\n" + "="*60)
    print("Final container status:")
    print("="*60)
    run(client, "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | head -20")
    
    # Test endpoints
    print("\n" + "="*60)
    print("Testing endpoints:")
    print("="*60)
    
    endpoints = [
        ("Website", "http://localhost:3000"),
        ("MINDEX API", "http://localhost:8000"),
        ("MINDEX Docs", "http://localhost:8000/docs"),
    ]
    
    for name, url in endpoints:
        out, _ = run(client, f"curl -s -o /dev/null -w '%{{http_code}}' {url} 2>/dev/null || echo '000'")
        status = "OK" if out in ['200', '307'] else "FAIL"
        print(f"  {name}: HTTP {out} [{status}]")
    
    print("\n" + "="*60)
    print("Deployment Complete!")
    print("="*60)
    print("\nTest URLs:")
    print("  - https://sandbox.mycosoft.com")
    print("  - http://192.168.0.187:8000/docs (MINDEX API)")
    
    client.close()

if __name__ == "__main__":
    main()
