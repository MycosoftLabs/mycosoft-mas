#!/usr/bin/env python3
"""Blue/green deploy ONLY — feature branch with reports engine (JUL 11 2026).

Deploys origin/fix/soc-compliance-hydration-jul10 to 187 via scripts/blue-green-deploy.sh.
Does not merge to main. Does not touch non-website services.
"""

from __future__ import annotations

import os
import sys
import time
import urllib.request
from pathlib import Path

import paramiko

BRANCH = "fix/soc-compliance-hydration-jul10"
HOST = "192.168.0.187"


def load_creds() -> None:
    for p in (
        Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\.credentials.local"),
        Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\.credentials.local"),
    ):
        if not p.exists():
            continue
        for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
            if ln and not ln.startswith("#") and "=" in ln:
                k, v = ln.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def main() -> int:
    load_creds()
    pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    cf_zone = (
        os.environ.get("CLOUDFLARE_ZONE_ID_PRODUCTION")
        or os.environ.get("CLOUDFLARE_ZONE_ID")
        or ""
    )
    cf_token = os.environ.get("CLOUDFLARE_API_TOKEN") or ""
    if not pw:
        print("VM_PASSWORD missing", file=sys.stderr)
        return 1

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username="mycosoft", password=pw, timeout=30)

    # Escape for embedding in remote bash (no secret echo of CF token in logs beyond env)
    remote = f"""
set -euo pipefail
cd /opt/mycosoft/website
git fetch origin {BRANCH} main
git checkout -B {BRANCH} origin/{BRANCH}
SHA=$(git rev-parse --short HEAD)
echo "BLUEGREEN_SHA=$SHA BRANCH={BRANCH}"

IMAGE="ghcr.io/mycosoftlabs/website:bg-$SHA"
echo "Building $IMAGE ..."
docker build -f Dockerfile.production -t "$IMAGE" .

export IMAGE
export CF_ZONE_ID='{cf_zone}'
export CF_API_TOKEN='{cf_token}'
export PUBLIC_HOST=mycosoft.com
export DEPLOY_ENV_FILE=/opt/mycosoft/deploy.env
export ROLLBACK_WINDOW=60
chmod +x scripts/blue-green-deploy.sh
./scripts/blue-green-deploy.sh

echo "ACTIVE_SLOT=$(cat /opt/mycosoft/state/active-slot 2>/dev/null || echo unknown)"
curl -sS -o /dev/null -w 'local3000=%{{http_code}}\\n' http://127.0.0.1:3000/ || true
curl -sS -o /dev/null -w 'reports=%{{http_code}}\\n' http://127.0.0.1:3000/api/security/reports/generate || true
curl -sSI http://127.0.0.1:3000/healthz 2>/dev/null | grep -iE 'x-active-slot|HTTP/' || true
"""

    print("Starting blue/green on 187...", flush=True)
    _i, stdout, stderr = ssh.exec_command(remote, timeout=5400)
    channel = stdout.channel
    while not channel.exit_status_ready():
        if channel.recv_ready():
            sys.stdout.write(channel.recv(8192).decode("utf-8", "replace"))
            sys.stdout.flush()
        if channel.recv_stderr_ready():
            sys.stderr.write(channel.recv_stderr(8192).decode("utf-8", "replace"))
            sys.stderr.flush()
        time.sleep(0.2)
    code = channel.recv_exit_status()
    rest_out = stdout.read().decode("utf-8", "replace")
    rest_err = stderr.read().decode("utf-8", "replace")
    if rest_out:
        print(rest_out[-6000:])
    if rest_err:
        print(rest_err[-2000:], file=sys.stderr)
    ssh.close()
    print(f"Exit code: {code}", flush=True)

    if code == 0:
        for url in (
            "http://192.168.0.187:3000/api/security/reports/generate",
            "https://mycosoft.com/api/health",
        ):
            try:
                with urllib.request.urlopen(url, timeout=30) as r:
                    print(f"{url} -> {r.status}", flush=True)
            except Exception as ex:
                print(f"{url} -> {ex}", flush=True)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
