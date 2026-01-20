#!/usr/bin/env python3
"""Inspect which cloudflared config the sandbox VM is actually running with.

We have multiple possible config locations (examples):
- /home/mycosoft/.cloudflared/config.yml
- /etc/cloudflared/config.yml

This script prints:
- systemd unit (cloudflared)
- running process args (cloudflared)
- existence + first lines of common config paths
"""

import paramiko
import sys

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "Mushroom1!Mushroom1!"


def run(ssh: paramiko.SSHClient, cmd: str) -> str:
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return (out + ("\n" + err if err.strip() else "")).strip()


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=30)

    sections = [
        ("systemd unit", "sudo systemctl cat cloudflared --no-pager -l || true"),
        ("systemd status", "sudo systemctl status cloudflared --no-pager -l | head -n 120 || true"),
        ("process args", "ps aux | grep -E '[c]loudflared' || true"),
        ("config paths", "ls -la /home/mycosoft/.cloudflared /etc/cloudflared 2>/dev/null || true"),
        ("home config head", "sed -n '1,120p' /home/mycosoft/.cloudflared/config.yml 2>/dev/null || echo 'NO_HOME_CONFIG'"),
        ("etc config head", "sed -n '1,120p' /etc/cloudflared/config.yml 2>/dev/null || echo 'NO_ETC_CONFIG'"),
    ]

    for title, cmd in sections:
        print("\n" + "=" * 90)
        print(title)
        print("=" * 90)
        print(run(ssh, cmd))

    ssh.close()


if __name__ == "__main__":
    main()

