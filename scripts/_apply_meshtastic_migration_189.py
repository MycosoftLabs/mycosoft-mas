"""Apply migrations/0037_meshtastic_mesh.sql on MINDEX VM 189 Postgres (idempotent)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import paramiko

for base in (
    Path(__file__).resolve().parents[1],
    Path(r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website"),
):
    p = base / ".credentials.local"
    if p.is_file():
        for line in p.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))
        break


def main() -> int:
    pw = (os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or "").strip()
    if not pw:
        print("no VM_PASSWORD", file=sys.stderr)
        return 1
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("192.168.0.189", username="mycosoft", password=pw, timeout=45)
    script = r"""
set -e
cd /home/mycosoft/mindex
git fetch origin && git reset --hard origin/main
PF=migrations/0037_meshtastic_mesh.sql
test -f "$PF" || { echo "missing $PF"; exit 1; }
# docker-compose uses container_name: mindex-postgres
if docker ps --format '{{.Names}}' | grep -q '^mindex-postgres$'; then
  NAME=mindex-postgres
else
  NAME=$(docker ps -q -f 'name=mindex-postgres' | head -1)
fi
if [ -z "$NAME" ]; then
  echo "no_postgres_container"
  docker ps --format '{{.Names}}'
  exit 1
fi
echo "postgres_target=$NAME"
# Prefer API DB user from .env; fall back to postgres superuser (some VMs never created role mindex)
set -a
[ -f .env ] && . ./.env
set +a
U="${MINDEX_DB_USER:-mindex}"
D="${MINDEX_DB_NAME:-mindex}"
if ! docker exec "$NAME" psql -U "$U" -d "$D" -c 'SELECT 1' >/dev/null 2>&1; then
  if docker exec "$NAME" psql -U postgres -d "$D" -c 'SELECT 1' >/dev/null 2>&1; then
    U=postgres
    echo "using_superuser_postgres"
  else
    echo "cannot_connect_db_$D"
    docker exec "$NAME" psql -U postgres -d postgres -c '\du' || true
    exit 1
  fi
fi
echo "psql_user_db=${U}/${D}"
cat "$PF" | docker exec -i "$NAME" psql -U "$U" -d "$D" -v ON_ERROR_STOP=1
echo "apply_ok"
docker exec "$NAME" psql -U "$U" -d "$D" -c "SELECT tablename FROM pg_tables WHERE schemaname = 'meshtastic' ORDER BY 1;"
"""
    _, o, e = c.exec_command(script, timeout=180)
    sys.stdout.write(o.read().decode(errors="replace"))
    sys.stdout.write(e.read().decode(errors="replace"))
    code = o.channel.recv_exit_status()
    c.close()
    return 0 if code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
