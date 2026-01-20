#!/usr/bin/env python3
"""Deploy latest Website repo to sandbox VM (pull + rebuild --no-cache + recreate).

This follows the documented deployment steps, but runs them non-interactively via SSH.
"""

from __future__ import annotations

import paramiko
import sys

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "Mushroom1!Mushroom1!"

WEBSITE_DIR = "/opt/mycosoft/website"
COMPOSE_DIR = "/home/mycosoft/mycosoft/mas"
COMPOSE_FILE = "docker-compose.always-on.yml"


def run(ssh: paramiko.SSHClient, cmd: str) -> str:
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=False)
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

    print("[1] Pull latest website code")
    print(run(ssh, f"cd {WEBSITE_DIR} && git fetch origin main && git reset --hard origin/main"))

    print("\n[2] Rebuild website image (no-cache)")
    print(
        run(
            ssh,
            f"cd {COMPOSE_DIR} && docker compose -f {COMPOSE_FILE} build mycosoft-website --no-cache",
        )
    )

    print("\n[3] Recreate website container")
    print(
        run(
            ssh,
            f"cd {COMPOSE_DIR} && docker compose -f {COMPOSE_FILE} up -d --no-deps --force-recreate mycosoft-website",
        )
    )

    print("\n[4] Smoke test (VM localhost)")
    tests = [
        ("website health", "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/api/health || true"),
        ("mycobrain health", "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/api/mycobrain/health || true"),
        ("mycobrain ports", "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/api/mycobrain/ports || true"),
        ("mindex health", "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/api/mindex/health || true"),
    ]
    for name, cmd in tests:
        print(f" - {name}: {run(ssh, cmd)}")

    ssh.close()


if __name__ == "__main__":
    main()

