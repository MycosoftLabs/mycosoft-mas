#!/usr/bin/env python3
"""Check cloudflared logs and fix the issue."""

import paramiko
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except:
    pass

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "REDACTED_VM_SSH_PASSWORD"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=30)

def run_sudo(cmd):
    full_cmd = f"echo '{VM_PASSWORD}' | sudo -S {cmd}"
    stdin, stdout, stderr = ssh.exec_command(full_cmd)
    return stdout.read().decode(), stderr.read().decode()

print("=" * 70)
print("CLOUDFLARED LOGS AND FIX")
print("=" * 70)

# Check logs
print("\n[1] Cloudflared logs:")
stdout, stderr = run_sudo("journalctl -u cloudflared -n 30 --no-pager")
print(stdout)

# Check config.yml content
print("\n[2] Current config.yml:")
stdin, stdout, stderr = ssh.exec_command('cat ~/.cloudflared/config.yml')
config = stdout.read().decode()
print(config)

# The issue is that config-based mode requires a credentials-file
# Let's revert to token mode but modify the ingress rules in Cloudflare Dashboard
print("\n[3] Reverting to token mode (dashboard-managed):")
print("   Since config mode requires credentials file, we need to use token mode")
print("   and update routes in Cloudflare Dashboard")

# Restore the token-based service
stdout, stderr = run_sudo("cp /etc/systemd/system/cloudflared.service.bak.token /etc/systemd/system/cloudflared.service 2>/dev/null || true")
stdout, stderr = run_sudo("systemctl daemon-reload")
stdout, stderr = run_sudo("systemctl restart cloudflared")

import time
time.sleep(3)

# Verify it's running
stdout, stderr = run_sudo("systemctl status cloudflared --no-pager | head -10")
print("\n[4] Cloudflared status after revert:")
print(stdout)

ssh.close()

print("\n" + "=" * 70)
print("ACTION REQUIRED: UPDATE CLOUDFLARE DASHBOARD")
print("=" * 70)
print("""
The cloudflared service is running with --token (dashboard-managed routes).
To fix MycoBrain routing, you need to update the Cloudflare Dashboard:

1. Go to: https://one.dash.cloudflare.com/
2. Navigate to: Zero Trust > Networks > Tunnels
3. Find tunnel: bd385313-a44a-47ae-8f8a-581608118127
4. Click "Configure"
5. Find the route for "brain-sandbox.mycosoft.com"
6. Change Service from: http://localhost:8003
7. Change Service to: http://192.168.0.172:18003

This routes MycoBrain requests from the tunnel to your Windows dev PC.

Alternatively, add a new ingress rule:
   Hostname: sandbox.mycosoft.com
   Path: /api/mycobrain/*
   Service: http://192.168.0.172:18003
""")
