#!/usr/bin/env python3
"""Hot-patch the running MINDEX API container to avoid ':param::type' patterns in SQL text().

Fixes in /app/mindex_api/routers/mycobrain.py:
- :device_type::mycobrain.device_type  -> CAST(:device_type AS mycobrain.device_type)
- :analog_channels::jsonb              -> CAST(:analog_channels AS jsonb)
- :metadata::jsonb                     -> CAST(:metadata AS jsonb)
"""

from __future__ import annotations

import base64
import paramiko
import sys

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "Mushroom1!Mushroom1!"


def run(ssh: paramiko.SSHClient, cmd: str) -> str:
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return (out + ("\n" + err if err.strip() else "")).strip()


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    py = r"""
from pathlib import Path

path = Path("/app/mindex_api/routers/mycobrain.py")
src = path.read_text(encoding="utf-8", errors="replace")

replacements = [
  (":device_type::mycobrain.device_type", "CAST(:device_type AS mycobrain.device_type)"),
  (":analog_channels::jsonb", "CAST(:analog_channels AS jsonb)"),
  (":metadata::jsonb", "CAST(:metadata AS jsonb)"),
]

total = 0
for old, new in replacements:
  c = src.count(old)
  if c:
    src = src.replace(old, new)
    total += c

if total == 0:
  raise SystemExit("No cast patterns found to replace.")

path.write_text(src, encoding="utf-8")
print("replacements_applied:", total)
"""

    encoded = base64.b64encode(py.encode("utf-8")).decode("ascii")
    mindex_container = "mycosoft-always-on-mindex-api-1"
    cmd = "docker exec " + mindex_container + " python -c " + repr(
        f"import base64; exec(base64.b64decode('{encoded}').decode('utf-8'))"
    )

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASS, timeout=30)
    print(run(ssh, cmd))
    print(run(ssh, f"docker restart {mindex_container} || true"))
    ssh.close()


if __name__ == "__main__":
    main()

