#!/usr/bin/env python3
"""Check port mappings and services"""

import paramiko
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "Mushroom1!Mushroom1!"

def run_sudo(ssh, cmd):
    full_cmd = f"echo '{VM_PASSWORD}' | sudo -S {cmd}"
    stdin, stdout, stderr = ssh.exec_command(full_cmd, timeout=300)
    out = stdout.read().decode(errors='replace')
    err = stderr.read().decode(errors='replace')
    return out, err

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=30)
    print("Connected!")

    # Check listening ports
    print("\n=== LISTENING PORTS ===")
    out, _ = run_sudo(ssh, "ss -tlnp 2>/dev/null")
    for line in out.split("\n"):
        if any(p in line for p in ["3000", "8000", "8003", "5678", "3100"]):
            print(line)

    # Check Docker port mappings
    print("\n=== DOCKER PORT MAPPINGS ===")
    out, _ = run_sudo(ssh, "docker ps --format '{{.Names}}: {{.Ports}}'")
    print(out)

    # Test local curl from VM
    print("\n=== TESTING LOCALHOST ACCESS FROM VM ===")
    endpoints = [
        ("Website", "http://localhost:3000"),
        ("MINDEX", "http://localhost:8000/api/mindex/health"),
        ("MycoBrain", "http://localhost:8003/health"),
    ]
    
    for name, url in endpoints:
        stdin, stdout, stderr = ssh.exec_command(f"curl -s -o /dev/null -w '%{{http_code}}' {url} 2>/dev/null || echo FAIL")
        code = stdout.read().decode().strip()
        print(f"  {name}: {code}")

    # Test static file
    print("\n=== TESTING STATIC FILE ===")
    stdin, stdout, stderr = ssh.exec_command("curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/_next/static/css/5160586124011305.css")
    print(f"  Static CSS: {stdout.read().decode().strip()}")

    ssh.close()

if __name__ == "__main__":
    main()
