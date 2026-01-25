#!/usr/bin/env python3
"""Switch cloudflared from token mode to config file mode.

This allows the local config.yml routes to be used, which includes
the MycoBrain route to the Windows PC (192.168.0.172:18003).
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
VM_PASSWORD = "Mushroom1!Mushroom1!"

print("=" * 70)
print("SWITCHING CLOUDFLARED TO CONFIG FILE MODE")
print("=" * 70)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=30)

def run_sudo(cmd):
    """Run command with sudo using password."""
    full_cmd = f"echo '{VM_PASSWORD}' | sudo -S {cmd}"
    stdin, stdout, stderr = ssh.exec_command(full_cmd)
    return stdout.read().decode(), stderr.read().decode()

# Step 1: Check current systemd service
print("\n[1] Current cloudflared systemd service:")
stdout, stderr = run_sudo("cat /etc/systemd/system/cloudflared.service")
print(stdout[:500] if stdout else "Not found")

# Step 2: Get tunnel ID from config.yml
print("\n[2] Getting tunnel info from existing config:")
stdin, stdout, stderr = ssh.exec_command('cat ~/.cloudflared/config.yml | head -5')
config_head = stdout.read().decode()
print(config_head)

# Extract tunnel ID if present
tunnel_id = None
for line in config_head.split('\n'):
    if line.startswith('tunnel:'):
        tunnel_id = line.split(':')[1].strip()
        break

if tunnel_id and tunnel_id != "PLACEHOLDER_TUNNEL_ID":
    print(f"   Found tunnel ID: {tunnel_id}")
else:
    print("   WARNING: Tunnel ID is placeholder or missing")
    print("   Need to get actual tunnel ID from running process or dashboard")

# Step 3: Find credentials file
print("\n[3] Looking for credentials file:")
stdin, stdout, stderr = ssh.exec_command('ls -la ~/.cloudflared/*.json 2>/dev/null || echo "No JSON files found"')
creds = stdout.read().decode()
print(creds)

# Step 4: Check what token-based tunnel ID is being used
print("\n[4] Extracting tunnel ID from running token:")
stdin, stdout, stderr = ssh.exec_command("ps aux | grep '[c]loudflared' | grep -oE 'token [^ ]+' | head -1")
token_part = stdout.read().decode().strip()
if token_part:
    print(f"   Token found in process: {token_part[:50]}...")
    # The token is base64 encoded JSON with tunnel info
    import base64
    import json
    try:
        token = token_part.split()[1] if ' ' in token_part else token_part.replace('token ', '')
        # Token has 3 parts: accountId, tunnelId, secret
        decoded = base64.b64decode(token + '==').decode('utf-8', errors='replace')
        token_data = json.loads(decoded)
        actual_tunnel_id = token_data.get('t', 'unknown')
        print(f"   Actual tunnel ID from token: {actual_tunnel_id}")
    except Exception as e:
        print(f"   Could not decode token: {e}")
        actual_tunnel_id = None

# Step 5: Create new systemd service that uses config file
print("\n[5] Creating new systemd service with config file:")

new_service = '''[Unit]
Description=Cloudflare Tunnel (config.yml)
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=notify
ExecStart=/usr/bin/cloudflared --no-autoupdate tunnel run
Restart=on-failure
RestartSec=5s
User=root
WorkingDirectory=/home/mycosoft/.cloudflared

[Install]
WantedBy=multi-user.target
'''

# First backup the current service
stdout, stderr = run_sudo('cp /etc/systemd/system/cloudflared.service /etc/systemd/system/cloudflared.service.bak.token 2>/dev/null || true')

# Write new service file
escaped_service = new_service.replace('\n', '\\n')
stdout, stderr = run_sudo(f'echo -e "{escaped_service}" > /tmp/cloudflared.service')
stdout, stderr = run_sudo('cp /tmp/cloudflared.service /etc/systemd/system/cloudflared.service')

# Reload systemd
stdout, stderr = run_sudo('systemctl daemon-reload')
print("   Systemd daemon reloaded")

# Step 6: Check if config.yml has proper tunnel ID
print("\n[6] Checking config.yml tunnel ID:")
stdin, stdout, stderr = ssh.exec_command('grep "^tunnel:" ~/.cloudflared/config.yml')
tunnel_line = stdout.read().decode().strip()
print(f"   {tunnel_line}")

if "PLACEHOLDER" in tunnel_line.upper():
    print("   WARNING: Config has placeholder tunnel ID!")
    print("   We need to update it with the actual tunnel ID from the token")
    
    if actual_tunnel_id:
        print(f"\n   Updating config.yml with tunnel ID: {actual_tunnel_id}")
        # Update the config file
        stdin, stdout, stderr = ssh.exec_command(f"sed -i 's/^tunnel:.*/tunnel: {actual_tunnel_id}/' ~/.cloudflared/config.yml")
        stdout.read()
        print("   Config updated!")
        
        # Verify update
        stdin, stdout, stderr = ssh.exec_command('grep "^tunnel:" ~/.cloudflared/config.yml')
        new_tunnel_line = stdout.read().decode().strip()
        print(f"   New tunnel line: {new_tunnel_line}")

# Step 7: Restart cloudflared
print("\n[7] Restarting cloudflared service:")
stdout, stderr = run_sudo('systemctl restart cloudflared')
time.sleep(3)

# Step 8: Check new status
print("\n[8] Checking new status:")
stdout, stderr = run_sudo('systemctl status cloudflared --no-pager | head -15')
print(stdout)

# Step 9: Verify routes work
print("\n[9] Testing routes:")
stdin, stdout, stderr = ssh.exec_command('curl -sf http://192.168.0.172:18003/health')
windows_result = stdout.read().decode()
print(f"   Windows MycoBrain: {windows_result.strip()}")

ssh.close()

print("\n" + "=" * 70)
print("CLOUDFLARED SWITCHED TO CONFIG FILE MODE")
print("=" * 70)
print("""
Next steps:
1. Test: curl https://sandbox.mycosoft.com/api/mycobrain/health
2. If working, the sandbox website should show MycoBrain data
3. If not, check: journalctl -u cloudflared -f
""")
