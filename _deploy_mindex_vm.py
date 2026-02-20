#!/usr/bin/env python3
"""Deploy MINDEX API to VM 192.168.0.189 via SSH."""
import os
import sys
import time

# Load credentials from MAS repo
os.chdir(os.path.dirname(os.path.abspath(__file__)))
creds = os.path.join(os.path.dirname(__file__), ".credentials.local")
for line in open(creds).read().splitlines():
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()

password = os.environ.get("VM_SSH_PASSWORD") or os.environ.get("VM_PASSWORD")
if not password:
    print("ERROR: No VM_PASSWORD in .credentials.local")
    sys.exit(1)

import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("192.168.0.189", username="mycosoft", password=password, timeout=30)


def run(cmd):
    stdin, stdout, stderr = client.exec_command(cmd, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return stdout.channel.recv_exit_status(), out, err


def safe_print(s):
    print(s.encode("ascii", "replace").decode("ascii"))


try:
    print("=== 1. Fetch and reset code ===")
    c, o, e = run("cd /home/mycosoft/mindex && git fetch origin && git reset --hard origin/main")
    safe_print(o or e)
    if c != 0:
        print("FAILED")
        sys.exit(1)

    print("=== 2. Stop and remove API container ===")
    c, o, e = run("cd /home/mycosoft/mindex && docker-compose stop api; docker rm -f mindex-api 2>/dev/null || true")
    safe_print(o or e)

    print("=== 3. Build API (no cache) ===")
    c, o, e = run("cd /home/mycosoft/mindex && docker-compose build --no-cache api")
    if c != 0:
        safe_print(o or e)
        print("BUILD FAILED")
        sys.exit(1)
    print("Build completed OK")

    print("=== 4. Start API (--no-deps, db/redis/qdrant already running) ===")
    c, o, e = run("cd /home/mycosoft/mindex && docker-compose up -d --no-deps api")
    safe_print(o or e)
    if c != 0:
        print("Compose failed, trying docker run with host network...")
        run("docker rm -f mindex-api 2>/dev/null || true")
        # Use host network: postgres/redis/qdrant are on host ports 5432/6379/6333
        c2, o2, e2 = run(
            "docker run -d --name mindex-api --network host "
            "-e MINDEX_DB_HOST=127.0.0.1 -e MINDEX_DB_PORT=5432 "
            "-e MINDEX_DB_USER=mindex -e MINDEX_DB_PASSWORD=mindex -e MINDEX_DB_NAME=mindex "
            "mindex_api:latest uvicorn mindex_api.main:app --host 0.0.0.0 --port 8000"
        )
        safe_print(o2 or e2)
        if c2 != 0:
            print("START FAILED")
            sys.exit(1)

    print("=== 5. Wait 10s and verify ===")
    time.sleep(10)
    c, o, e = run("curl -s http://localhost:8000/api/mindex/health")
    resp = (o or e).strip()
    safe_print("Health: " + resp)
    if "ok" not in resp.lower() and c != 0:
        print("Health check failed")
        sys.exit(1)
    print("Deployment complete. MINDEX API is running.")
finally:
    client.close()
