#!/usr/bin/env python3
"""Start MINDEX Postgres on the sandbox VM and restart mindex-api to restore DB-backed endpoints."""

from __future__ import annotations

import paramiko
import sys
import time

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

    print("[1] Starting mindex-postgres (compose project: mycosoft-production)")
    print(run(ssh, "cd /opt/mycosoft && docker compose -p mycosoft-production up -d mindex-postgres"))

    print("\n[2] Waiting for Postgres health...")
    for i in range(30):
        status = run(
            ssh,
            "docker ps --format \"{{.Names}}\\t{{.Status}}\" | grep -E \"mindex-postgres\" || true",
        )
        if "healthy" in status.lower():
            print("[OK] mindex-postgres healthy")
            break
        if i in (0, 4, 9, 14, 19, 24, 29):
            print(f"  [{i+1}/30] {status or '(not running yet)'}")
        time.sleep(2)

    print("\n[3] Restarting mindex-api (to re-init DB connection)")
    print(run(ssh, "docker restart mindex-api || true"))

    print("\n[4] Smoke: MINDEX health + DB-backed endpoints")
    checks = [
        ("health", "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/api/mindex/health || true"),
        ("devices_latest", "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/api/mindex/telemetry/devices/latest -H 'X-API-Key: local-dev-key' || true"),
        ("mycobrain_devices_list", "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/api/mindex/mycobrain/devices -H 'X-API-Key: local-dev-key' || true"),
    ]
    for name, cmd in checks:
        print(f" - {name}: {run(ssh, cmd)}")

    ssh.close()


if __name__ == "__main__":
    main()

