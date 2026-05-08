"""Optional LAN MQTT pub/sub ping on a non-mesh topic (password never printed)."""
from __future__ import annotations

import os
import re
import subprocess
import sys
import uuid
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
    token = uuid.uuid4().hex[:12]
    topic = f"mycosoft/internal/mqtt-smoke/{token}"
    payload = f"ok-{token}"

    pub = (
        "sudo docker exec mycobrain-mqtt mosquitto_pub "
        "-h 127.0.0.1 -p 1883 "
        f"-u {user} -P '{esc}' "
        f"-t '{topic}' -m '{payload}' -q 1 -r"
    )
    sub = (
        "sudo docker exec mycobrain-mqtt mosquitto_sub "
        "-h 127.0.0.1 -p 1883 "
        f"-u {user} -P '{esc}' "
        f"-t '{topic}' -C 1 -W 8 -v"
    )

    r1 = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=12", f"mycosoft@{host}", pub],
        capture_output=True,
        text=True,
    )
    if r1.returncode != 0:
        print("pub failed", r1.stderr, file=sys.stderr)
        return r1.returncode

    r2 = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=12", f"mycosoft@{host}", sub],
        capture_output=True,
        text=True,
    )
    got = (r2.stdout or "").strip()
    print(got or "(no message received)")
    if r2.stderr:
        print(r2.stderr.strip(), file=sys.stderr)
    if payload not in got:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
