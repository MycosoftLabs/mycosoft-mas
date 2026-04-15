"""SSH 249: refresh WSL portproxy 0.0.0.0:8220 -> WSL:8220 (Ubuntu)."""
from __future__ import annotations

import sys
from pathlib import Path

import paramiko

HOST = "192.168.0.249"
USER = "owner2"
KEY = Path.home() / ".ssh" / "id_ed25519"
LISTEN = "0.0.0.0"
PORT = 8220


def main() -> None:
    if not KEY.is_file():
        raise SystemExit(f"Missing {KEY}")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username=USER, key_filename=str(KEY), timeout=25)

    _, out, err = c.exec_command(
        "wsl -d Ubuntu -u root -- hostname -I", timeout=45
    )
    raw = (out.read() + err.read()).decode("utf-8", errors="replace").strip()
    parts = raw.split()
    if not parts:
        print("Could not get WSL IP:", raw, file=sys.stderr)
        c.close()
        raise SystemExit(1)
    wsl_ip = parts[0]
    print("WSL_IP", wsl_ip)

    cmds = [
        f"netsh interface portproxy delete v4tov4 listenaddress={LISTEN} listenport={PORT}",
        f"netsh interface portproxy add v4tov4 listenaddress={LISTEN} listenport={PORT} "
        f"connectaddress={wsl_ip} connectport={PORT}",
        "netsh interface portproxy show v4tov4",
    ]
    for cmd in cmds:
        print("===", cmd[:70], "...")
        _, o, e = c.exec_command(f"cmd.exe /c {cmd}", timeout=60)
        print((o.read() + e.read()).decode("utf-8", errors="replace").strip()[-2000:])

    c.close()


if __name__ == "__main__":
    main()
