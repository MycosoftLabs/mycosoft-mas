"""Idle-slot only: remove wedged leftover, start blue from GHCR, cutover if healthy.

Never stops the serving primary. Never prints secrets.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import paramiko

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

IMAGE = "ghcr.io/mycosoftlabs/website:manual-045eaa29637135c932829df36e862c832f3eb7d0"
CREDS = Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\.credentials.local")


def load_creds() -> str:
    for line in CREDS.read_text(encoding="utf-8", errors="replace").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())
    return os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""


def ssh() -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect("192.168.0.187", username="mycosoft", password=load_creds(), timeout=30)
    return client


def run(client: paramiko.SSHClient, command: str, timeout: int = 120) -> tuple[int, str]:
    _, stdout, stderr = client.exec_command(command, timeout=timeout)
    code = stdout.channel.recv_exit_status()
    return code, (stdout.read() + stderr.read()).decode("utf-8", "replace")


def main() -> int:
    phase = sys.argv[1] if len(sys.argv) > 1 else "status"
    client = ssh()
    try:
        if phase == "status":
            code, out = run(
                client,
                """
set -e
echo ACTIVE=$(cat /opt/mycosoft/state/active-slot)
echo ORIGIN=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 8 http://127.0.0.1:3000/api/health)
docker ps -a --format '{{.Names}} {{.Status}}' | sed -n '1,20p'
ps -ef | grep blue-green-deploy | grep -v grep || echo NO_BG
""",
            )
            print(out)
            return code

        if phase == "rm-leftover":
            code, out = run(
                client,
                """
set -euo pipefail
ACTIVE=$(tr -d '[:space:]' </opt/mycosoft/state/active-slot)
echo ACTIVE=$ACTIVE
if [ "$ACTIVE" != "green" ]; then echo REFUSING leftover cleanup — expected green primary; exit 20; fi
curl -fsS --max-time 8 http://127.0.0.1:3000/api/health >/dev/null
# leftover Created container is not serving
if docker ps -a --format '{{.Names}}' | grep -qx 'a22d1420a982_mycosoft-website-blue'; then
  ST=$(docker inspect -f '{{.State.Status}}' a22d1420a982_mycosoft-website-blue)
  echo leftover_status=$ST
  if [ "$ST" = "created" ] || [ "$ST" = "exited" ]; then
    docker rm -f a22d1420a982_mycosoft-website-blue
    echo leftover_removed
  else
    echo leftover_not_safe status=$ST
    exit 21
  fi
else
  echo leftover_absent
fi
docker ps -a --format '{{.Names}} {{.Status}}' | sed -n '1,15p'
echo ORIGIN=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 8 http://127.0.0.1:3000/api/health)
""",
                timeout=90,
            )
            print(out)
            return code

        if phase == "isolate-dstate-start-idle":
            code, out = run(
                client,
                f"""
set -euo pipefail
ACTIVE=$(tr -d '[:space:]' </opt/mycosoft/state/active-slot)
echo ACTIVE=$ACTIVE
if [ "$ACTIVE" != "green" ]; then echo REFUSING; exit 20; fi
curl -fsS --max-time 8 http://127.0.0.1:3000/api/health >/dev/null
if docker ps --format '{{.Names}}' | grep -qx mycosoft-website-green; then
  docker inspect -f 'green={{{{.State.Health.Status}}}}' mycosoft-website-green | grep -q healthy
fi
# Do not docker stop D-state. Best-effort isolate, then run a new idle name+alias.
docker update --restart=no mycosoft-website-blue >/dev/null || true
timeout 12 docker rename mycosoft-website-blue mycosoft-website-blue-wedged-sep09 && echo renamed || echo rename_timeout
NET=$(docker inspect -f '{{{{range $k,$v := .NetworkSettings.Networks}}}}{{{{$k}}}}{{{{end}}}}' mycosoft-website-green)
echo NET=$NET
if docker ps -a --format '{{.Names}}' | grep -qx mycosoft-website-blue; then
  echo NAME_STILL_HELD
else
  echo NAME_FREE
fi
if ! docker ps -a --format '{{.Names}}' | grep -qx mycosoft-website-blue; then
  docker run -d \
    --name mycosoft-website-blue \
    --restart unless-stopped \
    --network "$NET" \
    --network-alias website-blue \
    --env-file /opt/mycosoft/website/.env \
    -e NODE_ENV=production \
    -e PORT=3000 \
    -e HOSTNAME=0.0.0.0 \
    -e NODE_OPTIONS=--max-http-header-size=32768 \
    -e DEPLOY_SLOT=blue \
    -v /opt/mycosoft/media/website/assets:/app/public/assets:ro \
    {IMAGE}
  echo started_new_blue
else
  echo starting_alias_candidate
  docker run -d \
    --name mycosoft-website-blue-itdx \
    --restart unless-stopped \
    --network "$NET" \
    --network-alias website-blue-itdx \
    --env-file /opt/mycosoft/website/.env \
    -e NODE_ENV=production \
    -e PORT=3000 \
    -e HOSTNAME=0.0.0.0 \
    -e NODE_OPTIONS=--max-http-header-size=32768 \
    -e DEPLOY_SLOT=blue \
    -v /opt/mycosoft/media/website/assets:/app/public/assets:ro \
    {IMAGE}
  echo started_blue_itdx
fi
docker ps --format '{{.Names}} {{.Status}}' | sed -n '1,15p'
echo ORIGIN=$(curl -sS -o /dev/null -w '%{{http_code}}' --max-time 8 http://127.0.0.1:3000/api/health)
""",
                timeout=180,
            )
            print(out)
            return code

        if phase == "replace-idle-and-cutover":
            code, out = run(
                client,
                f"""
set -euo pipefail
cd /opt/mycosoft/website
ACTIVE=$(tr -d '[:space:]' </opt/mycosoft/state/active-slot)
echo ACTIVE=$ACTIVE
if [ "$ACTIVE" != "green" ]; then echo REFUSING — primary is not green; exit 20; fi
curl -fsS --max-time 8 http://127.0.0.1:3000/api/health >/dev/null
if ps -ef | grep -E '[b]lue-green-deploy.sh' >/dev/null; then
  echo REFUSING — blue-green-deploy already running
  exit 22
fi
# idle only
if docker ps -a --format '{{.Names}}' | grep -qx mycosoft-website-blue; then
  echo stopping idle mycosoft-website-blue
  docker stop -t 20 mycosoft-website-blue || true
  docker rm -f mycosoft-website-blue || true
fi
export IMAGE="{IMAGE}"
export PUBLIC_HOST=mycosoft.com
export LOCK_DIR="$HOME/.cache/mycosoft-deploy"
export LOCK_FILE="$LOCK_DIR/blue-green.lock"
mkdir -p "$LOCK_DIR"
# CF from deploy.env on VM — never echo
set -a
if [ -f /opt/mycosoft/deploy.env ]; then
  source <(grep -E '^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*=' /opt/mycosoft/deploy.env)
fi
set +a
chmod +x scripts/blue-green-deploy.sh
./scripts/blue-green-deploy.sh
echo POST_ACTIVE=$(cat /opt/mycosoft/state/active-slot)
echo ORIGIN=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 10 http://127.0.0.1:3000/api/health)
""",
                timeout=420,
            )
            print(out)
            return code

        print("usage: status | rm-leftover | replace-idle-and-cutover")
        return 2
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
