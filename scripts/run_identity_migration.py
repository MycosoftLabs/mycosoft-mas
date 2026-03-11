#!/usr/bin/env python3
"""
Run identity migration 025 on MINDEX Postgres.

Usage:
    python scripts/run_identity_migration.py

Requires MINDEX_DATABASE_URL in .env (or environment).
Example: postgresql://mindex:PASSWORD@192.168.0.189:5432/mindex

Author: MYCA
Created: March 9, 2026
"""

import asyncio
import os
import sys
from pathlib import Path
from urllib.parse import quote_plus

# Load .env and .credentials.local from repo root
_repo_root = Path(__file__).resolve().parent.parent
for name in (".env", ".credentials.local"):
    f = _repo_root / name
    if f.exists():
        for line in f.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                key, value = key.strip(), value.strip().strip('"').strip("'")
                if key and value and key not in os.environ:
                    os.environ[key] = value

try:
    import asyncpg
except ImportError:
    print("asyncpg required. Run: pip install asyncpg")
    sys.exit(1)


async def main() -> int:
    db_url = os.environ.get("MINDEX_DATABASE_URL", "")
    if not db_url:
        pw = os.environ.get("MINDEX_DB_PASSWORD") or os.environ.get("VM_PASSWORD")
        if pw:
            db_url = f"postgresql://mindex:{quote_plus(pw)}@192.168.0.189:5432/mindex"
    if not db_url:
        print(
            "MINDEX_DATABASE_URL not set. Set it in .env, or set MINDEX_DB_PASSWORD/VM_PASSWORD in .credentials.local.\n"
            "Example: postgresql://mindex:PASSWORD@192.168.0.189:5432/mindex"
        )
        return 1

    migration_path = _repo_root / "migrations" / "025_identity_system.sql"
    if not migration_path.exists():
        print(f"Migration not found: {migration_path}")
        return 1

    sql = migration_path.read_text()
    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute(sql)
        print("Migration 025_identity_system.sql applied successfully.")
    except Exception as e:
        print(f"Migration failed: {e}")
        return 1
    finally:
        await conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
