#!/usr/bin/env python3
"""Deploy website to VM 187 using background build to avoid SSH timeout."""
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

def ssh():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("192.168.0.187", username="mycosoft", password=pw, timeout=30)
    return c

def run(c, cmd, timeout=30):
    stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    rc = stdout.channel.recv_exit_status()
    return (out + err).strip(), rc

# Step 1: Git pull
print("=== Git pull on VM 187 ===")
c = ssh()
out, rc = run(c, "cd /opt/mycosoft/website && git fetch origin && git reset --hard origin/main && echo PULL_OK", timeout=60)
print(out[-300:])
c.close()

# Step 2: Background docker build (won't time out)
print("\n=== Starting background Docker build on VM 187 ===")
c = ssh()
out, rc = run(c, (
    "nohup bash -c '"
    "cd /opt/mycosoft/website && "
    "docker build -t mycosoft-always-on-mycosoft-website:latest --no-cache . "
    "> /tmp/website_build.log 2>&1 && "
    "docker stop mycosoft-website 2>/dev/null; "
    "docker rm mycosoft-website 2>/dev/null; "
    "docker run -d --name mycosoft-website -p 3000:3000 "
    "-v /opt/mycosoft/media/website/assets:/app/public/assets:ro "
    "--restart unless-stopped mycosoft-always-on-mycosoft-website:latest "
    "> /tmp/website_start.log 2>&1 && "
    "echo BUILD_DONE > /tmp/website_build_done.flag"
    "' > /tmp/nohup_build.out 2>&1 &"
    "echo $!"
), timeout=15)
pid = out.strip()
print(f"Build PID: {pid}")
c.close()

# Step 3: Poll until done
print("\nPolling for build completion (check every 30s)...")
for attempt in range(25):  # up to ~12 minutes
    time.sleep(30)
    c = ssh()
    out, rc = run(c, "test -f /tmp/website_build_done.flag && echo DONE || tail -3 /tmp/website_build.log 2>/dev/null || echo BUILDING", timeout=10)
    print(f"  [{attempt+1}] {out[:200]}")
    if "DONE" in out:
        print("Build complete!")
        # Check container is running
        out2, _ = run(c, "docker ps --filter name=mycosoft-website --format '{{.Status}}'", timeout=10)
        print(f"  Container status: {out2}")
        c.close()
        break
    c.close()
else:
    print("Build timed out — check /tmp/website_build.log on VM 187")

# Step 4: Smoke tests
print("\n=== Smoke tests ===")
import urllib.request, json

def check(label, url, method="GET", body=None):
    try:
        req = urllib.request.Request(url, method=method)
        if body:
            req.add_header("Content-Type", "application/json")
            req.data = json.dumps(body).encode()
        with urllib.request.urlopen(req, timeout=15) as r:
            data = r.read().decode()[:200]
            print(f"  ✓ {label}: {r.status}")
            return True
    except Exception as e:
        print(f"  ✗ {label}: {e}")
        return False

check("MAS health", "http://192.168.0.188:8001/health")
check("MINDEX health", "http://192.168.0.189:8000/api/mindex/health")
check("Website sandbox", "http://192.168.0.187:3000")
check("MYCA chat (MAS)", "http://192.168.0.188:8001/api/myca/chat", "POST",
      {"message": "what is the weather in chula vista", "session_id": "deploy-smoke", "context": {}})
check("NLM API", "http://192.168.0.188:8001/api/nlm/embeddings/nature", "POST",
      {"packet": {"bme688": {"temperature_c": 22, "humidity_percent": 60}, "fci": {}}})

print("\n→ Test MYCA at: https://sandbox.mycosoft.com")
print("→ Test MYCA chat on: https://sandbox.mycosoft.com/myca")
