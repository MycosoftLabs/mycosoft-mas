#!/usr/bin/env python3
"""Check MycoBrain services on the sandbox VM and validate routing.

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
ssh.connect('192.168.0.187', username='mycosoft', password='Mushroom1!Mushroom1!')

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
def _try(cmd: str) -> str:
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    return (out + ("\n" + err if err.strip() else "")).strip()


def _first_existing_dir(dirs: list[str]) -> str:
    for d in dirs:
        probe = _try(f'test -d "{d}" && echo OK || true')
        if probe.strip() == "OK":
            return d
    return ""


vm_root = _first_existing_dir(["/opt/mycosoft", "/home/mycosoft/mycosoft", "~/mycosoft"])

compose_candidates = []
if vm_root:
    compose_candidates.append(f'cd "{vm_root}" && docker compose -f docker-compose.always-on.yml ps')
    compose_candidates.append(f'cd "{vm_root}" && docker-compose -f docker-compose.always-on.yml ps')
compose_candidates.append('docker compose -f docker-compose.always-on.yml ps')
compose_candidates.append('docker-compose -f docker-compose.always-on.yml ps')

compose_services = ""
for cmd in compose_candidates:
    result = _try(cmd)
    if result and "no such file" not in result.lower() and "cannot" not in result.lower():
        compose_services = result
        break

if not compose_services:
    compose_services = "[WARN] Could not locate docker-compose.always-on.yml on VM (checked /opt/mycosoft and /home/mycosoft/mycosoft)."

print("\n3. DOCKER COMPOSE SERVICES:")
print("-" * 60)
print(compose_services)
compose_services = stdout.read().decode()
print(compose_services)

# 4. Check MycoBrain service specifically
print("\n4. MYCOBRAIN SERVICE IN COMPOSE:")
print("-" * 60)
print("\n4. MYCOBRAIN SERVICE IN COMPOSE (if present):")
print("-" * 60)
if vm_root:
    print(_try(f'cd "{vm_root}" && docker compose -f docker-compose.always-on.yml ps mycobrain-service 2>/dev/null || true') or "(not found)")
else:
    print("(skipped; VM root not found)")

# 5. Test localhost:8003 (MycoBrain port)
print("\n5. TESTING MYCOBRAIN API ENDPOINTS:")
print("-" * 60)
print("  VM localhost:8003 (only if MycoBrain is running on VM):")
for endpoint in ['/health', '/']:
    result = _try(f'curl -s -o /dev/null -w "%{{http_code}}" http://localhost:8003{endpoint} || echo "FAILED"')
    print(f"    {endpoint}: {result}")

print("\n  VM -> Windows LAN MycoBrain (authoritative sandbox target):")
for endpoint in ['/health', '/ports', '/devices']:
    result = _try(f'curl -s -o /dev/null -w "%{{http_code}}" http://192.168.0.172:18003{endpoint} || echo "FAILED"')
    print(f"    {endpoint}: {result}")

# 6. Check Cloudflare tunnel config for MycoBrain
print("\n6. CLOUDFLARE TUNNEL CONFIG:")
print("-" * 60)
print("\n6. CLOUDFLARE TUNNEL CONFIG (MycoBrain ingress snippets):")
print("-" * 60)
print(_try('cat ~/.cloudflared/config.yml 2>/dev/null | grep -n -A 6 -B 2 -i "/api/mycobrain" || echo "No /api/mycobrain rules found"'))

# 7. Check if MycoBrain service logs show errors
print("\n7. RECENT MYCOBRAIN SERVICE LOGS (last 20 lines):")
print("-" * 60)
print("  (Only available if MycoBrain is running as a VM container named mycobrain-service)")
if vm_root:
    logs = _try(f'cd "{vm_root}" && docker compose -f docker-compose.always-on.yml logs --tail=20 mycobrain-service 2>&1 || true')
    print(logs or "(no logs / service not present)")
else:
    print("(skipped; VM root not found)")

ssh.close()
