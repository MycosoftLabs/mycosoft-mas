#!/usr/bin/env python3
"""One-shot deploy website to Sandbox VM 187. Loads creds, SSH, build, restart, purge."""
import os
import sys
from pathlib import Path

# Load credentials
creds = Path(__file__).resolve().parent.parent / ".credentials.local"
if creds.exists():
    for line in creds.read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

import paramiko

VM = "192.168.0.187"
USER = "mycosoft"
PASSWORD = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")
WEB_DIR = "/opt/mycosoft/website"

if not PASSWORD:
    print("ERROR: VM_PASSWORD not set. Load .credentials.local")
    sys.exit(1)

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(VM, username=USER, password=PASSWORD, timeout=30)

def run(cmd, timeout=600, read_timeout=3600):
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    chan = stdout.channel
    chan.settimeout(read_timeout)  # Allow long docker build
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return chan.recv_exit_status(), out, err

try:
    print("1. Pulling code...")
    ec, out, err = run(f"cd {WEB_DIR} && git fetch origin && git reset --hard origin/main && git log -1 --oneline")
    if ec != 0:
        print("FAIL: git pull:", err[:800])
        sys.exit(1)
    print(out.strip())

    print("2. Building Docker image (no cache)...")
    ec, out, err = run(f"cd {WEB_DIR} && docker build --no-cache -t mycosoft-always-on-mycosoft-website:latest . 2>&1", timeout=1200, read_timeout=1800)
    if ec != 0:
        print("FAIL: Docker build. Last 1500 chars:", (err or out)[-1500:])
        sys.exit(1)
    print("Build OK")

    print("3. Stopping old container...")
    run("docker stop mycosoft-website 2>/dev/null; docker rm mycosoft-website 2>/dev/null; echo done")

    print("4. Starting new container with NAS mount...")
    ec, out, err = run(
        "docker run -d --name mycosoft-website -p 3000:3000 "
        "-v /opt/mycosoft/media/website/assets:/app/public/assets:ro "
        "--restart unless-stopped mycosoft-always-on-mycosoft-website:latest"
    )
    if ec != 0:
        print("FAIL: Container start:", err[:800])
        sys.exit(1)
    print("Container started")

    print("5. Health check...")
    ec, out, err = run("sleep 5 && curl -s -o /dev/null -w '%{http_code}' http://localhost:3000")
    print("HTTP status:", out.strip() if out.strip() else "(wait longer)")

finally:
    client.close()

print("Deploy complete. Purge Cloudflare cache separately if needed.")
