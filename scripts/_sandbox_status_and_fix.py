#!/usr/bin/env python3
"""Check Sandbox VM status: docker build, website container, curl. Start container if down but image exists."""
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CREDS_FILE = REPO_ROOT / ".credentials.local"
for line in CREDS_FILE.read_text().splitlines():
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()
password = os.environ.get("VM_SSH_PASSWORD") or os.environ.get("VM_PASSWORD")

import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("192.168.0.187", username="mycosoft", password=password, timeout=30)

def run(cmd, timeout=60):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    code = stdout.channel.recv_exit_status()
    return out, err, code

print("=== 1) Docker build still running? ===")
out, _, _ = run("ps aux | grep -E 'docker build' | grep -v grep || true")
print(out if out.strip() else "(none)")
build_running = bool(out.strip())

print("\n=== 2) mycosoft-website container running? ===")
out, _, _ = run("docker ps -a --filter name=mycosoft-website --format '{{.Names}} {{.Status}}'")
print(out if out.strip() else "(none)")
container_running = "Up" in out

print("\n=== 3) curl localhost:3000 status? ===")
out, _, code = run("curl -s -o /dev/null -w '%{http_code}' http://localhost:3000")
print(out or "000")

print("\n=== 4) Image exists? ===")
out, _, _ = run("docker images mycosoft-always-on-mycosoft-website:latest --format '{{.Tag}} {{.CreatedAt}}'")
print(out if out.strip() else "(none)")
image_exists = bool(out.strip())

# If build failed - check docker build logs / last output (we can't get build output easily;
# the deploy script captures it. Check if there's a recent failed build by looking at docker events or builder logs)
# For "last 40 lines" - we'd need journalctl or docker builder log. Try: docker build --progress=plain 2>&1 | tail -40
# But that would start a new build. Instead check: journalctl -u docker --no-pager -n 50 or docker system info
# Actually the user said "if build failed again, get last 40 lines of output" - the build runs remotely via SSH.
# The deploy script's output is in the terminal. We can't easily get that from here. We could check
# if there's a docker build process - if it's gone and container is down, the build likely failed.
# Let me add a check: run `docker builder prune` or `docker buildx ls` to see build state.
# Simpler: if build_running is False and container_running is False, we assume build failed.
# For "last 40 lines" - we'd need to run a build and capture output, or the deploy stores logs somewhere.
# I'll run a quick check: `docker buildx du` or just note "build not running" and if container down, start it.
if not build_running and not container_running and image_exists:
    print("\n=== 5) Starting container (image exists, container down) ===")
    run("docker rm -f mycosoft-website 2>/dev/null || true")  # remove any stopped container
    start_cmd = """docker run -d --name mycosoft-website -p 3000:3000 \
        -v /opt/mycosoft/media/website/assets:/app/public/assets:ro \
        -e MAS_API_URL=http://192.168.0.188:8001 \
        --restart unless-stopped mycosoft-always-on-mycosoft-website:latest"""
    out, err, code = run(start_cmd)
    print("stdout:", out)
    if err:
        print("stderr:", err)
    print("exit code:", code)
    if code == 0:
        import time
        time.sleep(5)
        out, _, _ = run("curl -s -o /dev/null -w '%{http_code}' http://localhost:3000")
        print("Post-start curl:", out or "000")

# For "last 40 lines if build failed"
if not build_running and not container_running:
    print("\n=== 4b) Build failure context (docker/journal last ~40 lines) ===")
    out, _, _ = run("journalctl -u docker --no-pager -n 60 2>/dev/null | tail -40 || docker events --since 30m --until 0s 2>/dev/null | tail -20 || echo '(no logs)'")
    print(out[:2500] if out.strip() else "(no build logs available)")

# Final curl
out, _, _ = run("curl -s -o /dev/null -w '%{http_code}' http://localhost:3000")
http_final = out.strip() or "000"
client.close()

print("\n=== FINAL STATUS ===")
print(f"1. Docker build running: {build_running}")
print(f"2. mycosoft-website container running: {container_running}")
print(f"3. Image exists: {image_exists}")
print(f"4. curl localhost:3000 HTTP status: {http_final}")
