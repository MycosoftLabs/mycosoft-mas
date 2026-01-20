#!/usr/bin/env python3
"""Fix Cloudflare tunnel routing for MycoBrain"""

import paramiko
import yaml
from io import StringIO

vm_ip = '192.168.0.187'
vm_user = 'mycosoft'
vm_password = 'Mushroom1!Mushroom1!'
mycobrain_lan_host = "192.168.0.172"
mycobrain_lan_port = "18003"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(vm_ip, username=vm_user, password=vm_password)

print("Fixing Cloudflare MycoBrain routes...")

# Read current config
stdin, stdout, stderr = ssh.exec_command('cat ~/.cloudflared/config.yml')
config_str = stdout.read().decode()
config = yaml.safe_load(StringIO(config_str))

print(f"Current ingress rules: {len(config.get('ingress', []))}")

# Remove all MycoBrain routes
config['ingress'] = [
    r for r in config.get('ingress', [])
    if not (isinstance(r, dict) and '8003' in str(r.get('service', '')))
]

# Find catch-all index
catch_idx = len(config['ingress'])
for i, r in enumerate(config['ingress']):
    if isinstance(r, dict) and str(r.get('service', '')).startswith('http_status'):
        catch_idx = i
        break

# Insert MycoBrain routes BEFORE catch-all (more specific first)
mycobrain_routes = [
    # Route sandbox API requests to the Windows MycoBrain service on the LAN.
    # This enables real board/COM telemetry without running MycoBrain inside the VM.
    {"hostname": "sandbox.mycosoft.com", "service": f"http://{mycobrain_lan_host}:{mycobrain_lan_port}", "path": "/api/mycobrain/*"},
    {"hostname": "sandbox.mycosoft.com", "service": f"http://{mycobrain_lan_host}:{mycobrain_lan_port}", "path": "/api/mycobrain"},
]

config['ingress'] = (
    config['ingress'][:catch_idx] +
    mycobrain_routes +
    config['ingress'][catch_idx:]
)

# Write updated config
config_yaml = yaml.dump(config, default_flow_style=False, sort_keys=False)
stdin, stdout, stderr = ssh.exec_command('cat > /tmp/cf_fixed.yml << \'CFEOF\'\n' + config_yaml + '\nCFEOF')
stdout.read()

stdin, stdout, stderr = ssh.exec_command('cp ~/.cloudflared/config.yml ~/.cloudflared/config.yml.backup2 && mv /tmp/cf_fixed.yml ~/.cloudflared/config.yml')
stdout.read()

# Restart tunnel
stdin, stdout, stderr = ssh.exec_command(f'echo "{vm_password}" | sudo -S systemctl restart cloudflared')
stdout.read()

print("[OK] Cloudflare config updated and tunnel restarted")
print(f"   Added {len(mycobrain_routes)} MycoBrain routes")

ssh.close()
