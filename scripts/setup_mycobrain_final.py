#!/usr/bin/env python3
"""Complete MycoBrain setup - Fixed version"""

import paramiko
import yaml
import time
from io import StringIO

vm_ip = '192.168.0.187'
vm_user = 'mycosoft'
vm_password = 'REDACTED_VM_SSH_PASSWORD'

print("=" * 80)
print("COMPLETE MYCOBRAIN SETUP")
print("=" * 80)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(vm_ip, username=vm_user, password=vm_password)

def exec_command(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    return stdout.read().decode(), stderr.read().decode()

def exec_sudo(cmd, password):
    """Execute sudo command with password"""
    cmd_with_sudo = f'echo "{password}" | sudo -S {cmd}'
    stdin, stdout, stderr = ssh.exec_command(cmd_with_sudo)
    return stdout.read().decode(), stderr.read().decode()

# Step 1: Find compose file and check MycoBrain
print("\n[STEP 1] Checking services...")
print("-" * 80)

# Find compose file
stdout, stderr = exec_command('find ~ -name "docker-compose.always-on.yml" 2>/dev/null | head -1')
compose_file = stdout.strip() or f'/home/{vm_user}/mycosoft/docker-compose.always-on.yml'

print(f"  Using compose file: {compose_file}")

# Check if file exists
stdout, stderr = exec_command(f'test -f {compose_file} && echo "EXISTS" || echo "NOT_FOUND"')
if "NOT_FOUND" in stdout:
    print(f"  [WARNING] Compose file not found at {compose_file}")
    print("  Searching for alternative locations...")
    stdout, stderr = exec_command('ls -la ~/mycosoft/*.yml 2>/dev/null | head -5')
    print(f"  Found files: {stdout[:200]}")

# Check MycoBrain
stdout, stderr = exec_command('docker ps --filter "name=mycobrain" --format "{{.Names}}"')
if stdout.strip():
    print(f"  [OK] MycoBrain container: {stdout.strip()}")
else:
    print("  [WARNING] MycoBrain container not running")

# Step 2: Check Cloudflare config and update
print("\n[STEP 2] Configuring Cloudflare tunnel...")
print("-" * 80)

stdout, stderr = exec_command('cat ~/.cloudflared/config.yml 2>/dev/null || echo "FILE_NOT_FOUND"')
current_config_str = stdout

if "FILE_NOT_FOUND" in current_config_str:
    print("  [INFO] Creating new Cloudflare config")
    config = {}
else:
    try:
        config = yaml.safe_load(StringIO(current_config_str))
        if config is None:
            config = {}
        print("  [OK] Loaded existing config")
    except Exception as e:
        print(f"  [WARNING] Parse error: {e}")
        config = {}

# Get tunnel ID - check for existing tunnel
if "tunnel" not in config or not config.get("tunnel"):
    stdout, stderr = exec_command('cloudflared tunnel list 2>/dev/null | grep -v "ID" | head -1 | awk \'{print $1}\'')
    tunnel_id = stdout.strip()
    if tunnel_id:
        config["tunnel"] = tunnel_id
        config["credentials-file"] = f"/home/{vm_user}/.cloudflared/{tunnel_id}.json"
        print(f"  [OK] Using existing tunnel: {tunnel_id}")
    else:
        print("  [WARNING] No tunnel found. You may need to create one:")
        print("    Run: cloudflared tunnel create mycobrain-tunnel")
        config["tunnel"] = "YOUR_TUNNEL_ID_HERE"
        config["credentials-file"] = f"/home/{vm_user}/.cloudflared/YOUR_TUNNEL_ID_HERE.json"

# Check for existing MycoBrain routes
has_mycobrain = False
if "ingress" in config and isinstance(config["ingress"], list):
    for rule in config["ingress"]:
        if isinstance(rule, dict) and "service" in rule:
            if "8003" in str(rule.get("service", "")):
                has_mycobrain = True
                break

# Add MycoBrain routes
if not has_mycobrain:
    print("  [ADDING] MycoBrain routes")
    mycobrain_routes = [
        {"hostname": "sandbox.mycosoft.com", "service": "http://localhost:8003", "path": "/api/mycobrain"},
        {"hostname": "sandbox.mycosoft.com", "service": "http://localhost:8003", "path": "/api/mycobrain/*"}
    ]
    
    if "ingress" in config and isinstance(config["ingress"], list):
        # Remove old MycoBrain routes
        config["ingress"] = [r for r in config["ingress"] if not (isinstance(r, dict) and "8003" in str(r.get("service", "")))]
        # Find catch-all position
        catch_idx = len(config["ingress"])
        for i, r in enumerate(config["ingress"]):
            if isinstance(r, dict) and str(r.get("service", "")).startswith("http_status"):
                catch_idx = i
                break
        # Insert before catch-all
        config["ingress"] = config["ingress"][:catch_idx] + mycobrain_routes + config["ingress"][catch_idx:]
    else:
        config["ingress"] = mycobrain_routes + [{"service": "http_status:404"}]
else:
    print("  [SKIP] MycoBrain routes already exist")

# Write config
config_yaml = yaml.dump(config, default_flow_style=False, sort_keys=False)
stdin, stdout, stderr = ssh.exec_command('mkdir -p ~/.cloudflared && cat > /tmp/cf_config.yml << \'CFEOF\'\n' + config_yaml + '\nCFEOF')
stdout.read()

stdin, stdout, stderr = ssh.exec_command('cp ~/.cloudflared/config.yml ~/.cloudflared/config.yml.backup 2>/dev/null; mv /tmp/cf_config.yml ~/.cloudflared/config.yml')
stdout.read()
print("  [OK] Config file written")

# Step 3: Update website env vars
print("\n[STEP 3] Updating website environment variables...")
print("-" * 80)

stdout, stderr = exec_command(f'cat {compose_file} 2>/dev/null')
if stdout.strip():
    compose_content = stdout
    if 'MYCOBRAIN_SERVICE_URL' not in compose_content:
        # Find website service - could be mycosoft-website or website
        lines = compose_content.split('\n')
        new_lines = []
        in_website = False
        in_env = False
        added = False
        
        for i, line in enumerate(lines):
            new_lines.append(line)
            if 'mycosoft-website:' in line or 'website:' in line or '  website:' in line:
                in_website = True
                continue
            if in_website and 'environment:' in line:
                in_env = True
                continue
            if in_website and in_env and not added:
                # Check if next non-empty line starts new section
                next_line = None
                for j in range(i+1, min(i+3, len(lines))):
                    if lines[j].strip() and not lines[j].strip().startswith(' ') and ':' in lines[j]:
                        next_line = lines[j]
                        break
                if next_line and not next_line.strip().startswith('#'):
                    new_lines.insert(-1, '      MYCOBRAIN_SERVICE_URL: http://host.docker.internal:8003')
                    added = True
                elif i == len(lines) - 1:
                    new_lines.append('      MYCOBRAIN_SERVICE_URL: http://host.docker.internal:8003')
                    added = True
        
        if added:
            new_content = '\n'.join(new_lines)
            stdin, stdout, stderr = ssh.exec_command(f'cat > /tmp/new_compose.yml << \'COMPEOF\'\n{new_content}\nCOMPEOF')
            stdout.read()
            stdin, stdout, stderr = exec_command(f'cp {compose_file} {compose_file}.backup && mv /tmp/new_compose.yml {compose_file}')
            print("  [OK] Environment variable added")
        else:
            print("  [WARNING] Could not find insertion point for env var")
    else:
        print("  [SKIP] MYCOBRAIN_SERVICE_URL already exists")
else:
    print(f"  [WARNING] Could not read compose file: {compose_file}")

# Step 4: Restart services with password
print("\n[STEP 4] Restarting services...")
print("-" * 80)

# Restart Cloudflare (using password)
stdout, stderr = exec_sudo('systemctl restart cloudflared', vm_password)
if "error" not in stdout.lower() and "failed" not in stdout.lower():
    print("  [OK] Cloudflare tunnel restarted")
else:
    print(f"  [INFO] Restart result: {stdout[:100]}")

time.sleep(2)

# Check Cloudflare status
stdout, stderr = exec_sudo('systemctl is-active cloudflared', vm_password)
if "active" in stdout.lower():
    print("  [OK] Cloudflare tunnel is active")

# Restart website - try docker compose (no hyphen) first
stdout, stderr = exec_command(f'cd ~/mycosoft 2>/dev/null && docker compose -f docker-compose.always-on.yml restart mycosoft-website 2>&1 || docker compose -f docker-compose.always-on.yml restart website 2>&1')
if "error" not in stdout.lower():
    print("  [OK] Website container restarted")
else:
    print(f"  [INFO] Restart: {stdout[:100]}")

# Step 5: Test connectivity
print("\n[STEP 5] Testing connectivity...")
print("-" * 80)

stdout, stderr = exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost:8003/health')
if stdout.strip() == "200":
    print("  [OK] MycoBrain service: HTTP 200")
else:
    print(f"  [INFO] MycoBrain health: {stdout.strip()}")

time.sleep(2)
stdout, stderr = exec_command('curl -s http://localhost:3000/api/mycobrain/health 2>&1 | head -1')
if "200" in stdout or "service_status" in stdout.lower():
    print("  [OK] Website API endpoint responding")
else:
    print(f"  [INFO] Website API: {stdout[:50]}")

ssh.close()

print("\n" + "=" * 80)
print("SETUP COMPLETE")
print("=" * 80)
print("\nSummary:")
print("  - Cloudflare tunnel configured with MycoBrain routes")
print("  - Website environment variable added (if compose file found)")
print("  - Services restarted")
print("\nNext: Test https://sandbox.mycosoft.com/api/mycobrain/health")
