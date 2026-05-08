"""LAN MQTT msh/# smoke: SSH to broker VM, mosquitto_sub inside Docker (password never printed)."""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^([^#=]+)=(.*)$", line.strip())
        if m:
            os.environ[m.group(1).strip()] = m.group(2).strip()


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    for p in (
        repo / ".credentials.local",
        Path(r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\.credentials.local"),
    ):
        load_dotenv(p)

    pw = (os.environ.get("MQTT_BROKER_PASSWORD") or "").strip()
    user = (os.environ.get("MQTT_BROKER_USER") or "mycobrain").strip()
    host = (os.environ.get("MQTT_BROKER_VM_IP") or "192.168.0.196").strip()
    if not pw:
        print(
            "MQTT_BROKER_PASSWORD not set. Add to WEBSITE website\\.credentials.local",
            file=sys.stderr,
        )
        return 2

    esc = pw.replace("'", "'\\''")
    remote = (
        "sudo docker exec mycobrain-mqtt mosquitto_sub "
        "-h 127.0.0.1 -p 1883 "
        f"-u {user} -P '{esc}' "
        "-t 'msh/#' -C 15 -W 70 -v"
    )
    r = subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=15",
            f"mycosoft@{host}",
            remote,
        ],
        capture_output=True,
        text=True,
    )
    if r.stdout:
        print(r.stdout.rstrip())
    else:
        print("(no stdout — no msh/# messages in window or sub timed out)")
    if r.stderr:
        print(r.stderr.rstrip(), file=sys.stderr)
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
