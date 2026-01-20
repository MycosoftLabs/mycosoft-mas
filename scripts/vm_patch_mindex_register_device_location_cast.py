#!/usr/bin/env python3
"""Hot-patch MINDEX mindex-api container to fix MycoBrain device registration when location is null.

Fix: cast :location parameter to text inside ST_GeomFromGeoJSON to avoid asyncpg AmbiguousParameterError.
"""

from __future__ import annotations

import base64
import paramiko
import sys

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "REDACTED_VM_SSH_PASSWORD"


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

targets = [
    "ST_SetSRID(ST_GeomFromGeoJSON(:location), 4326)::geography",
    "ST_SetSRID(ST_GeomFromGeoJSON(:location::text), 4326)::geography",
]
replacement = "ST_SetSRID(ST_GeomFromGeoJSON(CAST(:location AS text)), 4326)::geography"

count = 0
for old in targets:
    if old in src:
        src = src.replace(old, replacement)
        count += 1

case_old = "CASE WHEN :location IS NOT NULL"
case_new = "CASE WHEN CAST(:location AS text) IS NOT NULL"
case_count = src.count(case_old)
src = src.replace(case_old, case_new)

if count == 0 and case_count == 0:
    raise SystemExit("Target snippet(s) not found; mindex-api source changed.")

path.write_text(src, encoding="utf-8")
print("patched_snippets:", count, "patched_case:", case_count)
"""

    encoded = base64.b64encode(py.encode("utf-8")).decode("ascii")
    mindex_container = "mycosoft-always-on-mindex-api-1"
    cmd = f"docker exec {mindex_container} python -c " + repr(
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

