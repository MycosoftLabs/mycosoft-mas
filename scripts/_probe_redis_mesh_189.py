"""Probe mesh:packets stream on MINDEX Redis (189); resolves redis container name."""
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
    c.connect("192.168.0.189", username="mycosoft", password=pw, timeout=30)
    cmd = r"""
R=""
for n in mindex-redis mindex-redis-1; do
  if docker ps --format '{{.Names}}' | grep -qx "$n"; then R="$n"; break; fi
done
if [ -z "$R" ]; then R=$(docker ps --format '{{.Names}}' | grep -i redis | head -1); fi
if [ -z "$R" ]; then echo "no_redis_container"; docker ps --format '{{.Names}}'; exit 0; fi
echo "redis_container=$R"
docker exec "$R" redis-cli EXISTS mesh:packets
docker exec "$R" redis-cli XLEN mesh:packets
docker exec "$R" redis-cli XREVRANGE mesh:packets + - COUNT 2
"""
    _, o, e = c.exec_command(cmd, timeout=60)
    sys.stdout.write(o.read().decode(errors="replace"))
    sys.stdout.write(e.read().decode(errors="replace"))
    c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
