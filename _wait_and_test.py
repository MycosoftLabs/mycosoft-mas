#!/usr/bin/env python3
"""Wait for container to be healthy and test."""

import paramiko
import time
import requests

def run_ssh_command(host, user, password, command, timeout=60):
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

print("Waiting for container to become healthy...")
for i in range(12):  # Wait up to 60 seconds
    time.sleep(5)
    success, output = run_ssh_command(
        "192.168.0.188", "mycosoft", password,
        "docker ps --filter 'name=myca-orchestrator' --format '{{.Status}}'"
    )
    print(f"  Attempt {i+1}: {output.strip()}")
    if "healthy" in output.lower():
        print("Container is healthy!")
        break

# Check logs
print("\nContainer logs:")
success, output = run_ssh_command(
    "192.168.0.188", "mycosoft", password,
    "docker logs myca-orchestrator --tail 20 2>&1"
)
print(output)

# Test locally
print("\nTesting locally on VM:")
success, output = run_ssh_command(
    "192.168.0.188", "mycosoft", password,
    "curl -s http://localhost:8001/health || curl -s http://localhost:8000/health"
)
print(f"Health: {output}")

success, output = run_ssh_command(
    "192.168.0.188", "mycosoft", password,
    "curl -s http://localhost:8001/api/memory/health || curl -s http://localhost:8000/api/memory/health"
)
print(f"Memory: {output}")

# Test from outside
print("\nTesting from outside:")
try:
    r = requests.get("http://192.168.0.188:8001/health", timeout=10)
    print(f"Health: {r.status_code} - {r.text[:200]}")
except Exception as e:
    print(f"Health: ERROR - {e}")
