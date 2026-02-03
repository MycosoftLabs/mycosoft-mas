#!/usr/bin/env python3
"""Check entry point configuration."""

import paramiko

def run_ssh(host, user, password, command, timeout=60):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username=user, password=password, timeout=30)
    stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
    out = stdout.read().decode()
    client.close()
    return out

password = "REDACTED_VM_SSH_PASSWORD"

# Check Dockerfile CMD
print("Dockerfile CMD:")
output = run_ssh("192.168.0.188", "mycosoft", password,
    "grep CMD /home/mycosoft/mycosoft/mas/Dockerfile")
print(output)

# Check if main.py exists and has routers
print("\nChecking main.py routers:")
output = run_ssh("192.168.0.188", "mycosoft", password,
    "grep 'include_router' /home/mycosoft/mycosoft/mas/mycosoft_mas/core/main.py | head -10")
print(output if output else "No routers found in main.py")

# Check if myca_main.py exists and has routers  
print("\nChecking myca_main.py routers:")
output = run_ssh("192.168.0.188", "mycosoft", password,
    "grep 'include_router' /home/mycosoft/mycosoft/mas/mycosoft_mas/core/myca_main.py | head -10")
print(output if output else "No routers found")

# Check if memory_integration_api.py exists
print("\nChecking memory_integration_api.py:")
output = run_ssh("192.168.0.188", "mycosoft", password,
    "ls -la /home/mycosoft/mycosoft/mas/mycosoft_mas/core/routers/memory_integration_api.py 2>&1")
print(output)

# Check which file is imported
print("\nChecking imports in main.py:")
output = run_ssh("192.168.0.188", "mycosoft", password,
    "head -50 /home/mycosoft/mycosoft/mas/mycosoft_mas/core/main.py")
print(output[:2000] if output else "No output")
