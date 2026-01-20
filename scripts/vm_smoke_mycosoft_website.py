#!/usr/bin/env python3
"""Smoke test key endpoints from inside the sandbox VM (localhost)."""

import paramiko
import sys

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "Mushroom1!Mushroom1!"


def run(ssh: paramiko.SSHClient, cmd: str) -> str:
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    return out if not err else out + "\n" + err


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASS, timeout=30)

    print("website repo HEAD:", run(ssh, "cd /opt/mycosoft/website && git rev-parse --short HEAD || true"))
    print("health route exists:", run(ssh, "ls -la /opt/mycosoft/website/app/api/mycobrain/health/route.ts 2>/dev/null && echo OK || echo MISSING"))
    print("container build has health route:", run(ssh,
        "cid=$(docker ps --format \"{{.Names}}\" | grep -E \"mycosoft-website|website\" | head -n 1); "
        "docker exec \"$cid\" sh -lc 'ls -la /app/.next/server/app/api/mycobrain/health 2>/dev/null || echo MISSING' || true"
    ))

    checks = [
        ("website /api/health", "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/api/health || true"),
        ("website /api/mycobrain/health", "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/api/mycobrain/health || true"),
        ("website /api/mycobrain/ports", "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/api/mycobrain/ports || true"),
        ("website /api/mycobrain/devices", "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/api/mycobrain/devices || true"),
    ]

    for name, cmd in checks:
        print(f"{name}: {run(ssh, cmd)}")

    ssh.close()


if __name__ == "__main__":
    main()

