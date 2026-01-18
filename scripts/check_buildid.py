#!/usr/bin/env python3
"""Check Next.js build ID"""

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

    # Check BUILD_ID
    print("\n=== BUILD ID ===")
    out, _ = run_sudo(ssh, "docker exec mycosoft-website cat /app/.next/BUILD_ID 2>&1")
    print(f"Build ID: {out.strip()}")

    # Check static folder name
    print("\n=== STATIC FOLDER NAME ===")
    out, _ = run_sudo(ssh, "docker exec mycosoft-website ls /app/.next/static 2>&1")
    print(f"Static folders: {out.strip()}")

    # The static folder should have a folder matching BUILD_ID
    # Check what files are being requested vs what exists
    print("\n=== CHECKING CSS FILE ===")
    out, _ = run_sudo(ssh, "docker exec mycosoft-website ls /app/.next/static/css/ 2>&1")
    print(f"CSS files: {out.strip()}")

    print("\n=== CHECKING CHUNKS ===")
    out, _ = run_sudo(ssh, "docker exec mycosoft-website ls /app/.next/static/chunks/ 2>&1")
    print(out[:500])

    ssh.close()

if __name__ == "__main__":
    main()
