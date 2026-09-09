"""Wait for 188 ITDX health. No secrets."""

from __future__ import annotations

import json
import os
import time
import urllib.request
from pathlib import Path

import paramiko

CREDS = Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\.credentials.local")


def load_vm() -> None:
    for line in CREDS.read_text(encoding="utf-8", errors="replace").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def ssh_status() -> str:
    load_vm()
    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    pkey = paramiko.Ed25519Key.from_private_key_file(
        str(Path.home() / ".ssh" / "mycosoft_vm_automation_ed25519")
    )
    client.connect(
        "192.168.0.188",
        username="mycosoft",
        pkey=pkey,
        password=password,
        timeout=25,
        allow_agent=False,
        look_for_keys=False,
    )
    stdin, stdout, _stderr = client.exec_command(
        "systemctl is-active mas-orchestrator; "
        "systemctl show mas-orchestrator -p ActiveState -p SubState -p NRestarts --no-pager; "
        "ss -lnt | awk 'NR==1 || /:8001/'",
        timeout=20,
    )
    out = stdout.read().decode("utf-8", "replace")
    client.close()
    return out


def main() -> None:
    print("UNIT", ssh_status().replace("\n", " | "))
    for i in range(24):
        try:
            with urllib.request.urlopen("http://192.168.0.188:8001/api/itdx/health", timeout=6) as response:
                body = json.loads(response.read().decode("utf-8", "replace"))
                print("HEALTH", response.status, body.get("status") or body.get("ok"))
                return
        except Exception as exc:  # noqa: BLE001
            print("WAIT", i, type(exc).__name__)
            time.sleep(5)
    print("HEALTH_DOWN")


if __name__ == "__main__":
    main()
