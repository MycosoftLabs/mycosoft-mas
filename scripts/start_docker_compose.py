#!/usr/bin/env python3
"""Start docker compose on VM"""

import paramiko
import time

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "Mushroom1!Mushroom1!"

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=30)
    print("Connected!")

    # Run docker compose with proper syntax using sh -c
    print("Starting docker compose...")
    cmd = f"echo '{VM_PASSWORD}' | sudo -S sh -c 'cd /opt/mycosoft ; docker compose up -d'"
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=300)
    out = stdout.read().decode()
    err = stderr.read().decode()
    print("Output:", out)
    
    # Filter out password noise
    err_lines = [l for l in err.split("\n") if "password" not in l.lower() and l.strip()]
    if err_lines:
        print("Errors:", "\n".join(err_lines))

    # Wait
    print("\nWaiting 30 seconds...")
    time.sleep(30)

    # Check containers
    print("\nRunning containers:")
    cmd = f"echo '{VM_PASSWORD}' | sudo -S docker ps --format 'table {{{{.Names}}}}\\t{{{{.Status}}}}\\t{{{{.Ports}}}}'"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    print(stdout.read().decode())

    # Test endpoints
    print("\nTesting endpoints:")
    endpoints = [
        ("Website", "localhost:3000"),
        ("MINDEX", "localhost:8000"),
        ("MycoBrain", "localhost:8003"),
        ("n8n", "localhost:5678"),
        ("MYCA Dashboard", "localhost:3100"),
    ]
    
    for name, url in endpoints:
        stdin, stdout, stderr = ssh.exec_command(f"curl -s -o /dev/null -w '%{{http_code}}' http://{url} 2>/dev/null || echo 'FAIL'")
        code = stdout.read().decode().strip()
        status = "OK" if code in ["200", "301", "302", "304"] else code
        print(f"  {name}: {status}")

    ssh.close()
    print("\nDone!")

if __name__ == "__main__":
    main()
