#!/usr/bin/env python3
"""Check MINDEX container status and health on the sandbox VM."""

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

    print(run(ssh, "docker ps --format \"{{.Names}}\\t{{.Status}}\\t{{.Ports}}\" | grep -E \"mindex-api|mindex-postgres\" || true"))
    print("\n[mindex-api logs]")
    print(run(ssh, "docker logs --tail 120 mindex-api 2>&1 || true"))
    print("\n[health http]")
    print(run(ssh, "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/api/mindex/health || true"))

    ssh.close()


if __name__ == "__main__":
    main()

