"""Tail recent PersonaPlex / Ollama logs on 241."""
from __future__ import annotations

from pathlib import Path

import paramiko

KEY = Path.home() / ".ssh" / "id_ed25519"
LOGDIR = r"C:\Users\owner1\MycosoftData\logs"


def main() -> None:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("192.168.0.241", username="owner1", key_filename=str(KEY), timeout=30)
    for name in (
        "moshi-stderr.log",
        "moshi-stdout.log",
        "bridge-stderr.log",
        "bridge-stdout.log",
        "ollama-stderr.log",
    ):
        path = f"{LOGDIR}\\{name}".replace("\\", "\\\\")
        cmd = (
            "powershell -NoProfile -Command "
            f'"if (Test-Path "{LOGDIR}\\{name}") {{ Get-Content "{LOGDIR}\\{name}" -Tail 50 }} else {{ "missing" }}"'
        )
        _, o, e = c.exec_command(cmd, timeout=30)
        print("\n===", name, "===")
        print((o.read() + e.read()).decode("utf-8", "replace")[-3000:])
    c.close()


if __name__ == "__main__":
    main()
