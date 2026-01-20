#!/usr/bin/env python3
"""Check MINDEX Postgres container presence and network attachments on the sandbox VM."""

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

    print(run(ssh, "docker ps -a --format \"{{.Names}}\\t{{.Status}}\\t{{.Image}}\" | grep -E \"mindex-postgres|mycosoft-postgres\" || echo NONE"))

    for name in ["mindex-postgres", "mycosoft-postgres"]:
        print("\n== " + name + " (inspect) ==")
        print(run(ssh, f"docker inspect {name} --format '{{{{json .State}}}}' 2>/dev/null || echo NO_CONTAINER"))
        print(run(ssh, f"docker inspect {name} --format '{{{{json .NetworkSettings.Networks}}}}' 2>/dev/null || true"))

    ssh.close()


if __name__ == "__main__":
    main()

