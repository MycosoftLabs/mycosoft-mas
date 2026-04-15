"""SSH 249: SFTP bash script to Windows, run from WSL via /mnt/c/..."""
from __future__ import annotations

from pathlib import Path

import paramiko

KEY = Path.home() / ".ssh" / "id_ed25519"

SCRIPT = b"""#!/usr/bin/env bash
set -e
export UVICORN_LOOP=asyncio
export EARTH2_API_HOST=0.0.0.0
export EARTH2_API_PORT=8220
REPO=/root/mycosoft-mas
if [ ! -d "$REPO" ]; then REPO=$HOME/mycosoft-mas; fi
cd "$REPO"
git fetch -q origin
git reset --hard origin/main
pkill -f earth2_api_server.py 2>/dev/null || true
fuser -k 8220/tcp 2>/dev/null || true
sleep 2
PY="${MYCOSOFT_EARTH2_PYTHON:-/root/mycosoft-venvs/mycosoft-earth2-wsl/bin/python}"
nohup env UVICORN_LOOP=asyncio EARTH2_API_HOST=0.0.0.0 EARTH2_API_PORT=8220 "$PY" scripts/earth2_api_server.py >>earth2-api-nohup.log 2>&1 &
sleep 6
curl -sS -m 12 http://127.0.0.1:8220/health || true
echo ""
curl -sS -m 12 http://127.0.0.1:8220/health/event_loop || true
echo ""
"""

WIN_PATH = r"C:/Users/owner2/restart-earth2-wsl.sh"


def main() -> None:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("192.168.0.249", username="owner2", key_filename=str(KEY), timeout=30)

    sftp = c.open_sftp()
    with sftp.file(WIN_PATH, "wb") as f:
        f.write(SCRIPT.replace(b"\r\n", b"\n"))
    sftp.close()

    wsl = "wsl.exe -d Ubuntu -u root -- /bin/bash /mnt/c/Users/owner2/restart-earth2-wsl.sh"
    _, o, e = c.exec_command(wsl, timeout=300)
    print("=== restart ===")
    print((o.read() + e.read()).decode("utf-8", errors="replace")[:12000])

    _, o2, e2 = c.exec_command(
        "curl -sS -m 600 -X POST http://127.0.0.1:8220/models/sfno/load",
        timeout=660,
    )
    print("=== POST load ===")
    print((o2.read() + e2.read()).decode("utf-8", errors="replace")[:6000])

    c.close()


if __name__ == "__main__":
    main()
