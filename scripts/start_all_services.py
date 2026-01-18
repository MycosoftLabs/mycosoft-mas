#!/usr/bin/env python3
"""Start all Mycosoft services on VM"""
import paramiko
import time

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "Mushroom1!Mushroom1!"

def run_cmd(ssh, cmd, sudo=False, timeout=300):
    if sudo:
        cmd = f"echo '{VM_PASS}' | sudo -S {cmd}"
    print(f">>> {cmd[:80]}...")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out:
        lines = out.strip().split('\n')
        for line in lines[-15:]:
            print(f"    {line}")
    return out, err

print("=" * 70)
print("STARTING ALL MYCOSOFT SERVICES")
print("=" * 70)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_IP, username=VM_USER, password=VM_PASS)
print("Connected!")

# Check what docker-compose files exist
print("\n=== Docker Compose files ===")
run_cmd(ssh, "find /opt/mycosoft -name 'docker-compose*.yml' 2>/dev/null")
run_cmd(ssh, "find ~/mycosoft -name 'docker-compose*.yml' 2>/dev/null")

# Stop all existing containers first
print("\n=== Stopping existing containers ===")
run_cmd(ssh, "docker stop $(docker ps -aq) 2>/dev/null || true", sudo=True)
run_cmd(ssh, "docker rm $(docker ps -aq) 2>/dev/null || true", sudo=True)

# Start from the home directory docker-compose (sandbox deployment)
print("\n=== Starting from ~/mycosoft ===")
run_cmd(ssh, "cd ~/mycosoft && docker compose up -d", sudo=True, timeout=600)

# Wait for services
print("\n=== Waiting for services to start (30s) ===")
time.sleep(30)

# Check status
print("\n=== Container Status ===")
run_cmd(ssh, "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'", sudo=True)

# Test services
print("\n=== Testing Services ===")
endpoints = [
    ("Website :3000", "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000"),
    ("MINDEX :8000", "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000"),
    ("MycoBrain :8003", "curl -s -o /dev/null -w '%{http_code}' http://localhost:8003"),
    ("n8n :5678", "curl -s -o /dev/null -w '%{http_code}' http://localhost:5678/healthz"),
    ("Grafana :3002", "curl -s -o /dev/null -w '%{http_code}' http://localhost:3002"),
    ("Redis :6379", "redis-cli ping 2>/dev/null || echo 'not installed'"),
]

for name, cmd in endpoints:
    out, _ = run_cmd(ssh, cmd)
    status = out.strip() if out else "FAILED"
    print(f"    {name}: {status}")

ssh.close()
print("\n" + "=" * 70)
print("DEPLOYMENT CHECK COMPLETE")
print("=" * 70)
