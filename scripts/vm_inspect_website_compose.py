#!/usr/bin/env python3
"""Inspect sandbox VM for website repo + always-on compose env wiring."""

import paramiko
import sys

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "Mushroom1!Mushroom1!"


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
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASS, timeout=30)

    cmds = [
        "ls -la /opt/mycosoft | head -n 120 || true",
        "ls -la /opt/mycosoft/website | head -n 80 || true",
        "ls -la /opt/mycosoft/docker-compose.always-on.yml || true",
        "grep -n \"MYCOBRAIN_SERVICE_URL\" /opt/mycosoft/docker-compose.always-on.yml 2>/dev/null || echo \"NO_MYCOBRAIN_SERVICE_URL\"",
        "docker ps --format \"{{.Names}}\t{{.Status}}\t{{.Ports}}\" | grep -E \"website|mycosoft-website\" || true",
        "docker inspect $(docker ps --format \"{{.Names}}\" | grep -E \"mycosoft-website|website\" | head -n 1) --format \"{{range .Config.Env}}{{println .}}{{end}}\" | grep -E \"MYCOBRAIN_SERVICE_URL|MINDEX\" || true",
    ]

    for cmd in cmds:
        print("\n$ " + cmd)
        print(run(ssh, cmd))

    ssh.close()


if __name__ == "__main__":
    main()

