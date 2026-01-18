#!/usr/bin/env python3
"""Check website container status and logs"""

import paramiko

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "REDACTED_VM_SSH_PASSWORD"

def run_sudo(ssh, cmd):
    full_cmd = f"echo '{VM_PASSWORD}' | sudo -S {cmd}"
    stdin, stdout, stderr = ssh.exec_command(full_cmd, timeout=60)
    out = stdout.read().decode(errors='replace')
    err = stderr.read().decode(errors='replace')
    err_clean = "\n".join([l for l in err.split("\n") if "password" not in l.lower() and l.strip()])
    return out, err_clean

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=30)
    print("Connected!")

    # Check container status
    print("\n=== CONTAINER STATUS ===")
    out, _ = run_sudo(ssh, "docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}' | head -20")
    print(out)

    # Check website logs
    print("\n=== WEBSITE LOGS (last 30 lines) ===")
    out, err = run_sudo(ssh, "docker logs mycosoft-website --tail 30 2>&1")
    print(out)
    if err:
        print("Errors:", err)

    # Check if website is listening
    print("\n=== PORT 3000 CHECK ===")
    out, _ = run_sudo(ssh, "ss -tlnp | grep 3000")
    print(out if out else "Port 3000 not listening")

    # Try curl
    print("\n=== CURL TEST ===")
    stdin, stdout, stderr = ssh.exec_command("curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 http://localhost:3000")
    print("HTTP Status:", stdout.read().decode())

    ssh.close()

if __name__ == "__main__":
    main()
