#!/usr/bin/env python3
"""Apply MINDEX SQL migrations on the VM (inside the mindex-api container), stripping UTF-8 BOMs."""

from __future__ import annotations

import paramiko
import sys
import base64

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

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASS, timeout=30)

    # Run migrations via a small inline Python runner that reads SQL with utf-8-sig (BOM-safe).
    py = r"""
from pathlib import Path
import psycopg

dsn = "postgresql://mindex:mindex@mindex-postgres:5432/mindex"
files = sorted(Path("/app/migrations").glob("*.sql"))
if not files:
    raise SystemExit("No migrations found.")

with psycopg.connect(dsn, autocommit=True) as conn:
    with conn.cursor() as cur:
        has_vector = True
        try:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        except Exception as e:
            has_vector = False
            print(f"[WARN] pgvector extension not available; skipping image embedding features: {e}", flush=True)

        cur.execute("CREATE SCHEMA IF NOT EXISTS media;")
        # Some migrations append to a migration log; ensure it exists.
        cur.execute(
            "CREATE TABLE IF NOT EXISTS core.migration_log ("
            " migration_name TEXT PRIMARY KEY,"
            " applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
            ");"
        )
        for path in files:
            if path.name == "0005_images.sql" and not has_vector:
                print(f"Skipping {path.name} (pgvector missing)", flush=True)
                continue
            sql = path.read_text(encoding="utf-8-sig")
            # Hotfix: publications migration references non-existent core.taxa; core.taxon is the real table.
            if path.name == "0003_publications.sql":
                sql = sql.replace("core.taxa", "core.taxon")
            print(f"Applying {path.name} ...", flush=True)
            cur.execute(sql)

print("Migrations applied.")
"""

    encoded = base64.b64encode(py.encode("utf-8")).decode("ascii")
    cmd = "docker exec mindex-api python -c " + repr(
        f"import base64; exec(base64.b64decode('{encoded}').decode('utf-8'))"
    )
    print(run(ssh, cmd))

    # Restart mindex-api to ensure any startup-time constructs reload cleanly
    print(run(ssh, "docker restart mindex-api || true"))

    ssh.close()


if __name__ == "__main__":
    main()

