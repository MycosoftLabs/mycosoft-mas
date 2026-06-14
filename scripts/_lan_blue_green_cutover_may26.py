#!/usr/bin/env python3
"""LAN blue/green cutover only — pull GHCR image, run blue-green-deploy.sh. NO docker build."""
import os
import sys
import time
import paramiko
import urllib.request
from pathlib import Path

SHA = os.environ.get("DEPLOY_SHA", "")
IMAGE = os.environ.get("DEPLOY_IMAGE", "ghcr.io/mycosoftlabs/website:production-latest")
if SHA:
    IMAGE = f"ghcr.io/mycosoftlabs/website:manual-{SHA}"

for p in (
    Path(r"d:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\.credentials.local"),
    Path(r"d:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\.credentials.local"),
):
    if p.exists():
        for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
            if ln and not ln.startswith("#") and "=" in ln:
                k, v = ln.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD", "")
cf_zone = os.environ.get("CLOUDFLARE_ZONE_ID") or os.environ.get("CLOUDFLARE_ZONE_ID_PRODUCTION", "")
cf_token = os.environ.get("CLOUDFLARE_API_TOKEN") or os.environ.get("CLOUDFLARE_API_TOKEN_MYCODAO", "")
ghcr_user = os.environ.get("GHCR_USER", "")
ghcr_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GHCR_TOKEN", "")

CUTOVER = f"""
set -euo pipefail
cd /opt/mycosoft/website
export IMAGE="{IMAGE}"
export CF_ZONE_ID="{cf_zone}"
export CF_API_TOKEN="{cf_token}"
export PUBLIC_HOST=mycosoft.com
export LOCK_DIR="$HOME/.cache/mycosoft-deploy"
mkdir -p "$LOCK_DIR"

echo "=== Pre-cutover origin health ==="
curl -sf --max-time 10 http://127.0.0.1:3000/api/health >/dev/null && echo ORIGIN_UP || echo ORIGIN_DOWN

echo "=== Pull $IMAGE ==="
docker pull "$IMAGE"

echo "=== Blue/green cutover ==="
chmod +x scripts/blue-green-deploy.sh 2>/dev/null || true
./scripts/blue-green-deploy.sh

echo "=== Post-cutover ==="
cat /opt/mycosoft/state/active-slot
curl -sf --max-time 15 http://127.0.0.1:3000/api/health && echo " ORIGIN_OK"
"""


def check_public():
    try:
        r = urllib.request.urlopen("https://mycosoft.com/api/health", timeout=20)
        return r.status
    except Exception as ex:
        return str(ex)


def main():
    print(f"Public before: {check_public()}", flush=True)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("192.168.0.187", username="mycosoft", password=pw, timeout=25)

    if ghcr_token:
        login = f"echo '{ghcr_token}' | docker login ghcr.io -u '{ghcr_user or 'mycosoft'}' --password-stdin"
        _, o, e = ssh.exec_command(login, timeout=60)
        o.channel.recv_exit_status()
        print("GHCR login:", o.read().decode().strip() or e.read().decode()[:200])

    _, o, e = ssh.exec_command(CUTOVER, timeout=600)
    code = o.channel.recv_exit_status()
    for line in (o.read() + e.read()).decode("utf-8", errors="replace").splitlines():
        if "eyJ" in line and len(line) > 60:
            continue
        print(line, flush=True)
    ssh.close()
    time.sleep(5)
    print(f"Public after: {check_public()}", flush=True)
    sys.exit(0 if code == 0 else code)


if __name__ == "__main__":
    main()
