#!/usr/bin/env python3
"""Check Cloudflare tunnel configuration"""

import paramiko
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "REDACTED_VM_SSH_PASSWORD"

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

    # Check cloudflared status
    print("\n=== CLOUDFLARED STATUS ===")
    out, _ = run_sudo(ssh, "systemctl status cloudflared --no-pager 2>&1 || pgrep -f cloudflared")
    print(out[:500])

    # Check cloudflared config
    print("\n=== CLOUDFLARED CONFIG ===")
    out, _ = run_sudo(ssh, "cat /etc/cloudflared/config.yml 2>/dev/null || echo 'No config file'")
    print(out)

    # Check running cloudflared processes
    print("\n=== CLOUDFLARED PROCESSES ===")
    out, _ = run_sudo(ssh, "ps aux 2>/dev/null | grep cloudflared || echo 'Not running'")
    print(out)

    # Check cloudflared logs
    print("\n=== CLOUDFLARED LOGS ===")
    out, _ = run_sudo(ssh, "journalctl -u cloudflared --no-pager -n 20 2>/dev/null || docker logs cloudflared --tail 20 2>&1 || echo 'No logs found'")
    print(out[-1000:])

    ssh.close()

if __name__ == "__main__":
    main()
