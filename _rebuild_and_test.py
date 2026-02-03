#!/usr/bin/env python3
"""Rebuild MAS container with latest code and test."""

import paramiko
import time

def run_ssh_command(host, user, password, command, timeout=600):
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

password = "Mushroom1!Mushroom1!"

print("=" * 60)
print("Rebuilding MAS Docker Image and Container")
print("=" * 60)

# Step 1: Stop and remove old container
print("\n1. Removing old container...")
success, output = run_ssh_command(
    "192.168.0.188", "mycosoft", password,
    "docker stop myca-orchestrator 2>/dev/null; docker rm myca-orchestrator 2>/dev/null; echo 'Done'"
)
print(output)

# Step 2: Rebuild Docker image
print("\n2. Rebuilding Docker image (this takes a few minutes)...")
success, output = run_ssh_command(
    "192.168.0.188", "mycosoft", password,
    "cd /home/mycosoft/mycosoft/mas && docker build -t mycosoft/mas-agent:latest -f Dockerfile . 2>&1 | tail -20",
    timeout=600
)
print(output[-1500:] if output else "No output")

# Step 3: Start new container
print("\n3. Starting new container...")
success, output = run_ssh_command(
    "192.168.0.188", "mycosoft", password,
    """docker run -d --name myca-orchestrator \
        -p 8001:8001 \
        -e MAS_ENV=production \
        -e REDIS_URL=redis://mas-redis:6379/0 \
        -e N8N_URL=http://myca-n8n:5678 \
        --network mycosoft_mas-network \
        --restart unless-stopped \
        --health-cmd="curl -f http://localhost:8001/health || exit 1" \
        --health-interval=30s \
        --health-timeout=10s \
        --health-retries=3 \
        mycosoft/mas-agent:latest 2>&1 || echo 'Failed to start with network, trying bridge...'
    """
)
print(output)

# If network failed, try without network
if "Failed" in output or "Error" in output:
    print("\n3b. Trying with default bridge network...")
    success, output = run_ssh_command(
        "192.168.0.188", "mycosoft", password,
        "docker rm myca-orchestrator 2>/dev/null; " + 
        """docker run -d --name myca-orchestrator \
            -p 8001:8001 \
            -e MAS_ENV=production \
            --restart unless-stopped \
            mycosoft/mas-agent:latest"""
    )
    print(output)

# Step 4: Wait and check
print("\n4. Waiting for container to start...")
time.sleep(15)

success, output = run_ssh_command(
    "192.168.0.188", "mycosoft", password,
    "docker ps --filter 'name=myca-orchestrator' --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
)
print(output)

# Step 5: Check logs
print("\n5. Checking container logs...")
success, output = run_ssh_command(
    "192.168.0.188", "mycosoft", password,
    "docker logs myca-orchestrator --tail 15 2>&1"
)
print(output)

# Step 6: Test health
print("\n6. Testing health endpoint...")
success, output = run_ssh_command(
    "192.168.0.188", "mycosoft", password,
    "curl -s http://localhost:8001/health"
)
print(output)

# Step 7: Test memory endpoint
print("\n7. Testing memory endpoint...")
success, output = run_ssh_command(
    "192.168.0.188", "mycosoft", password,
    "curl -s http://localhost:8001/api/memory/health"
)
print(output)

print("\n" + "=" * 60)
print("Rebuild complete!")
print("=" * 60)
