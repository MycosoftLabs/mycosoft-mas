#!/usr/bin/env python3
"""Start website container and check logs"""

import paramiko
import time

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "REDACTED_VM_SSH_PASSWORD"

def run_sudo(ssh, cmd):
    full_cmd = f"echo '{VM_PASSWORD}' | sudo -S {cmd}"
    stdin, stdout, stderr = ssh.exec_command(full_cmd, timeout=300)
    return stdout.read().decode(errors='replace'), stderr.read().decode(errors='replace')

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=30)

    print("1. Checking all container status...")
    out, _ = run_sudo(ssh, 'docker ps -a --format "table {{.Names}}\t{{.Status}}"')
    print(out)

    print("\n2. Starting website container...")
    out, err = run_sudo(ssh, 'docker start mycosoft-website')
    print(f"   Result: {out.strip()}")

    print("\n3. Waiting 30 seconds for startup...")
    time.sleep(30)

    print("\n4. Website container status:")
    out, _ = run_sudo(ssh, 'docker ps --filter name=mycosoft-website --format "table {{.Names}}\t{{.Status}}"')
    print(out)

    print("\n5. Website logs (last 40 lines):")
    out, _ = run_sudo(ssh, 'docker logs mycosoft-website --tail 40 2>&1')
    out_clean = ''.join(c if ord(c) < 128 else '?' for c in out)
    print(out_clean[:2000])

    print("\n6. Testing website endpoint:")
    stdin, stdout, stderr = ssh.exec_command("curl -s -o /dev/null -w '%{http_code}' http://localhost:3000 2>/dev/null || echo 'FAIL'")
    code = stdout.read().decode().strip()
    print(f"   HTTP Status: {code}")

    ssh.close()

if __name__ == "__main__":
    main()
