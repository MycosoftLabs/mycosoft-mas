#!/usr/bin/env python3
"""Deploy updated MAS systemd-aware watchdog + tighten cron to every 2 minutes."""

from __future__ import annotations

import os
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[1]
CREDS = ROOT / ".credentials.local"
WATCHDOG = ROOT / "scripts" / "mas_watchdog.sh"


def load_creds() -> None:
    if not CREDS.exists():
        return
    for line in CREDS.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def main() -> int:
    load_creds()
    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("192.168.0.188", username="mycosoft", password=password, timeout=30)
    sftp = ssh.open_sftp()
    for remote in ("/home/mycosoft/mas_watchdog.sh", "/home/mycosoft/mycosoft/mas/scripts/mas_watchdog.sh"):
        with sftp.file(remote, "w") as f:
            f.write(WATCHDOG.read_text(encoding="utf-8"))
        ssh.exec_command(f"chmod +x {remote}")
    sftp.close()

    # Install/refresh cron every 2 minutes
    _i, o, _e = ssh.exec_command("crontab -l 2>/dev/null || true")
    existing = o.read().decode(errors="replace")
    lines = [ln for ln in existing.splitlines() if "mas_watchdog" not in ln]
    lines.append("*/2 * * * * /home/mycosoft/mas_watchdog.sh")
    new_cron = "\n".join(lines) + "\n"
    _i, o, e = ssh.exec_command("crontab -")
    _i.write(new_cron.encode())
    _i.channel.shutdown_write()
    print(o.read().decode(errors="replace"))
    err = e.read().decode(errors="replace")
    if err.strip():
        print("STDERR", err)
    _i, o, _e = ssh.exec_command("crontab -l | grep mas_watchdog; /home/mycosoft/mas_watchdog.sh; tail -n 3 /home/mycosoft/mas_watchdog.log")
    print(o.read().decode(errors="replace"))
    ssh.close()
    print("Watchdog deployed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
