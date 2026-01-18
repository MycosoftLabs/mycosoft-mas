#!/usr/bin/env python3
"""Check MycoBrain device detection service status and functionality"""

import paramiko
import requests
import json

vm_ip = '192.168.0.187'
vm_user = 'mycosoft'
vm_password = 'REDACTED_VM_SSH_PASSWORD'

print("=" * 80)
print("MYCOBRAIN DEVICE SERVICE DIAGNOSTICS")
print("=" * 80)

# SSH connection
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(vm_ip, username=vm_user, password=vm_password)

def exec_command(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    return stdout.read().decode(), stderr.read().decode()

def exec_sudo(cmd, password):
    stdin, stdout, stderr = ssh.exec_command(f'echo "{password}" | sudo -S {cmd}')
    return stdout.read().decode(), stderr.read().decode()

# 1. Check MycoBrain service status
print("\n[STEP 1] Checking MycoBrain Service...")
print("-" * 80)

stdout, stderr = exec_command('docker ps --filter "name=mycobrain" --format "{{.Names}}\t{{.Status}}\t{{.Ports}}"')
if stdout.strip():
    print(f"  [OK] {stdout.strip()}")
else:
    print("  [ERROR] MycoBrain container not running!")

# Check health
stdout, stderr = exec_command('curl -s http://localhost:8003/health')
print(f"  Health: {stdout.strip()[:100]}")

# 2. Check MycoBrain API endpoints
print("\n[STEP 2] Testing MycoBrain API Endpoints...")
print("-" * 80)

endpoints = ['/devices', '/ports', '/telemetry']
for endpoint in endpoints:
    stdout, stderr = exec_command(f'curl -s http://localhost:8003{endpoint}')
    try:
        data = json.loads(stdout) if stdout.strip() else {}
        print(f"  {endpoint:15s} - Status: OK, Response: {json.dumps(data)[:80]}")
    except:
        print(f"  {endpoint:15s} - Response: {stdout.strip()[:80]}")

# 3. Check website API endpoints
print("\n[STEP 3] Testing Website API Endpoints (via VM localhost)...")
print("-" * 80)

website_endpoints = [
    '/api/mycobrain/devices',
    '/api/mycobrain/ports',
    '/api/mycobrain/telemetry',
    '/api/mycobrain/health'
]

for endpoint in website_endpoints:
    stdout, stderr = exec_command(f'curl -s http://localhost:3000{endpoint}')
    try:
        data = json.loads(stdout) if stdout.strip() else {}
        status = data.get('service_status', 'unknown')
        devices = data.get('devices', [])
        print(f"  {endpoint:35s} - Status: {status}, Devices: {len(devices)}")
    except:
        print(f"  {endpoint:35s} - Response: {stdout.strip()[:80]}")

# 4. Check for device detection service/process
print("\n[STEP 4] Checking for Device Detection Service...")
print("-" * 80)

# Check systemd services
stdout, stderr = exec_sudo('systemctl list-units --type=service | grep -i mycobrain', vm_password)
if stdout.strip():
    print("  [FOUND] MycoBrain systemd services:")
    print(f"    {stdout.strip()}")
else:
    print("  [INFO] No MycoBrain systemd services found")

# Check running processes
stdout, stderr = exec_command('ps aux | grep -i "mycobrain\|serial\|com\|device" | grep -v grep | head -10')
if stdout.strip():
    print("  [FOUND] Related processes:")
    for line in stdout.strip().split('\n')[:5]:
        print(f"    {line[:80]}")
else:
    print("  [INFO] No device detection processes found")

# 5. Check Docker logs for device detection
print("\n[STEP 5] Checking MycoBrain Container Logs...")
print("-" * 80)

stdout, stderr = exec_command('docker logs mycobrain --tail 30 2>&1')
logs = stdout.strip()
if logs:
    print("  Recent logs:")
    for line in logs.split('\n')[-10:]:
        if any(keyword in line.lower() for keyword in ['device', 'port', 'com', 'serial', 'connect', 'detect']):
            print(f"    {line[:100]}")

# 6. Test sandbox endpoints
print("\n[STEP 6] Testing Sandbox Endpoints (Public)...")
print("-" * 80)

sandbox_endpoints = [
    'https://sandbox.mycosoft.com/api/mycobrain/devices',
    'https://sandbox.mycosoft.com/api/mycobrain/ports',
    'https://sandbox.mycosoft.com/natureos/devices'
]

for endpoint in sandbox_endpoints:
    try:
        r = requests.get(endpoint, timeout=10)
        try:
            data = r.json()
            status = data.get('service_status', 'unknown')
            devices = data.get('devices', []) if isinstance(data.get('devices'), list) else []
            count = data.get('count', len(devices))
            print(f"  {endpoint:50s} - HTTP {r.status_code}, Devices: {count}, Status: {status}")
        except:
            print(f"  {endpoint:50s} - HTTP {r.status_code}, Response: {r.text[:80]}")
    except Exception as e:
        print(f"  {endpoint:50s} - ERROR: {str(e)[:50]}")

# 7. Check website service logs
print("\n[STEP 7] Checking Website Container Logs for Device API...")
print("-" * 80)

stdout, stderr = exec_command('docker logs mycosoft-website --tail 50 2>&1 | grep -i "mycobrain\|device\|error" | tail -10')
if stdout.strip():
    print("  Recent relevant logs:")
    for line in stdout.strip().split('\n'):
        print(f"    {line[:100]}")

ssh.close()

print("\n" + "=" * 80)
print("DIAGNOSTICS COMPLETE")
print("=" * 80)
