#!/usr/bin/env python3
"""Quick health check for MINDEX VM 189: Docker containers and services."""
import os
import sys
import paramiko

# Load credentials from environment - NEVER hardcode passwords
VM_HOST = os.environ.get("MINDEX_VM_HOST", "192.168.0.189")
VM_USER = os.environ.get("VM_USER", "mycosoft")
VM_PASS = os.environ.get("VM_PASSWORD")

def run(ssh, cmd, timeout=15):
    i, o, e = ssh.exec_command(cmd, timeout=timeout)
    return o.read().decode(), e.read().decode()

def main():
    if not VM_PASS:
        print("ERROR: Set VM_PASSWORD environment variable. Never hardcode passwords!")
        sys.exit(1)
    
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=10)
    print("=== Docker on 189 ===")
    out, err = run(c, "sudo docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null")
    print(out or err)
    print("=== MINDEX API (8000) ===")
    out2, _ = run(c, "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/api/mindex/health 2>/dev/null || echo no-api")
    print("  HTTP:", out2.strip() if out2 else "no-api")
    print("=== Qdrant (6333) ===")
    out3, _ = run(c, "curl -s -o /dev/null -w '%{http_code}' http://localhost:6333/ 2>/dev/null")
    print("  HTTP:", out3.strip() if out3 else "n/a")
    c.close()
    print("\nDone.")

if __name__ == "__main__":
    main()
