#!/usr/bin/env python3
"""One-time deploy MAS (188) and MINDEX (189). Loads creds from .credentials.local."""
import os
import sys
from pathlib import Path

# Load credentials from MAS repo .credentials.local
REPO_ROOT = Path(__file__).resolve().parent.parent
CREDS_FILE = REPO_ROOT / ".credentials.local"
if not CREDS_FILE.exists():
    print("ERROR: .credentials.local not found")
    sys.exit(1)
for line in CREDS_FILE.read_text().splitlines():
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()

password = os.environ.get("VM_SSH_PASSWORD") or os.environ.get("VM_PASSWORD")
if not password:
    print("ERROR: VM_SSH_PASSWORD or VM_PASSWORD not set")
    sys.exit(1)

try:
    import paramiko
except ImportError:
    print("ERROR: paramiko not installed. Run: poetry install")
    sys.exit(1)

def run_ssh(host: str, user: str, commands: list[str], desc: str) -> bool:
    print(f"\n--- {desc} @ {host} ---")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(host, username=user, password=password, timeout=30)
    except Exception as e:
        print(f"SSH connect failed: {e}")
        return False
    ok = True
    for cmd in commands:
        print(f"$ {cmd[:80]}{'...' if len(cmd) > 80 else ''}")
        stdin, stdout, stderr = client.exec_command(cmd, timeout=600)
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        code = stdout.channel.recv_exit_status()
        if out:
            for line in out.strip().splitlines()[-20:]:  # last 20 lines
                print(f"  {line}")
        if err and code != 0:
            print(f"  stderr: {err[:500]}")
        if code != 0:
            print(f"  exit code: {code}")
            ok = False
    client.close()
    return ok

# --- MAS VM 188 ---
mas_ok = run_ssh(
    "192.168.0.188",
    "mycosoft",
    [
        "cd /home/mycosoft/mycosoft/mas && git fetch origin && git reset --hard origin/main",
        "cd /home/mycosoft/mycosoft/mas && docker build -t mycosoft/mas-agent:latest --no-cache .",
        "docker stop myca-orchestrator-new 2>/dev/null || true; docker rm myca-orchestrator-new 2>/dev/null || true",
        "docker run -d --name myca-orchestrator-new --restart unless-stopped -p 8001:8000 --env-file /home/mycosoft/mycosoft/mas/.env mycosoft/mas-agent:latest",
    ],
    "MAS Deploy",
)

# --- MINDEX VM 189 ---
# Build api image; VM may have existing db/redis (name conflict). Start api only:
# docker run on mindex_mindex-network with MINDEX_DB_HOST=mindex-postgres.
mindex_ok = run_ssh(
    "192.168.0.189",
    "mycosoft",
    [
        "cd /home/mycosoft/mindex && git fetch origin && git reset --hard origin/main",
        "cd /home/mycosoft/mindex && docker-compose build --no-cache api",
        "docker rm -f mindex-api 2>/dev/null; docker run -d --name mindex-api --restart unless-stopped -p 8000:8000 --network mindex_mindex-network -e MINDEX_DB_HOST=mindex-postgres -e MINDEX_DB_PORT=5432 -e MINDEX_DB_USER=mindex -e MINDEX_DB_PASSWORD=mindex -e MINDEX_DB_NAME=mindex mindex_api:latest",
    ],
    "MINDEX Deploy",
)

# --- Verify ---
print("\n--- Verifying ---")
import urllib.request
try:
    r = urllib.request.urlopen("http://192.168.0.188:8001/health", timeout=10)
    print(f"MAS health: {r.read().decode()[:200]}")
except Exception as e:
    print(f"MAS health check failed: {e}")
    mas_ok = False
try:
    r = urllib.request.urlopen("http://192.168.0.189:8000/api/mindex/health", timeout=10)
    print(f"MINDEX health: {r.read().decode()[:200]}")
except Exception as e:
    print(f"MINDEX health check failed: {e}")
    mindex_ok = False

print("\n--- Done ---")
sys.exit(0 if (mas_ok and mindex_ok) else 1)
