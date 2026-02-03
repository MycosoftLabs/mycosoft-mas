#!/usr/bin/env python3
"""Check MAS VM paths and deploy"""

import paramiko

def run_ssh_command(host, user, password, command, timeout=120):
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

# Check what's on MAS VM
print("Checking MAS VM directories...")
success, output = run_ssh_command(
    "192.168.0.188",
    "mycosoft",
    password,
    "ls -la /opt/mycosoft/ 2>/dev/null || ls -la /home/mycosoft/ 2>/dev/null || find /home -name 'mycosoft-mas' -type d 2>/dev/null || find /opt -name 'mycosoft*' -type d 2>/dev/null"
)
print(output)

# Check home directory
print("\nChecking home directory...")
success, output = run_ssh_command(
    "192.168.0.188",
    "mycosoft",
    password,
    "ls -la ~/"
)
print(output)

# Check for git repos
print("\nChecking for git repos...")
success, output = run_ssh_command(
    "192.168.0.188",
    "mycosoft",
    password,
    "find ~ -name '.git' -type d 2>/dev/null | head -10"
)
print(output)

# Check docker containers
print("\nDocker containers:")
success, output = run_ssh_command(
    "192.168.0.188",
    "mycosoft",
    password,
    "docker ps -a 2>/dev/null || echo 'Docker not available'"
)
print(output)
