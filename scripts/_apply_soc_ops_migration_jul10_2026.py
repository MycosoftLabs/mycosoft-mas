#!/usr/bin/env python3
"""Apply migrations/030_soc_security_platform_may03_2026.sql to MAS MINDEX Postgres.

Run from MAS repo (local) — SSHs to 192.168.0.188, reads MINDEX_DATABASE_URL from
the VM .env, applies migration 030, verifies soc_ops.compliance_controls exists.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[1]
CREDS = ROOT / ".credentials.local"
MIGRATION = ROOT / "migrations" / "030_soc_security_platform_may03_2026.sql"
MAS_HOST = os.environ.get("MAS_HOST", "192.168.0.188")


def load_creds() -> None:
    if not CREDS.exists():
        return
    for line in CREDS.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def main() -> int:
    load_creds()
    if not MIGRATION.exists():
        print(f"MISSING migration: {MIGRATION}", file=sys.stderr)
        return 1

    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    if not password:
        print("VM_PASSWORD not set", file=sys.stderr)
        return 1

    sql = MIGRATION.read_text(encoding="utf-8")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(MAS_HOST, username="mycosoft", password=password, timeout=30)

    sftp = ssh.open_sftp()
    with sftp.file("/tmp/030_soc.sql", "w") as remote:
        remote.write(sql)

    remote_apply = r'''#!/usr/bin/env python3
import asyncio
from pathlib import Path

def read_url() -> str:
    env_path = Path("/home/mycosoft/mycosoft/mas/.env")
    url = ""
    if env_path.exists():
        for line in env_path.read_text(errors="replace").splitlines():
            if line.startswith("MINDEX_DATABASE_URL="):
                url = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
            if line.startswith("DATABASE_URL=") and not url:
                url = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not url:
        raise SystemExit("No MINDEX_DATABASE_URL/DATABASE_URL in MAS .env")
    host_hint = url.split("@")[-1] if "@" in url else "none"
    print("DB_HOST_HINT", host_hint)
    return url

async def apply(url: str, sql: str) -> None:
    import asyncpg
    conn = await asyncpg.connect(url)
    try:
        await conn.execute(sql)
        exists = await conn.fetchval("SELECT to_regclass('soc_ops.compliance_controls')")
        count = 0
        if exists:
            count = await conn.fetchval("SELECT COUNT(*) FROM soc_ops.compliance_controls")
        print("OK exists=", exists, "count=", count)
    finally:
        await conn.close()

def main() -> None:
    url = read_url()
    sql = Path("/tmp/030_soc.sql").read_text()
    asyncio.run(apply(url, sql))

if __name__ == "__main__":
    main()
'''
    with sftp.file("/tmp/apply_soc_ops.py", "w") as remote:
        remote.write(remote_apply)
    sftp.close()

    py = "/home/mycosoft/mycosoft/mas/venv/bin/python"
    stdin, stdout, stderr = ssh.exec_command(f"{py} /tmp/apply_soc_ops.py", timeout=180)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    code = stdout.channel.recv_exit_status()
    print(out)
    if err.strip():
        print("STDERR:", err[:800], file=sys.stderr)
    if code != 0:
        ssh.close()
        return code

    stdin, stdout, stderr = ssh.exec_command(
        "curl -sS -w '\\nHTTP:%{http_code}\\n' http://127.0.0.1:8001/api/compliance/controls",
        timeout=30,
    )
    print(stdout.read().decode(errors="replace")[:500])
    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
