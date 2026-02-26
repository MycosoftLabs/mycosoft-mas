#!/usr/bin/env python3
"""Deploy MAS (188) + Website (187) to sandbox and run smoke tests."""
import os
import paramiko
import time
from pathlib import Path

creds = Path(__file__).parent.parent / ".credentials.local"
for line in creds.read_text().splitlines():
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()

pw = os.environ.get("VM_SSH_PASSWORD") or os.environ.get("VM_PASSWORD")

def ssh(host):
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(host, username="mycosoft", password=pw, timeout=30)
    return c

def run(client, cmd, timeout=600, tail=20):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    rc = stdout.channel.recv_exit_status()
    combined = (out + err).strip()
    lines = combined.splitlines()
    for line in lines[-tail:]:
        print(f"  {line}")
    return combined, rc

ENV_PATH = "/home/mycosoft/mycosoft/mas/.env"

# ══════════════════════════════════════════════════════════════════
# MAS VM 188 — pull latest + rebuild + restart
# ══════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("MAS VM (192.168.0.188) — Pull + Build + Restart")
print("="*60)

mas = ssh("192.168.0.188")
run(mas, "cd /home/mycosoft/mycosoft/mas && git fetch origin && git reset --hard origin/main && echo GIT_OK")
run(mas, "cd /home/mycosoft/mycosoft/mas && docker build -t mycosoft/mas-agent:latest --no-cache . 2>&1 | tail -8", timeout=600)
run(mas, "docker stop myca-orchestrator-new 2>/dev/null; docker rm myca-orchestrator-new 2>/dev/null; echo STOPPED", timeout=30)
run(mas, f"docker run -d --name myca-orchestrator-new --restart unless-stopped -p 8001:8000 --env-file {ENV_PATH} mycosoft/mas-agent:latest", timeout=30)
mas.close()

print("\nWaiting 20s for MAS to start...")
time.sleep(20)

# ══════════════════════════════════════════════════════════════════
# Website VM 187 — pull latest + rebuild + restart
# ══════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("Website VM (192.168.0.187) — Pull + Build + Restart")
print("="*60)

web = ssh("192.168.0.187")
run(web, "cd /opt/mycosoft/website && git fetch origin && git reset --hard origin/main && echo GIT_OK")
run(web, "cd /opt/mycosoft/website && docker build -t mycosoft-always-on-mycosoft-website:latest --no-cache . 2>&1 | tail -8", timeout=600)
run(web, "docker stop mycosoft-website 2>/dev/null; docker rm mycosoft-website 2>/dev/null; echo STOPPED", timeout=30)
run(web, (
    "docker run -d --name mycosoft-website -p 3000:3000 "
    "-v /opt/mycosoft/media/website/assets:/app/public/assets:ro "
    "--restart unless-stopped mycosoft-always-on-mycosoft-website:latest"
), timeout=30)
web.close()

print("\nWaiting 30s for website to start...")
time.sleep(30)

# ══════════════════════════════════════════════════════════════════
# Smoke tests
# ══════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("SMOKE TESTS")
print("="*60)

import urllib.request, json

def check(label, url, method="GET", body=None, timeout=15):
    try:
        req = urllib.request.Request(url, method=method)
        if body:
            req.add_header("Content-Type", "application/json")
            req.data = json.dumps(body).encode()
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read().decode()[:300]
            print(f"  ✓ {label}: {r.status} — {data[:120]}")
            return True
    except Exception as e:
        print(f"  ✗ {label}: {e}")
        return False

check("MAS health", "http://192.168.0.188:8001/health")
check("MYCA chat", "http://192.168.0.188:8001/api/myca/chat", "POST",
      {"message": "what is the weather in chula vista", "session_id": "sandbox-smoke", "context": {}})
check("MINDEX health", "http://192.168.0.189:8000/api/mindex/health")
check("Website sandbox", "http://192.168.0.187:3000")
check("NLM embeddings API", "http://192.168.0.188:8001/api/nlm/embeddings/nature", "POST",
      {"packet": {"bme688": {"temperature_c": 22, "humidity_percent": 60}, "fci": {}}})

print("\nDone. Sandbox is ready for testing.")
print("→ https://sandbox.mycosoft.com")
