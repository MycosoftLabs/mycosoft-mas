#!/usr/bin/env python3
"""Set up Cloudflare tunnel for MycoBrain service on VM."""

import paramiko
import yaml
from io import StringIO

vm_ip = '192.168.0.187'
vm_user = 'mycosoft'
vm_password = 'REDACTED_VM_SSH_PASSWORD'

print("=" * 80)
print("SETTING UP CLOUDFLARE TUNNEL FOR MYCOBRAIN")
print("=" * 80)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(vm_ip, username=vm_user, password=vm_password)

# 1. Check current Cloudflare config
print("\n1. Checking current Cloudflare tunnel configuration...")
print("-" * 80)

stdin, stdout, stderr = ssh.exec_command('cat ~/.cloudflared/config.yml 2>/dev/null || echo "File not found"')
current_config = stdout.read().decode()

if "File not found" in current_config:
    print("   [INFO] No existing Cloudflare config found. Will create new one.")
    current_config = ""
else:
    print("   [OK] Found existing config file")
    print(f"   Current config length: {len(current_config)} bytes")

# 2. Parse existing config or create new
if current_config and "File not found" not in current_config:
    try:
        config = yaml.safe_load(StringIO(current_config))
    except:
        print("   [WARNING] Could not parse YAML, will create new config")
        config = {"tunnel": "", "credentials-file": ""}
else:
    config = {"tunnel": "", "credentials-file": ""}

# 3. Check if MycoBrain route already exists
print("\n2. Checking for existing MycoBrain routes...")
print("-" * 80)

has_mycobrain = False
if "ingress" in config:
    for ingress in config["ingress"]:
        if isinstance(ingress, dict) and "service" in ingress:
            if "8003" in str(ingress["service"]) or "mycobrain" in str(ingress["service"]).lower():
                has_mycobrain = True
                print(f"   [FOUND] Existing MycoBrain route: {ingress}")

if not has_mycobrain:
    print("   [INFO] No MycoBrain route found. Will add one.")

# 4. Prepare new config with MycoBrain routes
print("\n3. Preparing Cloudflare tunnel configuration...")
print("-" * 80)

# Get tunnel ID and credentials file from existing config if available
tunnel_id = config.get("tunnel", "")
credentials_file = config.get("credentials-file", "")

# If no tunnel ID, we'll need to create one (user will need to do this manually)
if not tunnel_id:
    print("   [WARNING] No tunnel ID found in config.")
    print("   [INFO] You'll need to create a Cloudflare tunnel first:")
    print("   1. Run: cloudflared tunnel create mycobrain-tunnel")
    print("   2. Copy the tunnel ID that's output")
    print("   3. Run this script again with the tunnel ID")

# Create ingress rules
ingress_rules = [
    {
        "hostname": "sandbox.mycosoft.com",
        "service": "http://localhost:8003",
        "path": "/api/mycobrain"
    },
    {
        "hostname": "sandbox.mycosoft.com",
        "service": "http://localhost:8003",
        "path": "/api/mycobrain/*"
    },
    {
        "service": "http_status:404"
    }
]

# If config already has ingress, merge with existing
if "ingress" in config and isinstance(config["ingress"], list):
    # Remove any existing MycoBrain routes
    config["ingress"] = [
        rule for rule in config["ingress"]
        if not (isinstance(rule, dict) and "service" in rule and "8003" in str(rule.get("service", "")))
    ]
    # Add new MycoBrain routes at the beginning (more specific routes first)
    config["ingress"] = ingress_rules[:-1] + config["ingress"] + [ingress_rules[-1]]
else:
    config["ingress"] = ingress_rules

# Ensure tunnel and credentials-file are set
if tunnel_id:
    config["tunnel"] = tunnel_id
if credentials_file:
    config["credentials-file"] = credentials_file

# 5. Write new config
print("\n4. Writing updated Cloudflare tunnel configuration...")
print("-" * 80)

new_config_yaml = yaml.dump(config, default_flow_style=False, sort_keys=False)
print("   New config:")
print("-" * 40)
print(new_config_yaml)
print("-" * 40)

# Save to temp file first, then move to final location
stdin, stdout, stderr = ssh.exec_command('cat > /tmp/cloudflared_config.yml << \'EOF\'\n' + new_config_yaml + '\nEOF')
stdout.read()  # Wait for command to complete

# Backup existing config
stdin, stdout, stderr = ssh.exec_command('mkdir -p ~/.cloudflared && if [ -f ~/.cloudflared/config.yml ]; then cp ~/.cloudflared/config.yml ~/.cloudflared/config.yml.backup; fi')
stdout.read()

# Move new config to final location
stdin, stdout, stderr = ssh.exec_command('mv /tmp/cloudflared_config.yml ~/.cloudflared/config.yml')
stdout.read()

print("   [OK] Configuration file written to ~/.cloudflared/config.yml")
print("   [OK] Backup saved to ~/.cloudflared/config.yml.backup")

# 6. Restart cloudflared service
print("\n5. Restarting Cloudflare tunnel service...")
print("-" * 80)

stdin, stdout, stderr = ssh.exec_command('sudo systemctl restart cloudflared || sudo service cloudflared restart || echo "Service restart attempted"')
result = stdout.read().decode()
print(f"   Result: {result.strip() or 'Service restart attempted'}")

# 7. Check service status
print("\n6. Checking Cloudflare tunnel service status...")
print("-" * 80)

stdin, stdout, stderr = ssh.exec_command('sudo systemctl status cloudflared --no-pager -l || sudo service cloudflared status || echo "Could not check status"')
status = stdout.read().decode()
print(status[:500])  # First 500 chars

ssh.close()

print("\n" + "=" * 80)
print("CLOUDFLARE TUNNEL SETUP COMPLETE")
print("=" * 80)
print("\nNext steps:")
print("1. Verify tunnel is running: sudo systemctl status cloudflared")
print("2. Test MycoBrain endpoint: curl https://sandbox.mycosoft.com/api/mycobrain/health")
print("3. Check tunnel logs: sudo journalctl -u cloudflared -f")
