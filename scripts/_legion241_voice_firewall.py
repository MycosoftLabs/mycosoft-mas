"""SSH Voice Legion 241 (owner1): inbound TCP 8998, 8999, 11434 (Domain/Private/Public)."""
from __future__ import annotations

import sys
from pathlib import Path

import paramiko

HOST = "192.168.0.241"
USER = "owner1"
KEY = Path.home() / ".ssh" / "id_ed25519"
PORTS = (8998, 8999, 11434)


def main() -> None:
    if not KEY.is_file():
        raise SystemExit(f"Missing {KEY}")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username=USER, key_filename=str(KEY), timeout=25)

    for port in PORTS:
        rule = f"Mycosoft-Voice-TCP{port}"
        for profile_suffix, profiles in (
            ("DP", "private,domain"),
            ("Pub", "public"),
        ):
            name = f"{rule}-{profile_suffix}"
            add = (
                f"cmd.exe /c netsh advfirewall firewall add rule name={name} "
                f"dir=in action=allow protocol=TCP localport={port} profile={profiles}"
            )
            _, o, e = c.exec_command(add, timeout=45)
            print("===", name, "===")
            print((o.read() + e.read()).decode("utf-8", errors="replace").strip()[-500:])

    _, o, e = c.exec_command("cmd.exe /c netstat -an | findstr \"8998 8999 11434\"", timeout=30)
    print("=== netstat (voice ports) ===")
    print((o.read() + e.read()).decode("utf-8", errors="replace")[:2000])

    c.close()
    print("OK")


if __name__ == "__main__":
    main()
