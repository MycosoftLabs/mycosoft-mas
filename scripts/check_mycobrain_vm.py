#!/usr/bin/env python3
"""Check MycoBrain services on VM and test connectivity.

Notes:
- This script is run from Windows terminals sometimes; force UTF-8 stdout to avoid encoding crashes.
"""

import paramiko
import json
import sys

# Avoid UnicodeEncodeError on Windows consoles (cp1252).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.187', username='mycosoft', password='REDACTED_VM_SSH_PASSWORD')

print("=" * 60)
print("MYCOBRAIN SERVICE STATUS CHECK")
print("=" * 60)

# 1. Check all Docker containers
print("\n1. DOCKER CONTAINERS:")
print("-" * 60)
stdin, stdout, stderr = ssh.exec_command('docker ps --format "{{.Names}}\t{{.Status}}\t{{.Ports}}"')
containers = stdout.read().decode()
print(containers)

# 2. Check specifically for MycoBrain containers
print("\n2. MYCOBRAIN CONTAINERS:")
print("-" * 60)
stdin, stdout, stderr = ssh.exec_command('docker ps --filter "name=mycobrain" --format "{{.Names}}\t{{.Status}}\t{{.Ports}}"')
mycobrain_containers = stdout.read().decode()
if mycobrain_containers.strip():
    print(mycobrain_containers)
else:
    print("  [ERROR] No MycoBrain containers found!")

# 3. Check docker-compose services
print("\n3. DOCKER COMPOSE SERVICES:")
print("-" * 60)
stdin, stdout, stderr = ssh.exec_command('cd ~/mycosoft && docker-compose -f docker-compose.always-on.yml ps')
compose_services = stdout.read().decode()
print(compose_services)

# 4. Check MycoBrain service specifically
print("\n4. MYCOBRAIN SERVICE IN COMPOSE:")
print("-" * 60)
stdin, stdout, stderr = ssh.exec_command('cd ~/mycosoft && docker-compose -f docker-compose.always-on.yml ps mycobrain-service')
mycobrain_service = stdout.read().decode()
print(mycobrain_service)

# 5. Test localhost:8003 (MycoBrain port)
print("\n5. TESTING MYCOBRAIN API ENDPOINTS:")
print("-" * 60)
for endpoint in ['/health', '/api/health', '/']:
    stdin, stdout, stderr = ssh.exec_command(f'curl -s -o /dev/null -w "%{{http_code}}" http://localhost:8003{endpoint} || echo "FAILED"')
    result = stdout.read().decode().strip()
    print(f"  {endpoint}: {result}")

# 6. Check Cloudflare tunnel config for MycoBrain
print("\n6. CLOUDFLARE TUNNEL CONFIG:")
print("-" * 60)
try:
    stdin, stdout, stderr = ssh.exec_command('cat ~/.cloudflared/config.yml | grep -A 5 -i mycobrain || echo "No MycoBrain config found"')
    tunnel_config = stdout.read().decode()
    print(tunnel_config)
except:
    print("  ⚠ Could not read Cloudflare config")

# 7. Check if MycoBrain service logs show errors
print("\n7. RECENT MYCOBRAIN SERVICE LOGS (last 20 lines):")
print("-" * 60)
stdin, stdout, stderr = ssh.exec_command('cd ~/mycosoft && docker-compose -f docker-compose.always-on.yml logs --tail=20 mycobrain-service 2>&1')
logs = stdout.read().decode()
if logs.strip():
    print(logs)
else:
    print("  ⚠ No logs available")

ssh.close()
