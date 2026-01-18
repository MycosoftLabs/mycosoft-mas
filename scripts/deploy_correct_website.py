#!/usr/bin/env python3
"""Deploy the correct website image"""

import paramiko
import time
import sys
import io

# Force UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "REDACTED_VM_SSH_PASSWORD"

def run_sudo(ssh, cmd):
    full_cmd = f"echo '{VM_PASSWORD}' | sudo -S {cmd}"
    stdin, stdout, stderr = ssh.exec_command(full_cmd, timeout=300)
    out = stdout.read().decode(errors='replace')
    err = stderr.read().decode(errors='replace')
    err_clean = "\n".join([l for l in err.split("\n") if "password" not in l.lower() and l.strip()])
    return out, err_clean

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=30)
    print("Connected!")

    # Step 1: Stop and remove current website
    print("\n1. Stopping current website...")
    run_sudo(ssh, "docker stop mycosoft-website 2>/dev/null || true")
    run_sudo(ssh, "docker rm mycosoft-website 2>/dev/null || true")
    print("   Done")

    # Step 2: Tag the correct image as website-website
    print("\n2. Tagging correct image...")
    out, err = run_sudo(ssh, "docker tag mycosoft-always-on-mycosoft-website:latest website-website:latest")
    print(f"   {out or 'Tagged'}")
    if err:
        print(f"   Error: {err}")

    # Step 3: Restart using docker compose
    print("\n3. Starting website container...")
    out, err = run_sudo(ssh, "sh -c 'cd /opt/mycosoft && docker compose up -d mycosoft-website'")
    if err:
        # Just print first few lines
        lines = err.split("\n")[:10]
        for l in lines:
            print(f"   {l}")
    
    # Wait for startup
    print("\n4. Waiting 30 seconds for website to start...")
    time.sleep(30)

    # Step 4: Check status
    print("\n5. Checking website status...")
    out, _ = run_sudo(ssh, "docker ps --format '{{.Names}} {{.Image}} {{.Status}}' | head -5")
    for line in out.split("\n"):
        if line.strip():
            print(f"   {line}")

    # Step 5: Test endpoint
    print("\n6. Testing website endpoint...")
    stdin, stdout, stderr = ssh.exec_command("curl -s -o /dev/null -w '%{http_code}' --connect-timeout 10 http://localhost:3000")
    code = stdout.read().decode().strip()
    print(f"   HTTP Status: {code}")

    if code == "200":
        print("\n   SUCCESS! Website is running!")
    else:
        # Check logs
        print("\n   Checking logs...")
        out, _ = run_sudo(ssh, "docker logs mycosoft-website --tail 10 2>&1")
        lines = out.split("\n")[:10]
        for l in lines:
            print(f"   {l}")

    ssh.close()

if __name__ == "__main__":
    main()
