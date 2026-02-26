#!/usr/bin/env python3
"""Restart MAS container and run quick smoke tests."""
import os, paramiko, time, urllib.request, json
from pathlib import Path

creds = Path(__file__).parent.parent / ".credentials.local"
for line in creds.read_text().splitlines():
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()

pw = os.environ.get("VM_SSH_PASSWORD")
ENV_PATH = "/home/mycosoft/mycosoft/mas/.env"

def ssh(host):
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(host, username="mycosoft", password=pw, timeout=15)
    return c

def run(c, cmd, timeout=20):
    stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    rc = stdout.channel.recv_exit_status()
    return (out + err).strip(), rc

# Restart MAS container
print("=== Restarting MAS container ===")
c = ssh("192.168.0.188")
out, _ = run(c, "docker ps --filter name=myca-orchestrator-new --format '{{.Status}}'")
print(f"Current status: {out}")
run(c, "docker restart myca-orchestrator-new 2>&1", timeout=30)
c.close()

print("Waiting 25s for startup...")
time.sleep(25)

# Check health
print("\n=== Health checks ===")
def check(label, url):
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            print(f"  OK  {label}: {r.status}")
            return True
    except Exception as e:
        print(f"  FAIL {label}: {e}")
        return False

check("MAS", "http://192.168.0.188:8001/health")
check("MINDEX", "http://192.168.0.189:8000/api/mindex/health")
check("Sandbox website", "http://192.168.0.187:3000")

# Test MYCA chat via MAS directly
print("\n=== MYCA chat via MAS ===")
c = ssh("192.168.0.188")
out, _ = run(c, "curl -s http://localhost:8001/health | head -c 100", timeout=10)
print(f"MAS health: {out}")
out, _ = run(c, (
    "curl -s -X POST http://localhost:8001/api/myca/chat "
    "-H 'Content-Type: application/json' "
    "-d '{\"message\": \"hello MYCA what can you do\", \"session_id\": \"smoke\", \"context\": {}}' "
    "--max-time 25"
), timeout=30)
if out:
    try:
        d = json.loads(out)
        print(f"Chat response: {d.get('message', out[:300])[:300]}")
    except Exception:
        print(f"Chat raw: {out[:300]}")
else:
    print("No response from chat")
c.close()

print("\n=== MYCA chat via sandbox website orchestrator ===")
try:
    req = urllib.request.Request("https://sandbox.mycosoft.com/api/mas/voice/orchestrator", method="POST")
    req.add_header("Content-Type", "application/json")
    req.data = json.dumps({"message": "hello MYCA what is the weather in chula vista", "session_id": "sandbox-final", "context": {}}).encode()
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read())
        print(f"Provider: {d.get('routed_to', '?')}")
        print(f"Response: {d.get('response_text', '?')[:300]}")
except Exception as e:
    print(f"Sandbox orchestrator error: {e}")

print("\nDone. Go test at: https://sandbox.mycosoft.com/myca")
