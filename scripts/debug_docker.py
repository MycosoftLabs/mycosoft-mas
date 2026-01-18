#!/usr/bin/env python3
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.187', username='mycosoft', password='REDACTED_VM_SSH_PASSWORD')

VM_PASS = 'REDACTED_VM_SSH_PASSWORD'

def run(cmd):
    full_cmd = f"echo '{VM_PASS}' | sudo -S {cmd}"
    print(f"\n>>> {cmd}")
    stdin, stdout, stderr = ssh.exec_command(full_cmd, timeout=60)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out:
        print(out[:2000])
    if err and 'password' not in err.lower():
        print("STDERR:", err[:500])

print("=== Docker Compose file ===")
run("cat /home/mycosoft/mycosoft/docker-compose.yml | head -50")

print("=== Try starting with verbose output ===")
run("cd /home/mycosoft/mycosoft && docker compose up -d 2>&1")

print("=== All containers (including exited) ===")
run("docker ps -a")

print("=== Docker logs for failed containers ===")
run("docker logs mycosoft-website 2>&1 | tail -20")
run("docker logs mindex-api 2>&1 | tail -20")

ssh.close()
