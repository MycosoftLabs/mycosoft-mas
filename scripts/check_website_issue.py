#!/usr/bin/env python3
"""Check website container issues"""

import paramiko
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "REDACTED_VM_SSH_PASSWORD"

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

    # Check container logs
    print("\n=== WEBSITE CONTAINER LOGS ===")
    out, _ = run_sudo(ssh, "docker logs mycosoft-website --tail 50 2>&1")
    # Print last 30 lines safely
    lines = out.split("\n")[-30:]
    for line in lines:
        print(line)

    # Check if static files exist in container
    print("\n=== CHECKING STATIC FILES IN CONTAINER ===")
    out, _ = run_sudo(ssh, "docker exec mycosoft-website ls -la /app/.next/static 2>&1")
    print(out[:500])

    # Check container image details
    print("\n=== CONTAINER IMAGE DETAILS ===")
    out, _ = run_sudo(ssh, "docker inspect mycosoft-website --format '{{.Config.Image}}'")
    print(f"Image: {out.strip()}")

    out, _ = run_sudo(ssh, "docker inspect mycosoft-website --format '{{.Config.WorkingDir}}'")
    print(f"Working Dir: {out.strip()}")

    # Check what's in the container
    print("\n=== FILES IN CONTAINER /app ===")
    out, _ = run_sudo(ssh, "docker exec mycosoft-website ls -la /app 2>&1")
    print(out[:800])

    ssh.close()

if __name__ == "__main__":
    main()
