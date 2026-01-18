#!/usr/bin/env python3
"""Debug VM docker setup"""

import paramiko
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "Mushroom1!Mushroom1!"

def run_sudo(ssh, cmd):
    full_cmd = f"echo '{VM_PASSWORD}' | sudo -S {cmd}"
    stdin, stdout, stderr = ssh.exec_command(full_cmd, timeout=300)
    out = stdout.read().decode(errors='replace')
    err = stderr.read().decode(errors='replace')
    return out, err

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=30)
    print("Connected!")

    # Check docker-compose file
    print("\n=== Docker Compose File (first 80 lines) ===")
    stdin, stdout, stderr = ssh.exec_command("cat /opt/mycosoft/docker-compose.yml | head -80")
    print(stdout.read().decode(errors='replace'))

    # Check all containers
    print("\n=== All Containers ===")
    out, _ = run_sudo(ssh, "docker ps -a --format 'table {{.Names}}\t{{.Status}}'")
    print(out)

    # Check images
    print("\n=== Website Images ===")
    out, _ = run_sudo(ssh, "docker images | head -10")
    print(out)

    # Try to run website container manually
    print("\n=== Starting website manually ===")
    out, err = run_sudo(ssh, "docker run -d --name mycosoft-website-test -p 3000:3000 mycosoft-always-on-mycosoft-website:latest 2>&1 || docker run -d --name mycosoft-website-test -p 3000:3000 website-website:latest 2>&1")
    print(out)
    if "password" not in err.lower():
        print(err[:500])

    ssh.close()

if __name__ == "__main__":
    main()
