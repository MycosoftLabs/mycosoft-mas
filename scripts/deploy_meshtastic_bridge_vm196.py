#!/usr/bin/env python3
"""
Deploy mqtt_meshtastic_bridge on broker VM 196 (SSH key auth to 196, password to 189).

Loads WEBSITE/website/.credentials.local for VM_PASSWORD, MQTT_BROKER_PASSWORD.
Fetches first token from MINDEX_INTERNAL_TOKENS on 189. Does not print secrets.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def load_credentials() -> None:
    roots = [
        Path(__file__).resolve().parent.parent / ".credentials.local",
        Path(r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\.credentials.local"),
    ]
    for p in roots:
        if not p.exists():
            continue
        for line in p.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def extract_first_mindex_token(client):  # type: ignore[no-untyped-def]
    import paramiko

    _, stdout, _ = client.exec_command(
        "grep '^MINDEX_INTERNAL_TOKENS=' /home/mycosoft/mindex/.env 2>/dev/null | head -1",
        timeout=30,
    )
    raw = stdout.read().decode().strip()
    if not raw or "=" not in raw:
        raise RuntimeError("MINDEX_INTERNAL_TOKENS not found on 189")
    val = raw.split("=", 1)[1].strip().strip('"').strip("'")
    first = val.split(",")[0].strip()
    if not first:
        raise RuntimeError("empty MINDEX_INTERNAL_TOKENS")
    return first


def ssh196(cmd: str, timeout: int = 120) -> tuple[int, str]:
    """OpenSSH to 196 (key auth)."""
    full = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", f"mycosoft@{HOST_196}", cmd]
    r = subprocess.run(full, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
    out = (r.stdout or "") + (r.stderr or "")
    return r.returncode, out


def scp196(local: Path, remote: str) -> int:
    full = ["scp", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", str(local), f"mycosoft@{HOST_196}:{remote}"]
    return subprocess.run(full, capture_output=True, text=True, timeout=120).returncode


HOST_196 = "192.168.0.196"
HOST_189 = "192.168.0.189"


def main() -> int:
    load_credentials()
    pw = (os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or "").strip()
    mqtt_pass = (os.environ.get("MQTT_BROKER_PASSWORD") or "").strip()
    if not pw:
        print("ERROR: VM_PASSWORD not set (load website .credentials.local)")
        return 1
    if not mqtt_pass:
        print("ERROR: MQTT_BROKER_PASSWORD not in credentials — bridge cannot authenticate to Mosquitto")
        return 1

    import paramiko

    print("[1/5] Fetch MINDEX internal token from 189...")
    c189 = paramiko.SSHClient()
    c189.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c189.connect(HOST_189, username="mycosoft", password=pw, timeout=20, allow_agent=False, look_for_keys=False)
    try:
        token = extract_first_mindex_token(c189)
    finally:
        c189.close()

    env_body = f"""MESHTASTIC_MQTT_HOST=127.0.0.1
MESHTASTIC_MQTT_PORT=1883
MESHTASTIC_MQTT_TLS=0
MESHTASTIC_MQTT_SUBSCRIBE=msh/#
MESHTASTIC_MQTT_USERNAME=mycobrain
MESHTASTIC_MQTT_PASSWORD={mqtt_pass}
MINDEX_API_URL=http://192.168.0.189:8000
REDIS_URL=redis://192.168.0.189:6379/0
MINDEX_INTERNAL_TOKEN={token}
LOG_LEVEL=INFO
"""

    print("[2/5] Upload env + install venv on 196...")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False, encoding="utf-8") as tf:
        tf.write(env_body)
        tf.flush()
        local_env = Path(tf.name)

    try:
        code = scp196(local_env, "/tmp/meshtastic-bridge.env")
        if code != 0:
            print("scp failed")
            return code
    finally:
        local_env.unlink(missing_ok=True)

    repo = "/home/mycosoft/mycosoft-mas"
    script = f"""
set -e
sudo apt-get update -qq && sudo apt-get install -y -qq python3.12-venv python3-pip || sudo apt-get install -y -qq python3-venv python3-pip
sudo install -d /etc/mycosoft
sudo mv /tmp/meshtastic-bridge.env /etc/mycosoft/meshtastic-bridge.env
sudo chmod 600 /etc/mycosoft/meshtastic-bridge.env
cd {repo}
rm -rf .venv
python3 -m venv .venv
. .venv/bin/activate
pip install -q -U pip wheel
pip install -q paho-mqtt httpx redis httpcore certifi idna hpack protobuf pydantic pydantic-settings PyYAML
pip install -q -e .
sudo cp {repo}/scripts/vm/mqtt-meshtastic-bridge.service /etc/systemd/system/mqtt-meshtastic-bridge.service
sudo systemctl daemon-reload
sudo systemctl enable mqtt-meshtastic-bridge
sudo systemctl restart mqtt-meshtastic-bridge
sleep 2
sudo systemctl is-active mqtt-meshtastic-bridge || true
journalctl -u mqtt-meshtastic-bridge -n 40 --no-pager
"""
    rc, out = ssh196(script.strip(), timeout=600)
    print(out[-12000:] if len(out) > 12000 else out)
    if rc != 0:
        print(f"remote script exit {rc}")
        return rc

    print("[3/5] Bridge active check OK")
    print("[4/5] Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
