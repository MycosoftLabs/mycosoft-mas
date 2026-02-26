#!/usr/bin/env python3
"""
Apply Grounded Cognition MINDEX migrations (0016, 0017, 0018) to VM 189.
Run from MAS repo with VM_PASSWORD set. Created: February 17, 2026
"""

import os
import sys
from pathlib import Path

mas_root = Path(__file__).resolve().parent.parent
mindex_root = mas_root.parent / "MINDEX" / "mindex"
if not mindex_root.exists():
    mindex_root = mas_root.parent.parent / "MINDEX" / "mindex"
if not mindex_root.exists():
    mindex_root = mas_root.parent / "mindex"
migrations_dir = mindex_root / "migrations"

MIGRATIONS = [
    "0016_postgis_spatial.sql",
    "0017_temporal_episodes.sql",
    "0018_grounded_cognition.sql",
]


def main():
    vm_pass = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")
    if not vm_pass:
        creds = mas_root / ".credentials.local"
        if creds.exists():
            for line in creds.read_text().splitlines():
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip()
        vm_pass = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")
    if not vm_pass:
        print("ERROR: VM_PASSWORD not set. Load from .credentials.local or set env.")
        sys.exit(1)

    try:
        import paramiko
    except ImportError:
        print("ERROR: paramiko required. pip install paramiko")
        sys.exit(1)

    vm = os.environ.get("MINDEX_VM_IP", "192.168.0.189")
    user = os.environ.get("VM_USER", "mycosoft")
    db_user = os.environ.get("MINDEX_DB_USER", "mycosoft")
    db_name = os.environ.get("MINDEX_DB_NAME", "mindex")
    db_pass = os.environ.get("MINDEX_DB_PASSWORD", "postgres")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print(f"Connecting to {vm}...")
        client.connect(vm, username=user, password=vm_pass, timeout=30)

        for m in MIGRATIONS:
            p = migrations_dir / m
            if not p.exists():
                print(f"  SKIP: {m} (file not found)")
                continue
            print(f"  Applying {m}...")
            sftp = client.open_sftp()
            remote = f"/tmp/{m}"
            sftp.put(str(p), remote)
            sftp.close()
            stdin, stdout, stderr = client.exec_command(
                f"PGPASSWORD={db_pass} psql -h 127.0.0.1 -U {db_user} -d {db_name} -f /tmp/{m} 2>&1",
                timeout=60,
            )
            out = stdout.read().decode("utf-8", errors="replace")
            if "ERROR" in out and "already exists" not in out:
                print(f"    Warning: {out[:300]}")
            else:
                print(f"    OK")
            client.exec_command(f"rm -f /tmp/{m}", timeout=5)

        print("Migrations complete.")
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    main()
