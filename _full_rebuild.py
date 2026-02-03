#!/usr/bin/env python3
"""Full rebuild with latest code."""

import paramiko
import time

def run_ssh(host, user, password, command, timeout=600):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username=user, password=password, timeout=30)
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        out = stdout.read().decode()
        err = stderr.read().decode()
        client.close()
        return out + err
    except Exception as e:
        return str(e)

password = "Mushroom1!Mushroom1!"

print("=" * 60)
print("Full Rebuild with Latest Code")
print("=" * 60)

# 1. Stop container
print("\n1. Stopping container...")
output = run_ssh("192.168.0.188", "mycosoft", password,
    "docker stop myca-orchestrator 2>/dev/null; docker rm myca-orchestrator 2>/dev/null; echo Done")
print(output)

# 2. Pull latest code
print("\n2. Pulling latest code from GitHub...")
output = run_ssh("192.168.0.188", "mycosoft", password,
    "cd /home/mycosoft/mycosoft/mas && git fetch origin && git reset --hard origin/main && git log -1 --oneline")
print(output)

# 3. Verify new file exists
print("\n3. Verifying memory_integration_api.py exists...")
output = run_ssh("192.168.0.188", "mycosoft", password,
    "ls -la /home/mycosoft/mycosoft/mas/mycosoft_mas/core/routers/memory_integration_api.py 2>&1")
print(output)

# 4. Rebuild Docker image
print("\n4. Rebuilding Docker image (this takes a few minutes)...")
output = run_ssh("192.168.0.188", "mycosoft", password,
    "cd /home/mycosoft/mycosoft/mas && docker build -t mycosoft/mas-agent:latest -f Dockerfile . 2>&1 | tail -15",
    timeout=600)
print(output[-1500:] if output else "No output")

# 5. Start container
print("\n5. Starting container...")
output = run_ssh("192.168.0.188", "mycosoft", password,
    """docker run -d --name myca-orchestrator \
        -p 8001:8000 \
        -e MAS_ENV=production \
        --restart unless-stopped \
        --health-cmd="curl -sf http://localhost:8000/health || exit 1" \
        --health-interval=30s \
        --health-timeout=10s \
        --health-retries=3 \
        mycosoft/mas-agent:latest""")
print(output)

# 6. Wait for startup
print("\n6. Waiting for container to start...")
time.sleep(15)

# 7. Check status
print("\n7. Container status:")
output = run_ssh("192.168.0.188", "mycosoft", password,
    "docker ps --filter name=myca-orchestrator --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'")
print(output)

# 8. Test endpoints
print("\n8. Testing endpoints...")
output = run_ssh("192.168.0.188", "mycosoft", password,
    "curl -s http://localhost:8001/health")
print(f"Health: {output}")

output = run_ssh("192.168.0.188", "mycosoft", password,
    "curl -s http://localhost:8001/api/memory/health")
print(f"Memory: {output}")

output = run_ssh("192.168.0.188", "mycosoft", password,
    "curl -s http://localhost:8001/mindex/health")
print(f"MINDEX: {output}")

# 9. Check logs
print("\n9. Container logs:")
output = run_ssh("192.168.0.188", "mycosoft", password,
    "docker logs myca-orchestrator --tail 15 2>&1")
print(output)

print("\n" + "=" * 60)
print("Rebuild complete!")
print("=" * 60)
