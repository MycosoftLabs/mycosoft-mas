#!/usr/bin/env python3
import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.187', username='mycosoft', password='REDACTED_VM_SSH_PASSWORD')

VM_PASS = 'REDACTED_VM_SSH_PASSWORD'

def run(cmd):
    full_cmd = f"echo '{VM_PASS}' | sudo -S {cmd}"
    stdin, stdout, stderr = ssh.exec_command(full_cmd, timeout=60)
    return stdout.read().decode('utf-8', errors='replace')

print("=" * 60)
print("MYCOSOFT SANDBOX - FINAL STATUS")
print("=" * 60)

print("\n=== All Docker Containers ===")
result = run("docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'")
print(result)

print("=== Service Tests ===")
services = [
    (3000, "Website"),
    (8000, "MINDEX API"),
    (8001, "MAS Orchestrator"),
    (8003, "MycoBrain"),
    (5678, "n8n"),
    (3002, "Grafana"),
    (5432, "PostgreSQL"),
    (6379, "Redis"),
    (6333, "Qdrant"),
]

for port, name in services:
    stdin, stdout, stderr = ssh.exec_command(f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:{port} 2>/dev/null || echo 000")
    result = stdout.read().decode().strip()
    status = "[OK]" if result in ['200', '302', '401'] else f"[FAIL:{result}]"
    print(f"  {name:20} :{port} {status}")

ssh.close()

print("\n" + "=" * 60)
print("Public URLs:")
print("  https://sandbox.mycosoft.com")
print("  https://api-sandbox.mycosoft.com")
print("  https://brain-sandbox.mycosoft.com")
print("=" * 60)
