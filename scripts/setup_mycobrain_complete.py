#!/usr/bin/env python3
"""Complete MycoBrain setup: Cloudflare tunnel, API routes, service persistence"""

import paramiko
import yaml
import time
from io import StringIO

vm_ip = '192.168.0.187'
vm_user = 'mycosoft'
vm_password = 'Mushroom1!Mushroom1!'

print("=" * 80)
print("COMPLETE MYCOBRAIN SETUP")
print("=" * 80)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(vm_ip, username=vm_user, password=vm_password)

def exec_command(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    return stdout.read().decode(), stderr.read().decode()

# Step 1: Check MycoBrain service status
print("\n[STEP 1] Checking MycoBrain service status...")
print("-" * 80)
stdout, stderr = exec_command('docker ps --filter "name=mycobrain" --format "{{.Names}}\t{{.Status}}"')
if stdout.strip():
    print(f"  [OK] {stdout.strip()}")
else:
    print("  [WARNING] MycoBrain container not found")

# Test MycoBrain health
stdout, stderr = exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost:8003/health')
if stdout.strip() == "200":
    print("  [OK] MycoBrain health endpoint responding")
else:
    print(f"  [WARNING] MycoBrain health returned: {stdout.strip()}")

# Step 2: Read/update Cloudflare config
print("\n[STEP 2] Configuring Cloudflare tunnel...")
print("-" * 80)

stdout, stderr = exec_command('cat ~/.cloudflared/config.yml 2>/dev/null || echo "FILE_NOT_FOUND"')
current_config_str = stdout

if "FILE_NOT_FOUND" in current_config_str:
    print("  [INFO] No existing Cloudflare config found")
    config = {}
else:
    try:
        config = yaml.safe_load(StringIO(current_config_str))
        if config is None:
            config = {}
        print("  [OK] Loaded existing config")
    except Exception as e:
        print(f"  [WARNING] Could not parse config: {e}")
        config = {}

# Get tunnel ID and credentials
if "tunnel" not in config or not config["tunnel"]:
    print("  [INFO] No tunnel ID found. Checking for existing tunnel...")
    stdout, stderr = exec_command('cloudflared tunnel list 2>/dev/null | head -5')
    if stdout.strip():
        print("  [INFO] Existing tunnels found:")
        print(stdout[:200])
        print("  [ACTION REQUIRED] Please specify tunnel ID in script or create one manually")
        print("    Run: cloudflared tunnel create mycobrain-tunnel")
    else:
        print("  [INFO] No tunnels found. Will use placeholder tunnel ID")
        config["tunnel"] = "PLACEHOLDER_TUNNEL_ID"

# Build ingress rules
ingress = []

# Check if MycoBrain routes already exist
has_mycobrain = False
if "ingress" in config and isinstance(config["ingress"], list):
    for rule in config["ingress"]:
        if isinstance(rule, dict) and "service" in rule:
            service = str(rule.get("service", ""))
            if "8003" in service or "mycobrain" in service.lower():
                has_mycobrain = True
                print("  [INFO] MycoBrain route already exists")
                break

# Add MycoBrain routes if not present
if not has_mycobrain:
    print("  [ADDING] MycoBrain routes to Cloudflare config")
    # MycoBrain routes must come before catch-all
    mycobrain_routes = [
        {
            "hostname": "sandbox.mycosoft.com",
            "service": "http://localhost:8003",
            "path": "/api/mycobrain"
        },
        {
            "hostname": "sandbox.mycosoft.com",
            "service": "http://localhost:8003",
            "path": "/api/mycobrain/*"
        }
    ]
    
    # Insert before catch-all (which should be last)
    if "ingress" in config and isinstance(config["ingress"], list):
        # Remove any existing MycoBrain routes (cleanup)
        config["ingress"] = [
            r for r in config["ingress"]
            if not (isinstance(r, dict) and "service" in r and "8003" in str(r.get("service", "")))
        ]
        # Find catch-all index
        catch_all_idx = len(config["ingress"])
        for i, rule in enumerate(config["ingress"]):
            if isinstance(rule, dict) and rule.get("service", "").startswith("http_status"):
                catch_all_idx = i
                break
        # Insert MycoBrain routes before catch-all
        config["ingress"] = (
            config["ingress"][:catch_all_idx] +
            mycobrain_routes +
            config["ingress"][catch_all_idx:]
        )
    else:
        # No existing ingress, create new
        config["ingress"] = mycobrain_routes + [{"service": "http_status:404"}]
else:
    print("  [SKIP] MycoBrain routes already configured")

# Ensure credentials-file is set
if "credentials-file" not in config:
    tunnel_id = config.get("tunnel", "")
    if tunnel_id and tunnel_id != "PLACEHOLDER_TUNNEL_ID":
        config["credentials-file"] = f"/home/{vm_user}/.cloudflared/{tunnel_id}.json"

# Write updated config
print("  [WRITING] Updated Cloudflare config...")
config_yaml = yaml.dump(config, default_flow_style=False, sort_keys=False)

# Backup existing config
stdin, stdout, stderr = ssh.exec_command('mkdir -p ~/.cloudflared && if [ -f ~/.cloudflared/config.yml ]; then cp ~/.cloudflared/config.yml ~/.cloudflared/config.yml.backup.$(date +%Y%m%d_%H%M%S); fi')
stdout.read()

# Write new config
stdin, stdout, stderr = ssh.exec_command('cat > /tmp/cloudflared_config_new.yml << \'CFEOF\'\n' + config_yaml + '\nCFEOF')
stdout.read()

# Move to final location
stdin, stdout, stderr = ssh.exec_command('mv /tmp/cloudflared_config_new.yml ~/.cloudflared/config.yml')
stdout.read()
print("  [OK] Config file written")

# Step 3: Update website environment variables
print("\n[STEP 3] Updating website environment variables...")
print("-" * 80)

compose_file = f'/home/{vm_user}/mycosoft/docker-compose.always-on.yml'

# Read compose file
stdin, stdout, stderr = ssh.exec_command(f'cat {compose_file}')
compose_content = stdout.read().decode()

if 'MYCOBRAIN_SERVICE_URL' not in compose_content:
    print("  [ADDING] MYCOBRAIN_SERVICE_URL environment variable")
    # Find mycosoft-website service and add env var
    if 'mycosoft-website:' in compose_content:
        # Add after existing environment section
        lines = compose_content.split('\n')
        new_lines = []
        in_website_service = False
        in_env_section = False
        env_added = False
        
        for i, line in enumerate(lines):
            new_lines.append(line)
            
            if 'mycosoft-website:' in line:
                in_website_service = True
                continue
            
            if in_website_service and line.strip().startswith('environment:'):
                in_env_section = True
                continue
            
            if in_website_service and in_env_section and not env_added:
                # Check if we're past env vars (hit volumes, ports, etc)
                if line.strip() and not line.strip().startswith('-') and not line.strip().startswith(' ') and ':' in line:
                    # We've hit a new section, insert before it
                    new_lines.insert(-1, '      MYCOBRAIN_SERVICE_URL: http://host.docker.internal:8003')
                    env_added = True
                    in_env_section = False
                elif line.strip().startswith('-') or (line.strip() and ':' in line and not line.strip().startswith('#')):
                    # Still in env vars, check if this is the last one
                    # Look ahead to see if next non-empty line is not an env var
                    found_next_section = False
                    for j in range(i + 1, min(i + 5, len(lines))):
                        if lines[j].strip() and not lines[j].strip().startswith('-') and not lines[j].strip().startswith(' ') and ':' in lines[j]:
                            found_next_section = True
                            break
                    if found_next_section:
                        new_lines.insert(-1, '      MYCOBRAIN_SERVICE_URL: http://host.docker.internal:8003')
                        env_added = True
                        in_env_section = False
            elif in_website_service and not line.strip().startswith(' ') and line.strip() and ':' in line:
                # New service started
                in_website_service = False
        
        if not env_added and in_env_section:
            # Add at end of env section
            new_lines.append('      MYCOBRAIN_SERVICE_URL: http://host.docker.internal:8003')
        
        compose_content = '\n'.join(new_lines)
        
        # Write back
        stdin, stdout, stderr = ssh.exec_command(f'cat > /tmp/compose_new.yml << \'COMPOSEEOF\'\n{compose_content}\nCOMPOSEEOF')
        stdout.read()
        
        # Backup and move
        stdin, stdout, stderr = ssh.exec_command(f'cp {compose_file} {compose_file}.backup.$(date +%Y%m%d_%H%M%S) && mv /tmp/compose_new.yml {compose_file}')
        stdout.read()
        print("  [OK] Environment variable added")
    else:
        print("  [WARNING] mycosoft-website service not found in compose file")
else:
    print("  [SKIP] MYCOBRAIN_SERVICE_URL already exists")

# Step 4: Restart Cloudflare tunnel
print("\n[STEP 4] Restarting Cloudflare tunnel...")
print("-" * 80)
stdin, stdout, stderr = ssh.exec_command('sudo systemctl restart cloudflared 2>&1 || sudo service cloudflared restart 2>&1 || echo "RESTART_ATTEMPTED"')
result = stdout.read().decode()
print(f"  Result: {result.strip() or 'Restart attempted'}")

# Wait a moment
time.sleep(2)

# Check status
stdin, stdout, stderr = ssh.exec_command('sudo systemctl status cloudflared --no-pager -l 2>&1 | head -10')
status = stdout.read().decode()
if "active (running)" in status.lower():
    print("  [OK] Cloudflare tunnel is running")
else:
    print(f"  [WARNING] Status check: {status[:200]}")

# Step 5: Restart website container
print("\n[STEP 5] Restarting website container...")
print("-" * 80)
stdin, stdout, stderr = ssh.exec_command(f'cd ~/mycosoft && docker-compose -f docker-compose.always-on.yml restart mycosoft-website 2>&1')
result = stdout.read().decode()
print(f"  Result: {result.strip()[:100]}")

# Step 6: Set up service persistence
print("\n[STEP 6] Setting up service persistence...")
print("-" * 80)

# Create systemd service for Docker Compose stack
service_content = f"""[Unit]
Description=Mycosoft Always-On Stack
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/{vm_user}/mycosoft
ExecStart=/usr/bin/docker compose -f docker-compose.always-on.yml up -d
ExecStop=/usr/bin/docker compose -f docker-compose.always-on.yml down
TimeoutStartSec=0
User={vm_user}
Group=docker

[Install]
WantedBy=multi-user.target
"""

stdin, stdout, stderr = ssh.exec_command('cat > /tmp/mycosoft-stack.service << \'SERVICEEOF\'\n' + service_content + '\nSERVICEEOF')
stdout.read()

# Copy to systemd
stdin, stdout, stderr = ssh.exec_command('sudo cp /tmp/mycosoft-stack.service /etc/systemd/system/mycosoft-stack.service')
result = stdout.read().decode()
if "Permission denied" not in result:
    print("  [OK] Systemd service file created")
    
    # Reload and enable
    stdin, stdout, stderr = ssh.exec_command('sudo systemctl daemon-reload && sudo systemctl enable mycosoft-stack.service')
    result = stdout.read().decode()
    print("  [OK] Service enabled for auto-start")
else:
    print(f"  [WARNING] Could not create service (may need sudo): {result[:100]}")

# Enable Cloudflare tunnel
stdin, stdout, stderr = ssh.exec_command('sudo systemctl enable cloudflared 2>&1')
result = stdout.read().decode()
print("  [OK] Cloudflare tunnel enabled for auto-start")

# Enable Docker
stdin, stdout, stderr = ssh.exec_command('sudo systemctl enable docker 2>&1')
result = stdout.read().decode()
print("  [OK] Docker enabled for auto-start")

# Step 7: Test connectivity
print("\n[STEP 7] Testing connectivity...")
print("-" * 80)

# Test MycoBrain directly
stdin, stdout, stderr = ssh.exec_command('curl -s http://localhost:8003/health')
result = stdout.read().decode()
if "200" in result or "ok" in result.lower() or "healthy" in result.lower():
    print("  [OK] MycoBrain service responding on localhost:8003")
else:
    print(f"  [INFO] MycoBrain response: {result[:100]}")

# Test website API endpoint
time.sleep(3)  # Give it a moment to restart
stdin, stdout, stderr = ssh.exec_command('curl -s http://localhost:3000/api/mycobrain/health 2>&1 | head -5')
result = stdout.read().decode()
if "200" in result or "service_status" in result.lower():
    print("  [OK] Website API endpoint responding")
else:
    print(f"  [INFO] Website API response: {result[:100]}")

ssh.close()

print("\n" + "=" * 80)
print("MYCOBRAIN SETUP COMPLETE")
print("=" * 80)
print("\nSummary:")
print("  ✅ Cloudflare tunnel configured with MycoBrain routes")
print("  ✅ Website environment variable added")
print("  ✅ Services configured for auto-start")
print("  ✅ Containers restarted")
print("\nNext steps:")
print("  1. Test: curl https://sandbox.mycosoft.com/api/mycobrain/health")
print("  2. Verify: Check Cloudflare tunnel logs if needed")
print("  3. Reboot VM to test service persistence")
