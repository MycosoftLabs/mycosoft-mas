#!/usr/bin/env python3
"""Rebuild MAS container on VM."""

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
print("Rebuilding MAS Container on VM (192.168.0.188)")
print("=" * 60)

# Stop the failing container
print("\n1. Stopping failing container...")
success, output = run_ssh_command(
    "192.168.0.188",
    "mycosoft",
    password,
    "docker stop myca-orchestrator 2>/dev/null; docker rm myca-orchestrator 2>/dev/null; echo 'Container removed'"
)
print(output)

# Check for docker-compose file
print("\n2. Checking build configuration...")
success, output = run_ssh_command(
    "192.168.0.188",
    "mycosoft",
    password,
    "ls -la /home/mycosoft/mycosoft/mas/docker-compose*.yml | head -5"
)
print(output)

# Rebuild using docker-compose
print("\n3. Rebuilding Docker image (this may take several minutes)...")
success, output = run_ssh_command(
    "192.168.0.188",
    "mycosoft",
    password,
    "cd /home/mycosoft/mycosoft/mas && docker build -t mycosoft/mas-agent:latest -f Dockerfile . 2>&1 | tail -30",
    timeout=600
)
print(output[-2000:] if output else "No output")

if not success:
    print("\nBuild may have failed. Trying alternative approach...")
    # Try using the simpler approach - just volume mount
    print("\n4. Trying volume mount approach...")
    success, output = run_ssh_command(
        "192.168.0.188",
        "mycosoft",
        password,
        """docker run -d --name myca-orchestrator \
           -p 8001:8001 \
           -v /home/mycosoft/mycosoft/mas:/app/mas \
           -e PYTHONPATH=/app/mas \
           --restart unless-stopped \
           --network bridge \
           python:3.11-slim \
           bash -c "pip install fastapi uvicorn pydantic redis && cd /app/mas && python -m uvicorn mycosoft_mas.core.myca_main:app --host 0.0.0.0 --port 8001"
        """
    )
    print(output)
else:
    # Start the rebuilt container
    print("\n4. Starting rebuilt container...")
    success, output = run_ssh_command(
        "192.168.0.188",
        "mycosoft",
        password,
        "cd /home/mycosoft/mycosoft/mas && docker compose up -d myca-orchestrator 2>&1 || docker run -d --name myca-orchestrator -p 8001:8001 --restart unless-stopped mycosoft/mas-agent:latest"
    )
    print(output)

# Wait and check status
print("\n5. Waiting for container to start...")
time.sleep(10)

success, output = run_ssh_command(
    "192.168.0.188",
    "mycosoft",
    password,
    "docker ps --filter 'name=myca-orchestrator' --format 'table {{.Names}}\t{{.Status}}'"
)
print(output)

success, output = run_ssh_command(
    "192.168.0.188",
    "mycosoft",
    password,
    "docker logs myca-orchestrator --tail 20 2>&1"
)
print("\nRecent logs:")
print(output[-1500:] if output else "No logs")

print("\n" + "=" * 60)
print("Rebuild complete!")
print("=" * 60)
