#!/usr/bin/env python3
"""Deploy MINDEX API to VM 192.168.0.189 via SSH."""
from __future__ import annotations

import os
import sys
import time

# Load credentials from MAS repo
_REPO = os.path.dirname(os.path.abspath(__file__))
os.chdir(_REPO)
creds = os.path.join(_REPO, ".credentials.local")
if not os.path.isfile(creds):
    print(f"ERROR: Missing {creds}")
    sys.exit(1)
for line in open(creds, encoding="utf-8", errors="replace").read().splitlines():
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()

password = os.environ.get("VM_SSH_PASSWORD") or os.environ.get("VM_PASSWORD")
if not password:
    print("ERROR: No VM_PASSWORD / VM_SSH_PASSWORD in .credentials.local")
    sys.exit(1)

import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("192.168.0.189", username="mycosoft", password=password, timeout=30)


def run(cmd: str):
    stdin, stdout, stderr = client.exec_command(cmd, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return stdout.channel.recv_exit_status(), out, err


def detect_compose_cmd() -> str:
    """Prefer Docker Compose v2 (`docker compose`); fall back to `docker-compose`."""
    c, o, e = run("bash -lc 'command -v docker-compose >/dev/null 2>&1 && docker-compose version >/dev/null 2>&1 && echo legacy || true'")
    _ = (o, e)
    c2, o2, _ = run("bash -lc 'docker compose version >/dev/null 2>&1 && echo v2 || echo legacy'")
    out = (o2 or "").strip()
    if "v2" in out or (c2 == 0 and "v2" in (o2 or "")):
        return "docker compose"
    return "docker-compose"


COMPOSE = detect_compose_cmd()
print(f"Using compose command: {COMPOSE}\n")


try:
    print("=== 1. Fetch and reset code ===")
    c, o, e = run("cd /home/mycosoft/mindex && git fetch origin && git reset --hard origin/main")
    print((o or e).strip())
    if c != 0:
        print("FAILED")
        sys.exit(1)

    print("=== 2. Stop and remove API container ===")
    c, o, e = run(
        f"cd /home/mycosoft/mindex && {COMPOSE} stop api 2>/dev/null; "
        "docker rm -f mindex-api 2>/dev/null || true"
    )
    print((o or e).strip())

    print("=== 3. Build API (no cache) ===")
    c, o, e = run(f"cd /home/mycosoft/mindex && {COMPOSE} build --no-cache api")
    if c != 0:
        print((o or e)[-4000:])
        print("BUILD FAILED")
        sys.exit(1)
    print("Build completed OK")

    print("=== 4. Start API (--no-deps, db/redis/qdrant already running) ===")
    c, o, e = run(f"cd /home/mycosoft/mindex && {COMPOSE} up -d --no-deps api")
    print((o or e).strip())
    if c != 0:
        print("Compose failed, trying docker run with host network...")
        run("docker rm -f mindex-api 2>/dev/null || true")
        c2, o2, e2 = run(
            "docker run -d --name mindex-api --network host "
            "-e MINDEX_DB_HOST=127.0.0.1 -e MINDEX_DB_PORT=5432 "
            "-e MINDEX_DB_USER=mindex -e MINDEX_DB_PASSWORD=mindex -e MINDEX_DB_NAME=mindex "
            "mindex_api:latest uvicorn mindex_api.main:app --host 0.0.0.0 --port 8000"
        )
        print((o2 or e2).strip())
        if c2 != 0:
            print("START FAILED")
            sys.exit(1)

    print("=== 5. Wait 10s and verify ===")
    time.sleep(10)
    c, o, e = run("curl -s http://localhost:8000/api/mindex/health")
    resp = (o or e).strip()
    print("Health:", resp)
    okish = any(
        x in resp.lower()
        for x in ("ok", "healthy", '"status"', "green")
    )
    if c != 0 or not okish:
        print("Health check failed (curl rc=", c, ")")
        sys.exit(1)
    print("Deployment complete. MINDEX API is running.")
finally:
    client.close()
