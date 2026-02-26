#!/usr/bin/env python3
"""
Sync local MAS .env (including LLM API keys) to MAS VM and restart container.

Use when you've added/updated API keys locally and need them on the MAS VM (192.168.0.188).
Loads credentials from .credentials.local. Never commits .env.
"""
import os
import sys
import time
from pathlib import Path

creds_file = Path(__file__).parent.parent / ".credentials.local"
if creds_file.exists():
    for line in creds_file.read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD", "")
if not pw:
    print("ERROR: VM_PASSWORD or VM_SSH_PASSWORD not set (from .credentials.local)")
    sys.exit(1)

import paramiko

MAS_HOST = "192.168.0.188"
MAS_USER = "mycosoft"
REMOTE_ENV_PATH = "/home/mycosoft/mycosoft/mas/.env"
REMOTE_MAS_DIR = "/home/mycosoft/mycosoft/mas"

local_env = Path(__file__).parent.parent / ".env"
if not local_env.exists():
    print(f"ERROR: Local .env not found at {local_env}")
    sys.exit(1)

content = local_env.read_text(encoding="utf-8")

# Ensure VM-required vars for MAS container (Redis on 189)
if "REDIS_URL=" not in content:
    content = "REDIS_URL=redis://192.168.0.189:6379/0\n" + content
if "N8N_URL=" not in content:
    content = content.rstrip() + "\nN8N_URL=http://192.168.0.188:5678\n"

print("Connecting to MAS VM...")
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(MAS_HOST, username=MAS_USER, password=pw, timeout=30)

def run(cmd, timeout=30):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    rc = stdout.channel.recv_exit_status()
    return (out + err).strip(), rc

# Ensure remote directory exists
run(f"mkdir -p {Path(REMOTE_ENV_PATH).parent}")

# Write .env via SFTP (avoids shell escaping issues with special chars in keys)
sftp = client.open_sftp()
try:
    with sftp.file(REMOTE_ENV_PATH, "w") as f:
        f.write(content)
    print(f"Synced .env to {REMOTE_ENV_PATH}")
except Exception as e:
    print(f"SFTP write failed: {e}")
    sftp.close()
    client.close()
    sys.exit(1)
sftp.close()

# Verify LLM keys present
out, _ = run(f"grep -E '^(GEMINI_API_KEY|ANTHROPIC_API_KEY|OPENAI_API_KEY)=' {REMOTE_ENV_PATH} | sed 's/=.*/=***/'")
print(f"LLM keys on VM: {out}")

# Restart MAS container with env-file
print("\nRestarting MAS container with --env-file...")
run("docker stop myca-orchestrator-new 2>/dev/null; docker rm myca-orchestrator-new 2>/dev/null", timeout=20)
out, rc = run(
    f"docker run -d --name myca-orchestrator-new --restart unless-stopped "
    f"-p 8001:8000 --env-file {REMOTE_ENV_PATH} mycosoft/mas-agent:latest",
    timeout=20,
)
if rc != 0:
    print(f"Container start failed: {out}")
    client.close()
    sys.exit(1)
print(f"Container started: {out[:80]}")

print("Waiting 20s for MAS to start...")
time.sleep(20)

# Test health
out, _ = run("curl -s --connect-timeout 10 http://localhost:8001/health", timeout=15)
print(f"\nHealth: {out[:200]}")

# Test consciousness/chat
print("\nTesting MYCA chat (consciousness)...")
out, _ = run(
    "curl -s -X POST http://localhost:8001/api/myca/chat "
    "-H 'Content-Type: application/json' "
    "-d '{\"message\": \"what is your name\", \"session_id\": \"sync-test\"}' "
    "--max-time 25",
    timeout=30,
)
if out and "MYCA" in out and "difficulty" not in out.lower():
    print(f"Consciousness OK: {out[:150]}...")
else:
    print(f"Chat response: {out[:300]}")

client.close()
print("\nDone. MAS now has LLM keys; consciousness should respond.")
