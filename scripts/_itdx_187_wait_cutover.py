"""Wait for idle blue 3x 200, then nginx-cutover. Never stop green. No secrets."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import paramiko

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CREDS = Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\.credentials.local")
for line in CREDS.read_text(encoding="utf-8", errors="replace").splitlines():
    if line and not line.startswith("#") and "=" in line:
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(
    "192.168.0.187",
    username="mycosoft",
    password=os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or "",
    timeout=30,
)

cmd = r"""
set -euo pipefail
ACTIVE=$(tr -d '[:space:]' </opt/mycosoft/state/active-slot)
echo ACTIVE=$ACTIVE
test "$ACTIVE" = green
curl -fsS --max-time 8 http://127.0.0.1:3000/api/health >/dev/null
echo CANDIDATE_IMAGE=$(docker inspect -f '{{.Config.Image}}' mycosoft-website-blue)
echo CANDIDATE_NAS=$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "/app/public/assets"}}{{.Source}}{{end}}{{end}}' mycosoft-website-blue)
streak=0
for i in $(seq 1 40); do
  if docker exec mycosoft-website-blue curl -fsS --max-time 5 http://localhost:3000/api/health >/dev/null 2>&1; then
    streak=$((streak+1))
    echo health_pass $streak/3
    if [ "$streak" -ge 3 ]; then
      echo CANDIDATE_200
      break
    fi
  else
    streak=0
    echo health_wait $i
  fi
  sleep 3
done
test "$streak" -ge 3

# auth gate must not be config_missing
loc=$(docker exec mycosoft-website-blue curl -sSI http://localhost:3000/natureos/mycobrain --max-time 10 \
  | tr -d '\r' | awk 'tolower($1)=="location:"{print $2}' | head -1)
echo AUTH_LOC=$loc
case "$loc" in
  *error=config_missing*) echo AUTH_BROKEN; exit 12 ;;
esac

cd /opt/mycosoft/website
tmpl=deploy/nginx/conf.d/website.conf.template
out=/opt/mycosoft/nginx/conf.d/website.conf
sed "s|__ACTIVE_SLOT__|blue|g" "$tmpl" > "$out"
docker exec mycosoft-website-proxy nginx -t
docker exec mycosoft-website-proxy nginx -s reload
echo blue > /opt/mycosoft/state/active-slot
echo FLIPPED=$(cat /opt/mycosoft/state/active-slot)
echo ORIGIN=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 10 http://127.0.0.1:3000/api/health)
# CF purge from deploy.env
if [ -f /opt/mycosoft/deploy.env ]; then
  set -a
  # shellcheck disable=SC1091
  source <(grep -E '^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*=' /opt/mycosoft/deploy.env)
  set +a
fi
if [ -n "${CF_ZONE_ID:-}" ] && [ -n "${CF_API_TOKEN:-}" ]; then
  resp=$(curl -sS -X POST "https://api.cloudflare.com/client/v4/zones/${CF_ZONE_ID}/purge_cache" \
    -H "Authorization: Bearer ${CF_API_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{"purge_everything":true}')
  echo "$resp" | grep -q '"success":true' && echo CF_PURGE_OK || echo CF_PURGE_FAIL
else
  echo CF_PURGE_SKIP
fi
echo PUBLIC_SLOT=$(curl -sSI https://mycosoft.com/healthz --max-time 12 | awk -F': *' 'tolower($1)=="x-active-slot"{gsub("\r",""); print tolower($2)}')
echo PUBLIC=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 15 https://mycosoft.com/api/health)
echo SANDBOX=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 15 https://sandbox.mycosoft.com/api/health)
echo GREEN_STILL=$(docker inspect -f '{{.State.Health.Status}}' mycosoft-website-green)
"""
_, stdout, stderr = client.exec_command(cmd, timeout=240)
print((stdout.read() + stderr.read()).decode("utf-8", "replace"))
print("exit", stdout.channel.recv_exit_status())
client.close()
