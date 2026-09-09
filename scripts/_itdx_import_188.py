"""Reproduce the exact ITDX import used by myca_main on 188. No secrets."""

from __future__ import annotations

import os
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[1]


def load_creds() -> None:
    for line in (ROOT / ".credentials.local").read_text(encoding="utf-8", errors="replace").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def main() -> None:
    load_creds()
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    key_path = Path.home() / ".ssh" / "mycosoft_vm_automation_ed25519"
    client.connect(
        "192.168.0.188",
        username="mycosoft",
        pkey=paramiko.Ed25519Key.from_private_key_file(str(key_path)),
        password=os.environ.get("VM_PASSWORD") or "",
        timeout=25,
        allow_agent=True,
        look_for_keys=True,
    )
    cmd = r"""
cd /home/mycosoft/mycosoft/mas
./venv/bin/python - <<'PY'
import traceback
try:
    from mycosoft_mas.core.routers.itdx_api import (
        avani_task8_router,
        myca_task8_router,
        router as itdx_router,
    )
    print('IMPORT_OK', itdx_router.prefix, avani_task8_router.prefix, myca_task8_router.prefix)
except Exception as exc:
    print('IMPORT_FAIL', type(exc).__name__, exc)
    traceback.print_exc()
PY
"""
    stdin, stdout, stderr = client.exec_command(cmd, timeout=40)
    print(stdout.read().decode("utf-8", "replace"))
    err = stderr.read().decode("utf-8", "replace")
    if err.strip():
        print("STDERR", err[:1500])
    client.close()


if __name__ == "__main__":
    main()
