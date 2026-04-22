"""
Apply crep.project_nature_cache migration on MINDEX VM (192.168.0.189).
Uses postgres image env (POSTGRES_USER/PASSWORD/DB) inside the container.
"""
from __future__ import annotations

import os
import shlex
import sys
from pathlib import Path

import paramiko

MINDEX_IP = "192.168.0.189"
_CODE = Path(__file__).resolve()
SQL_PATH = _CODE.parents[3] / "MINDEX" / "mindex" / "migrations" / "crep_project_nature_cache_APR22_2026.sql"


def load_vm_password() -> str:
    root = Path(__file__).resolve().parent.parent
    for p in (root / ".credentials.local", Path.home() / ".mycosoft-credentials"):
        if p.exists():
            for line in p.read_text().splitlines():
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
    return os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""


def main() -> int:
    pw = load_vm_password()
    if not pw:
        print("ERROR: VM_PASSWORD not set", file=sys.stderr)
        return 1
    if not SQL_PATH.is_file():
        print(f"ERROR: SQL not found: {SQL_PATH}", file=sys.stderr)
        return 1
    sql = SQL_PATH.read_text(encoding="utf-8")

    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(MINDEX_IP, username="mycosoft", password=pw, timeout=30)

    _, stdout, _ = c.exec_command(
        "docker ps --format '{{.Names}}' | grep -iE 'mindex-postgres|postgres' | head -1",
        timeout=30,
    )
    container = stdout.read().decode("utf-8", errors="replace").strip()
    if not container:
        print("ERROR: No postgres container", file=sys.stderr)
        c.close()
        return 1
    print(f"Using container: {container}")

    # Inside official postgres image, env vars select user/db/password
    inner = (
        "export PGPASSWORD=\"$POSTGRES_PASSWORD\" && "
        "psql -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\" -v ON_ERROR_STOP=1"
    )
    remote = f"docker exec -i {shlex.quote(container)} sh -c {shlex.quote(inner)}"

    stdin, stdout, stderr = c.exec_command(remote, timeout=120)
    stdin.write(sql)
    stdin.channel.shutdown_write()
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    if out:
        print(out)
    if err:
        print(err, file=sys.stderr)
    code = stdout.channel.recv_exit_status()
    c.close()
    if code == 0:
        print("OK: crep.project_nature_cache applied (idempotent if re-run).")
    return 0 if code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
