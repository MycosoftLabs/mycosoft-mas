#!/usr/bin/env python3
"""Install socat and set up the MycoBrain proxy correctly."""

import paramiko
import sys
import time

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except:
    pass

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "Mushroom1!Mushroom1!"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=30)

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    return stdout.read().decode(), stderr.read().decode()

def run_sudo(cmd):
    full_cmd = f"echo '{VM_PASSWORD}' | sudo -S bash -c \"{cmd}\""
    stdin, stdout, stderr = ssh.exec_command(full_cmd)
    return stdout.read().decode(), stderr.read().decode()

print("=" * 60)
print("FIXING SOCAT INSTALLATION")
print("=" * 60)

# Check if socat exists
print("\n[1] Checking socat:")
stdout, stderr = run("which socat")
print(f"   Path: {stdout.strip() if stdout.strip() else 'NOT FOUND'}")

# Install socat
print("\n[2] Installing socat:")
stdout, stderr = run_sudo("apt-get update -qq && apt-get install -y socat")
print(f"   Install output: {stdout[-200:] if len(stdout) > 200 else stdout}")

# Verify installation
print("\n[3] Verifying socat:")
stdout, stderr = run("which socat && socat -V | head -1")
print(f"   {stdout.strip()}")

# Restart the proxy service
print("\n[4] Restarting mycobrain-proxy service:")
stdout, stderr = run_sudo("systemctl restart mycobrain-proxy")
time.sleep(2)

# Check status
print("\n[5] Service status:")
stdout, stderr = run_sudo("systemctl status mycobrain-proxy --no-pager | head -15")
print(stdout)

# Test the proxy
print("\n[6] Testing proxy:")
stdout, stderr = run("curl -sf http://localhost:8003/health || echo 'FAILED'")
print(f"   Result: {stdout.strip()}")

ssh.close()

print("\n" + "=" * 60)
