#!/usr/bin/env python3
"""Check MAS VM status."""

import paramiko

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

print("Checking MAS VM (192.168.0.188)...")
print("=" * 50)

# Check container status
success, output = run_ssh_command(
    "192.168.0.188",
    "mycosoft",
    password,
    "docker ps --filter 'name=myca-orchestrator' --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
)
print("\nContainer Status:")
print(output if output else "No output")

# Check container logs
success, output = run_ssh_command(
    "192.168.0.188",
    "mycosoft",
    password,
    "docker logs myca-orchestrator --tail 30 2>&1"
)
print("\nRecent Container Logs:")
print(output[-2000:] if output else "No logs")

# Check if port is listening
success, output = run_ssh_command(
    "192.168.0.188",
    "mycosoft",
    password,
    "ss -tlnp | grep 8001 || echo 'Port 8001 not listening'"
)
print("\nPort 8001 Status:")
print(output if output else "No output")

# Try local curl
success, output = run_ssh_command(
    "192.168.0.188",
    "mycosoft",
    password,
    "curl -s http://localhost:8001/health 2>&1 || echo 'Curl failed'"
)
print("\nLocal Health Check:")
print(output if output else "No output")
