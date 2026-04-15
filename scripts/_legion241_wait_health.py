"""Poll 241 for bridge :8999 health and listening ports."""
from __future__ import annotations

import time
from pathlib import Path

import paramiko

KEY = Path.home() / ".ssh" / "id_ed25519"


def main() -> None:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("192.168.0.241", username="owner1", key_filename=str(KEY), timeout=30)
    for i in range(12):
        time.sleep(5)
        _, o, e = c.exec_command(
            'powershell -NoProfile -Command "try { '
            "(Invoke-WebRequest -UseBasicParsing -Uri http://127.0.0.1:8999/health -TimeoutSec 10).Content } "
            'catch { $_.Exception.Message }"',
            timeout=25,
        )
        blob = (o.read() + e.read()).decode("utf-8", "replace")
        print(f"attempt {i + 1}:", blob[:600])
        if "{" in blob or "ok" in blob.lower():
            break
    _, o2, e2 = c.exec_command(
        "cmd.exe /c netstat -an | findstr LISTENING",
        timeout=25,
    )
    raw = (o2.read() + e2.read()).decode("utf-8", "replace")
    for line in raw.splitlines():
        if ":8998" in line or ":8999" in line or ":11434" in line:
            print("LISTEN", line.strip())
    c.close()


if __name__ == "__main__":
    main()
