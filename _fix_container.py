#!/usr/bin/env python3
"""Fix and restart the MAS container with correct port mapping."""

import paramiko
import time

def run_ssh_command(host, user, password, command, timeout=300):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username=user, password=password, timeout=30)
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        out = stdout.read().decode()
        err = stderr.read().decode()
        exit_code = stdout.channel.recv_exit_status()
        client.close()
        return exit_code == 0, out + err
    except Exception as e:
        return False, str(e)

password = "REDACTED_VM_SSH_PASSWORD"

print("=" * 60)
print("Fixing MAS Container Port Mapping")
print("=" * 60)

# Stop and remove old container
print("\n1. Stopping old container...")
success, output = run_ssh_command(
    "192.168.0.188", "mycosoft", password,
    "docker stop myca-orchestrator 2>/dev/null; docker rm myca-orchestrator 2>/dev/null; echo 'Done'"
)
print(output)

# Check what port the app expects
print("\n2. Checking Dockerfile port...")
success, output = run_ssh_command(
    "192.168.0.188", "mycosoft", password,
    "grep -i 'expose\\|port' /home/mycosoft/mycosoft/mas/Dockerfile | head -5"
)
print(output)

# Start with correct port mapping (8000 internal -> 8001 external)
print("\n3. Starting container with correct port mapping...")
success, output = run_ssh_command(
    "192.168.0.188", "mycosoft", password,
    """docker run -d --name myca-orchestrator \
        -p 8001:8000 \
        -e MAS_ENV=production \
        --restart unless-stopped \
        --health-cmd="curl -sf http://localhost:8000/health || exit 1" \
        --health-interval=30s \
        --health-timeout=10s \
        --health-retries=3 \
        mycosoft/mas-agent:latest"""
)
print(output)

# Wait for startup
print("\n4. Waiting for container to start...")
time.sleep(10)

# Check status
success, output = run_ssh_command(
    "192.168.0.188", "mycosoft", password,
    "docker ps --filter 'name=myca-orchestrator' --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
)
print(output)

# Test health
print("\n5. Testing health endpoint...")
success, output = run_ssh_command(
    "192.168.0.188", "mycosoft", password,
    "curl -s http://localhost:8001/health"
)
print(f"Health: {output}")

# Test memory
success, output = run_ssh_command(
    "192.168.0.188", "mycosoft", password,
    "curl -s http://localhost:8001/api/memory/health"
)
print(f"Memory: {output}")

# Check logs
print("\n6. Container logs:")
success, output = run_ssh_command(
    "192.168.0.188", "mycosoft", password,
    "docker logs myca-orchestrator --tail 10 2>&1"
)
print(output)

print("\n" + "=" * 60)
print("Container fixed!")
print("=" * 60)
