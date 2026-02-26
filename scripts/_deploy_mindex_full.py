#!/usr/bin/env python3
"""Deploy MINDEX: pull, apply migration 0014, rebuild, restart. Loads creds from MAS .credentials.local"""
import os
import sys
import time
from pathlib import Path

root = Path(__file__).resolve().parent.parent
creds = root / ".credentials.local"
if creds.exists():
    for line in creds.read_text().splitlines():
        if line and "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

pw = os.environ.get("VM_SSH_PASSWORD") or os.environ.get("VM_PASSWORD")
if not pw:
    print("ERROR: VM_SSH_PASSWORD not in .credentials.local"); sys.exit(1)

import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("192.168.0.189", username="mycosoft", password=pw, timeout=60)

def run(cmd, timeout=120):
    _, o, e = c.exec_command(cmd, timeout=timeout)
    code = o.channel.recv_exit_status()
    out = o.read().decode("utf-8", errors="replace")
    err = e.read().decode("utf-8", errors="replace")
    if out.strip():
        print(out[-2000:] if len(out) > 2000 else out)
    if err.strip() and "Warning" not in err:
        print("STDERR:", err[-500:] if len(err) > 500 else err)
    return code, out

# MINDEX path - /home/mycosoft/mindex or /opt/mycosoft/mindex
_, out = run("test -d /home/mycosoft/mindex && echo /home/mycosoft/mindex || echo /opt/mycosoft/mindex", timeout=5)
MINDEX_DIR = out.strip().splitlines()[-1].strip() if out.strip() else "/home/mycosoft/mindex"

print("1. Pull latest...")
run(f"cd {MINDEX_DIR} && git fetch origin && git reset --hard origin/main && git log -1 --oneline")

print("2. Apply migration 0014_nlm_training.sql...")
run(f"cat {MINDEX_DIR}/migrations/0014_nlm_training.sql | docker exec -i mindex-postgres psql -U mindex -d mindex 2>&1 | tail -15")

print("3. Rebuild image...")
code, _ = run(f"cd {MINDEX_DIR} && docker build -t mindex-api:latest --no-cache . 2>&1 | tail -25", timeout=300)
if code != 0:
    print("Build failed"); c.close(); sys.exit(1)

print("4. Restart container...")
run("docker stop mindex-api 2>/dev/null; docker rm mindex-api 2>/dev/null; true")
out, _ = run("docker network ls --format '{{.Name}}' | grep -i mindex | head -1", timeout=10)
net = out.strip().split("\n")[0] if out.strip() else "mindex_default"
run(f"""docker run -d --name mindex-api --network {net} -p 8000:8000 \\
  -e MINDEX_DB_HOST=mindex-postgres -e MINDEX_DB_PORT=5432 \\
  -e MINDEX_DB_USER=mindex -e MINDEX_DB_PASSWORD=mindex_secure_password \\
  -e MINDEX_DB_NAME=mindex \\
  -e API_CORS_ORIGINS='[\"http://localhost:3000\",\"http://localhost:3010\",\"http://192.168.0.187:3000\"]' \\
  --restart unless-stopped mindex-api:latest""")

time.sleep(8)
print("5. Verify...")
run("curl -s http://localhost:8000/api/mindex/health")
c.close()
print("MINDEX deploy done.")
