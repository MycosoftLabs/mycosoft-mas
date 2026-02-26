#!/usr/bin/env python3
"""Quick Sandbox check - run all commands in one remote script to avoid timeouts."""
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
for line in (REPO_ROOT / ".credentials.local").read_text().splitlines():
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()
pwd = os.environ.get("VM_SSH_PASSWORD") or os.environ.get("VM_PASSWORD")

import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("192.168.0.187", username="mycosoft", password=pwd, timeout=30)

# Single remote script - avoids multiple SSH round-trips and docker lock contention
script = r'''
echo "===1 BUILD==="
ps aux | grep "docker build" | grep -v grep || echo "(none)"
echo "===2 CONTAINER==="
docker ps -a --filter name=mycosoft-website --format "{{.Names}} {{.Status}}" 2>/dev/null || echo "(error)"
echo "===3 CURL==="
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 || echo "000"
echo "===4 IMAGE==="
docker images | grep -E "mycosoft.*website|mycosoft-always" || echo "no match"
'''
stdin, stdout, stderr = c.exec_command("bash -c " + repr(script), timeout=120)
out = stdout.read().decode(errors="replace")
err = stderr.read().decode(errors="replace")
c.close()

# Parse output: ===1 BUILD=== \n lines \n ===2 CONTAINER=== ...
import re
m1 = re.search(r"===1 BUILD===\s*\n(.*?)(?=\n===2|$)", out, re.DOTALL)
m2 = re.search(r"===2 CONTAINER===\s*\n(.*?)(?=\n===3|$)", out, re.DOTALL)
m3 = re.search(r"===3 CURL===\s*\n(.*?)(?=\n===4|$)", out, re.DOTALL)
m4 = re.search(r"===4 IMAGE===\s*\n(.*?)$", out, re.DOTALL)
build_out = (m1.group(1) if m1 else "").strip()
cont_out = (m2.group(1) if m2 else "").strip()
http_out = (m3.group(1) if m3 else "").strip().split("\n")[0] or "000"
img_out = (m4.group(1) if m4 else "").strip()

build_running = bool(build_out and "docker build" in build_out)
cont_up = "Up" in cont_out
has_img = "mycosoft" in img_out and "no match" not in img_out

print("1) Docker build running?", "YES" if build_running else "NO")
print("   ", build_out[:200] if build_out else "(none)")
print("2) mycosoft-website container?", cont_out or "(none)")
print("3) curl localhost:3000?", http_out or "000")
print("4) Image exists?", "yes" if has_img else "no (docker images may have timed out)")

if not build_running and not cont_up and (has_img or True):  # try start if down (image check unreliable when docker slow)
    print("5) Starting container...")
    c2 = paramiko.SSHClient()
    c2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c2.connect("192.168.0.187", username="mycosoft", password=pwd, timeout=30)
    stdin, stdout, stderr = c2.exec_command(
        "docker rm -f mycosoft-website 2>/dev/null; "
        "docker run -d --name mycosoft-website -p 3000:3000 "
        "-v /opt/mycosoft/media/website/assets:/app/public/assets:ro "
        "-e MAS_API_URL=http://192.168.0.188:8001 --restart unless-stopped "
        "mycosoft-always-on-mycosoft-website:latest", timeout=60
    )
    out2 = stdout.read().decode()
    code = stdout.channel.recv_exit_status()
    import time
    time.sleep(8)
    stdin, stdout, stderr = c2.exec_command("curl -s -o /dev/null -w '%{http_code}' http://localhost:3000", timeout=15)
    http_final = stdout.read().decode().strip() or "000"
    c2.close()
    print("   ", "OK" if code == 0 else f"FAIL {out2}")
    print("   Post-start curl:", http_final)
    http_out = http_final
    cont_up = code == 0

print("\n=== FINAL STATUS ===")
print("1. Docker build running:", "yes" if build_running else "no")
print("2. mycosoft-website container:", "up" if cont_up else "down")
print("3. curl localhost:3000:", http_out or "000")
print("4. Image exists:", "yes" if has_img else "no")