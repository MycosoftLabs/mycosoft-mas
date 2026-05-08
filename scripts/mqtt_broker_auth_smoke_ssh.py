"""Quick MQTT auth check: read one $SYS message inside broker container (password never printed)."""
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
    for p in (repo / ".credentials.local", Path(r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\.credentials.local")):
        load_dotenv(p)

    pw = (os.environ.get("MQTT_BROKER_PASSWORD") or "").strip()
    user = (os.environ.get("MQTT_BROKER_USER") or "mycobrain").strip()
    host = (os.environ.get("MQTT_BROKER_VM_IP") or "192.168.0.196").strip()
    if not pw:
        print("MQTT_BROKER_PASSWORD missing", file=sys.stderr)
        return 2

    esc = pw.replace("'", "'\\''")
    remote = (
        "sudo docker exec mycobrain-mqtt mosquitto_sub "
        "-h 127.0.0.1 -p 1883 "
        f"-u {user} -P '{esc}' "
        "-t '$SYS/broker/version' -C 1 -W 10 -v"
    )
    r = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=12", f"mycosoft@{host}", remote],
        capture_output=True,
        text=True,
    )
    print(r.stdout.rstrip() or "(empty stdout)")
    if r.stderr:
        print(r.stderr.rstrip(), file=sys.stderr)
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
