#!/usr/bin/env python3
"""Recreate MAS container with correct env (Postgres/Redis on MINDEX 189). No rebuild."""

import os
import sys
from pathlib import Path

creds_file = Path(__file__).parent.parent / ".credentials.local"
if creds_file.exists():
    for line in creds_file.read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD", "")
if not password:
    print("ERROR: VM_PASSWORD not set")
    sys.exit(1)

import paramiko

host, user = "192.168.0.188", "mycosoft"

# DB password from .env or use common one - avoid ! in shell by using env file or quotes
db_pass = os.environ.get("MINDEX_DB_PASSWORD", "Diamond1!")
# Escape for shell: use single-quoted URL, escape any single quotes in password
import urllib.parse
escaped_pass = urllib.parse.quote(db_pass, safe="")
db_url = f"postgresql://mycosoft:{escaped_pass}@192.168.0.189:5432/mindex"

cmd = (
    f"docker stop myca-orchestrator-new 2>/dev/null; "
    f"docker rm myca-orchestrator-new 2>/dev/null; "
    f"docker run -d --name myca-orchestrator-new --restart unless-stopped -p 8001:8000 "
    f"-e REDIS_URL=redis://192.168.0.189:6379/0 "
    f"-e MINDEX_DATABASE_URL='postgresql://mycosoft:{db_pass}@192.168.0.189:5432/mindex' "
    f"-e DATABASE_URL='postgresql://mycosoft:{db_pass}@192.168.0.189:5432/mindex' "
    f"-e N8N_URL=http://192.168.0.188:5678 "
    f"mycosoft/mas-agent:latest"
)

# Prefer --env-file so LLM keys (GEMINI, ANTHROPIC, OPENAI) from VM .env are used.
# Run scripts/sync_mas_env_to_vm.py first to push local .env to VM.
ENV_PATH = "/home/mycosoft/mycosoft/mas/.env"
cmd_with_env = (
    "docker stop myca-orchestrator-new 2>/dev/null; docker rm myca-orchestrator-new 2>/dev/null; "
    f"docker run -d --name myca-orchestrator-new --restart unless-stopped -p 8001:8000 "
    f"--env-file {ENV_PATH} "
    "mycosoft/mas-agent:latest"
)
cmd_simple = cmd_with_env  # Use env-file for consciousness/LLM keys

print("Connecting to MAS VM...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=password, timeout=30)

def run(c):
    i, o, e = ssh.exec_command(c)
    return o.channel.recv_exit_status(), o.read().decode("utf-8", "replace"), e.read().decode("utf-8", "replace")

# Use set -H to disable history expansion so ! in password is safe
rc, out, err = run("set +H; " + cmd_simple)
print(out or err)
if rc != 0:
    print("[FAIL] Container create failed")
    ssh.close()
    sys.exit(1)

print("Waiting 20s for startup...")
run("sleep 20")
rc, out, err = run("curl -s --connect-timeout 10 http://localhost:8001/health")
print("Health:", out or err)
ssh.close()

if "healthy" in (out or "").lower() or "postgresql" in (out or ""):
    print("\n[OK] MAS container recreated. Check health response above.")
else:
    print("\n[WARN] Verify health - Postgres/Redis on 189 must be reachable from 188.")
