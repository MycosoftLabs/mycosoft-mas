#!/usr/bin/env python3
"""Check MycoBrain status on VM and Windows PC."""

import paramiko
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except:
    pass

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "REDACTED_VM_SSH_PASSWORD"
WINDOWS_IP = "192.168.0.172"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=30)

print("=" * 60)
print("MYCOBRAIN STATUS CHECK")
print("=" * 60)

# Check Docker containers
print("\n[1] MycoBrain Docker containers on VM:")
stdin, stdout, stderr = ssh.exec_command('docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -i mycobrain')
result = stdout.read().decode()
print(result if result.strip() else "   None running")

# Check localhost:8003 on VM
print("\n[2] VM localhost:8003 (MycoBrain container):")
stdin, stdout, stderr = ssh.exec_command('curl -sf http://localhost:8003/health || echo "FAILED - not running"')
result = stdout.read().decode()
print(f"   {result.strip()}")

# Check Windows PC:18003 from VM
print(f"\n[3] VM -> Windows PC ({WINDOWS_IP}:18003):")
stdin, stdout, stderr = ssh.exec_command(f'curl -sf http://{WINDOWS_IP}:18003/health || echo "FAILED - not reachable"')
result = stdout.read().decode()
print(f"   {result.strip()}")

# Check Cloudflared routes
print("\n[4] Cloudflared running config (routes to 8003 or 18003):")
stdin, stdout, stderr = ssh.exec_command('cat ~/.cloudflared/config.yml | grep -E "8003|18003|192.168.0.172|mycobrain" | head -10')
result = stdout.read().decode()
print(result if result.strip() else "   No matching routes in config.yml")

# Check cloudflared process
print("\n[5] Cloudflared process (token vs config):")
stdin, stdout, stderr = ssh.exec_command('ps aux | grep -E "[c]loudflared" | head -2')
result = stdout.read().decode()
if "--token" in result:
    print("   Running with --token (Dashboard managed)")
elif "--config" in result:
    print("   Running with config file")
else:
    print(f"   Process: {result.strip()[:100]}")

ssh.close()

print("\n" + "=" * 60)
print("RECOMMENDATIONS")
print("=" * 60)
print("""
The Cloudflare tunnel is running with --token (dashboard-managed routes).
To fix MycoBrain on sandbox:

OPTION A: Update Cloudflare Dashboard
1. Go to: https://one.dash.cloudflare.com/
2. Navigate to: Zero Trust > Networks > Tunnels
3. Find the tunnel for sandbox.mycosoft.com
4. Edit the route for brain-sandbox.mycosoft.com
5. Change from: http://localhost:8003
6. Change to: http://192.168.0.172:18003

OPTION B: Reconfigure to use local config.yml
1. SSH to VM: ssh mycosoft@192.168.0.187
2. Stop current tunnel: sudo systemctl stop cloudflared
3. Edit systemd service to use config file instead of token
4. Restart: sudo systemctl start cloudflared
""")
