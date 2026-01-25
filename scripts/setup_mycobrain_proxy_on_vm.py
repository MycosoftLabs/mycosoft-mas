#!/usr/bin/env python3
"""Set up a simple proxy on the VM that forwards MycoBrain requests to Windows PC.

Since the Cloudflare tunnel routes brain-sandbox.mycosoft.com to localhost:8003,
we'll run a simple proxy on port 8003 that forwards to the Windows PC at 192.168.0.172:18003.
"""

import paramiko
import sys
import time

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except:
    pass

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "REDACTED_VM_SSH_PASSWORD"
WINDOWS_IP = "192.168.0.172"
WINDOWS_PORT = "18003"
PROXY_PORT = "8003"

print("=" * 70)
print("SETTING UP MYCOBRAIN PROXY ON VM")
print("=" * 70)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=30)

def run_sudo(cmd):
    full_cmd = f"echo '{VM_PASSWORD}' | sudo -S {cmd}"
    stdin, stdout, stderr = ssh.exec_command(full_cmd)
    return stdout.read().decode(), stderr.read().decode()

# Step 1: Check if anything is on port 8003
print(f"\n[1] Checking port {PROXY_PORT} on VM:")
stdin, stdout, stderr = ssh.exec_command(f'ss -tlnp | grep ":{PROXY_PORT}" || echo "Port is free"')
result = stdout.read().decode()
print(f"   {result.strip()}")

# Step 2: Create a simple socat proxy (TCP forwarder)
print(f"\n[2] Installing socat for TCP forwarding:")
stdout, stderr = run_sudo("apt-get update && apt-get install -y socat 2>/dev/null")
print("   socat installed (or already present)")

# Step 3: Kill any existing proxy on port 8003
print(f"\n[3] Killing any existing process on port {PROXY_PORT}:")
stdout, stderr = run_sudo(f"fuser -k {PROXY_PORT}/tcp 2>/dev/null || true")
print("   Cleared")

# Step 4: Create systemd service for the proxy
print(f"\n[4] Creating MycoBrain proxy systemd service:")

proxy_service = f'''[Unit]
Description=MycoBrain TCP Proxy (VM -> Windows PC)
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/socat TCP-LISTEN:{PROXY_PORT},fork,reuseaddr TCP:{WINDOWS_IP}:{WINDOWS_PORT}
Restart=always
RestartSec=3
User=root

[Install]
WantedBy=multi-user.target
'''

# Write the service file
stdin, stdout, stderr = ssh.exec_command(f'''cat > /tmp/mycobrain-proxy.service << 'EOF'
{proxy_service}
EOF''')
stdout.read()

stdout, stderr = run_sudo("mv /tmp/mycobrain-proxy.service /etc/systemd/system/mycobrain-proxy.service")
stdout, stderr = run_sudo("systemctl daemon-reload")
stdout, stderr = run_sudo("systemctl enable mycobrain-proxy")
stdout, stderr = run_sudo("systemctl restart mycobrain-proxy")
print("   Service created and started")

time.sleep(2)

# Step 5: Verify proxy is running
print(f"\n[5] Verifying proxy status:")
stdout, stderr = run_sudo("systemctl status mycobrain-proxy --no-pager | head -12")
print(stdout)

# Step 6: Test the proxy
print(f"\n[6] Testing proxy (VM localhost:{PROXY_PORT} -> Windows {WINDOWS_IP}:{WINDOWS_PORT}):")
stdin, stdout, stderr = ssh.exec_command(f'curl -sf http://localhost:{PROXY_PORT}/health || echo "FAILED"')
result = stdout.read().decode()
print(f"   Result: {result.strip()}")

ssh.close()

print("\n" + "=" * 70)
print("MYCOBRAIN PROXY SETUP COMPLETE")
print("=" * 70)
print(f"""
Architecture:
   browser -> sandbox.mycosoft.com/api/mycobrain/*
           -> Cloudflare Tunnel -> VM:3000 (website)
           -> /api/mycobrain/* -> VM:8003 (proxy)
           -> Windows:18003 (MycoBrain service with COM7 device)

OR:
   browser -> brain-sandbox.mycosoft.com
           -> Cloudflare Tunnel -> VM:8003 (proxy)
           -> Windows:18003 (MycoBrain service with COM7 device)

Next: Test with curl https://brain-sandbox.mycosoft.com/health
""")
