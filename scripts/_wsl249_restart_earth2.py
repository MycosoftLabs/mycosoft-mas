"""SSH 249 (owner2): WSL pull main + restart Earth-2 API with asyncio loop."""
from __future__ import annotations

from pathlib import Path

import paramiko

KEY = Path.home() / ".ssh" / "id_ed25519"


def main() -> None:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("192.168.0.249", username="owner2", key_filename=str(KEY), timeout=30)

    one = (
        "export UVICORN_LOOP=asyncio EARTH2_API_HOST=0.0.0.0 EARTH2_API_PORT=8220; "
        "cd /root/mycosoft-mas 2>/dev/null || cd ~/mycosoft-mas; "
        "git fetch origin; git reset --hard origin/main; "
        "pkill -f earth2_api_server.py 2>/dev/null || true; sleep 2; "
        "nohup env UVICORN_LOOP=asyncio EARTH2_API_HOST=0.0.0.0 EARTH2_API_PORT=8220 "
        "${MYCOSOFT_EARTH2_PYTHON:-/root/mycosoft-venvs/mycosoft-earth2-wsl/bin/python} "
        "scripts/earth2_api_server.py >>earth2-api-nohup.log 2>&1 & sleep 5; "
        "curl -sS -m 10 http://127.0.0.1:8220/health"
    )
    cmd = f"wsl -d Ubuntu -u root -- bash -lc {repr(one)}"
    _, o, e = c.exec_command(cmd, timeout=300)
    print("=== restart ===")
    print((o.read() + e.read()).decode("utf-8", errors="replace")[:8000])

    _, o2, e2 = c.exec_command(
        "curl -sS -m 120 -X POST http://127.0.0.1:8220/models/sfno/load",
        timeout=150,
    )
    print("=== POST /models/sfno/load ===")
    print((o2.read() + e2.read()).decode("utf-8", errors="replace")[:8000])

    c.close()


if __name__ == "__main__":
    main()
