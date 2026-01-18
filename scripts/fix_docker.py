#!/usr/bin/env python3
import paramiko
import sys

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.187', username='mycosoft', password='REDACTED_VM_SSH_PASSWORD')

VM_PASS = 'REDACTED_VM_SSH_PASSWORD'

def run(cmd, timeout=120):
    full_cmd = f"echo '{VM_PASS}' | sudo -S {cmd}"
    print(f"\n>>> {cmd}")
    stdin, stdout, stderr = ssh.exec_command(full_cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if out:
        # Remove problematic unicode chars
        out_clean = out.replace('\u25cf', '*').replace('\u2022', '*')
        print(out_clean[:1500])
    if err and 'password' not in err.lower():
        print("ERR:", err[:500])
    return out, err

print("=== Check Docker service ===")
run("systemctl is-active docker")

print("=== Docker version ===")
run("docker --version")

print("=== Docker compose version ===")
run("docker compose version")

print("=== Check disk space ===")
run("df -h /")

print("=== Try docker compose up with output ===")
out, err = run("cd /home/mycosoft/mycosoft && docker compose up -d 2>&1")

print("=== Check for any containers ===")
run("docker ps -a")

print("=== Try running a simple container ===")
run("docker run --rm hello-world 2>&1 || echo DOCKER_TEST_FAILED")

ssh.close()
